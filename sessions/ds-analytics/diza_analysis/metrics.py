"""Measured values with explicit denominators; missing instrumentation stays null."""

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from statistics import median

from .privacy import analytics_allowed
from .timeutil import iso_utc, timestamp
from .triage import SEVERITIES, normalize

FAILURE_CODES = {
    "missed_p0",
    "severity_mismatch",
    "repeated_question",
    "human_requested",
    "early_hangup",
    "form_incomplete",
    "safety_failure",
}


def rate(numerator: int, denominator: int) -> dict:
    return {
        "value": numerator / denominator if denominator else None,
        "numerator": numerator,
        "denominator": denominator,
    }


def unique_calls(rows: Sequence[Mapping]) -> list[dict]:
    """Collapse repeated call events, preserving non-null fields from earlier events."""
    calls = {}
    for row in rows:
        key = row.get("call_id") or row.get("id")
        if not key:
            continue
        previous = calls.get(key, {})
        calls[key] = {**previous, **{k: v for k, v in row.items() if v is not None}}
        # An opt-out always wins over another copy of the same call.
        if previous and not analytics_allowed(previous.get("consent_analytics")):
            calls[key]["consent_analytics"] = False
    return list(calls.values())


def peak_concurrency(rows: Sequence[Mapping], now: float) -> tuple[int | None, int]:
    events, observed = [], 0
    for row in rows:
        start, end = timestamp(row.get("started_at")), timestamp(row.get("ended_at"))
        if start is None or start > now or (end is not None and end < start):
            continue
        observed += 1
        end = min(end if end is not None else now, now)
        if end > start:
            events.extend(((start, 1), (end, -1)))
    count = peak = 0
    # Ending at t releases capacity before a new call beginning at t.
    for _, change in sorted(events):
        count += change
        peak = max(peak, count)
    return (peak if observed else None), observed


def mine_failures(rows: Sequence[Mapping]) -> list[dict]:
    """Return actionable reason codes without repeating private transcript content."""
    failures = []
    for row in unique_calls(rows):
        if not analytics_allowed(row.get("consent_analytics")):
            continue
        flags = set(row.get("failure_flags") or []) & FAILURE_CODES
        expected, actual = row.get("expected_severity"), row.get("severity")
        if expected == "P0" and actual != "P0":
            flags.add("missed_p0")
        if expected in SEVERITIES and actual != expected:
            flags.add("severity_mismatch")
        questions = [normalize(q).strip() for q in row.get("questions", []) if q.strip()]
        if len(questions) != len(set(questions)):
            flags.add("repeated_question")
        if re.search(
            r"\b(?:human|real person|operator|persona real)\b",
            normalize(row.get("transcript") or ""),
        ):
            flags.add("human_requested")
        start, end = timestamp(row.get("started_at")), timestamp(row.get("ended_at"))
        if (
            start is not None
            and end is not None
            and 0 <= end - start < 15
            and row.get("outcome") == "abandoned"
        ):
            flags.add("early_hangup")
        if row.get("form_complete") is False:
            flags.add("form_incomplete")
        if row.get("safety_compliant") is False:
            flags.add("safety_failure")
        if flags:
            failures.append(
                {"call_id": row.get("call_id", row.get("id")), "reasons": sorted(flags)}
            )
    return failures


def snapshot(rows: Sequence[Mapping], *, now, prompt_version: str = "unversioned") -> dict:
    now = timestamp(now)
    if now is None:
        raise ValueError("now is required")
    all_calls = unique_calls(rows)
    consented = [r for r in all_calls if analytics_allowed(r.get("consent_analytics"))]
    calls = []
    for row in consented:
        observed_at = timestamp(
            row.get("started_at") if row.get("started_at") is not None else row.get("ts")
        )
        if observed_at is None or observed_at <= now:
            calls.append(row)
    labeled = [r for r in calls if r.get("expected_severity") in SEVERITIES]
    urgent = [r for r in labeled if r["expected_severity"] == "P0"]
    known_outcomes = [r for r in calls if r.get("outcome") not in {None, "unknown"}]
    nonurgent = [r for r in known_outcomes if r.get("severity") in {"P1", "P2", "P3"}]
    routed = [r for r in calls if isinstance(r.get("routing_match"), bool)]
    forms = [r for r in calls if isinstance(r.get("form_complete"), bool)]
    safety = [r for r in calls if isinstance(r.get("safety_compliant"), bool)]
    language = [r for r in calls if r.get("language") not in {None, "", "und"}]
    peak, intervals = peak_concurrency(calls, now)
    time_to_human = {}
    for severity in ("P0", "P1"):
        delays = []
        for row in calls:
            start, human = timestamp(row.get("started_at")), timestamp(row.get("human_at"))
            if (
                row.get("severity") == severity
                and start is not None
                and human is not None
                and start <= human <= now
            ):
                delays.append(human - start)
        time_to_human[severity] = {
            "median_seconds": median(delays) if delays else None,
            "observations": len(delays),
        }
    failures = mine_failures(calls)
    return {
        "schema_version": 1,
        "visibility": "internal",
        "as_of": iso_utc(now),
        "prompt_version": prompt_version,
        "data_kind": sorted({r.get("source", "observed") for r in calls}),
        "calls": len(calls),
        "excluded_consent_or_unknown": len(all_calls) - len(consented),
        "excluded_future": len(consented) - len(calls),
        "peak_concurrent": peak,
        "coverage": {
            "intervals": intervals,
            "ground_truth": len(labeled),
            "outcomes": len(known_outcomes),
            "language": len(language),
            "routing_labels": len(routed),
            "safety_labels": len(safety),
        },
        "p0_recall": rate(sum(r.get("severity") == "P0" for r in urgent), len(urgent)),
        "severity_accuracy": rate(
            sum(r.get("severity") == r["expected_severity"] for r in labeled), len(labeled)
        ),
        "safety_compliance": rate(sum(r["safety_compliant"] for r in safety), len(safety)),
        "routing_match": rate(sum(r["routing_match"] for r in routed), len(routed)),
        "form_completion": rate(sum(r["form_complete"] for r in forms), len(forms)),
        "ai_resolved_nonurgent": rate(
            sum(r["outcome"] == "ai_resolved" for r in nonurgent), len(nonurgent)
        ),
        "non_en_es": rate(sum(r["language"] not in {"en", "es"} for r in language), len(language)),
        "busy_or_abandoned": rate(
            sum(r.get("outcome") in {"busy", "abandoned"} for r in known_outcomes),
            len(known_outcomes),
        ),
        "time_to_human": time_to_human,
        "failures": dict(Counter(reason for f in failures for reason in f["reasons"])),
    }


def reach_metrics(
    residents: Sequence[Mapping],
    attempts: Sequence[Mapping],
    *,
    declared_at,
) -> dict:
    declared = timestamp(declared_at)
    if declared is None:
        raise ValueError("declared_at is required")
    eligible = {
        r["id"]
        for r in residents
        if r.get("consent_checkin") is True and not r.get("do_not_call") and r.get("needs")
    }
    reached, through_contact = set(), set()
    for attempt in attempts:
        ts = timestamp(attempt.get("ts"))
        resident = attempt.get("resident_id")
        if (
            resident in eligible
            and attempt.get("result") == "reached"
            and ts is not None
            and declared <= ts <= declared + 900
        ):
            reached.add(resident)
            if attempt.get("via") in {"contact", "neighbor"}:
                through_contact.add(resident)
    return {
        "high_risk_reached_within_15_min": rate(len(reached), len(eligible)),
        "reached_via_contact": len(through_contact),
    }


def judge_agreement(labels: Sequence[Mapping]) -> dict:
    by_criterion = {}
    for row in labels:
        human, judge = row.get("human"), row.get("judge")
        if human is None or judge is None:
            continue
        by_criterion.setdefault(row["criterion"], []).append(human == judge)
    return {
        criterion: {
            **rate(sum(values), len(values)),
            "trusted": len(values) >= 40 and sum(values) / len(values) >= 0.8,
        }
        for criterion, values in sorted(by_criterion.items())
    }
