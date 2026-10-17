"""Reproducible synthetic registry, responder roster, and labeled flood fixtures."""

import random
from collections.abc import Mapping

from .config import load_config
from .evaluation import load_cases
from .triage import classify, score_priority


def synthetic_data(
    *,
    now: float,
    seed: int = 42,
    residents_count: int = 500,
    calls_count: int = 200,
    profiles: Mapping | None = None,
) -> dict:
    if residents_count < 1 or calls_count < 0:
        raise ValueError("Need at least one resident and a nonnegative call count")
    rng = random.Random(seed)
    profiles = profiles or load_config("profiles")
    zones = load_config("zones")
    residents = []
    for i in range(residents_count):
        zone = zones[i % len(zones)]
        profile = profiles["zones"][zone["id"]]
        weights = profile["language_weights"]
        if not weights or any(v < 0 for v in weights.values()) or sum(weights.values()) <= 0:
            raise ValueError("Language weights must be nonnegative and sum to a positive value")
        if not 0 <= profile["age_65_share"] <= 1:
            raise ValueError("age_65_share must be between zero and one")
        language = rng.choices(list(weights), weights=list(weights.values()), k=1)[0]
        older = rng.random() < profile["age_65_share"]
        needs = [
            need
            for need, probability in (
                ("mobility", 0.15 if older else 0.04),
                ("oxygen", 0.04),
                ("dialysis", 0.02),
                ("alone", 0.2),
            )
            if rng.random() < probability
        ]
        residents.append(
            {
                "id": f"synthetic-resident-{i:04d}",
                "language": language,
                "zone_id": zone["id"],
                "lat": zone["center"][0] + rng.uniform(-0.002, 0.002),
                "lon": zone["center"][1] + rng.uniform(-0.002, 0.002),
                "age_65_plus": older,
                "needs": needs,
                "contact_id": f"synthetic-contact-{i:04d}",
                "consent_checkin": rng.random() < 0.9,
                "consent_analytics": rng.random() < 0.95,
                "do_not_call": False,
                "source": "synthetic",
            }
        )
    responders = []
    specialties = ("medical", "evac_logistics", "facilities", "safety_escort")
    for i in range(10):
        listener = i in (8, 9)
        responders.append(
            {
                "id": f"synthetic-responder-{i:02d}",
                "name": f"Synthetic helper {i + 1}",
                "skills": ["mental_health"] if listener else [specialties[i % 4], "general"],
                "languages": ["en", ("es", "ko", "zh", "tl", "hy")[i % 5]],
                "pools": ["trained_listener"] if listener else ["trained_responder"],
                "verified": True,
                "status": "available",
                "active_calls": 0,
                "calls_this_shift": rng.randrange(8),
                "source": "synthetic",
            }
        )
    cases = load_cases()
    routine = [c for c in cases if c["bucket"] == "everyday"]
    crisis = [
        c
        for c in cases
        if c["bucket"] in {"p0", "hazard"} and c["expected"]["severity"] in {"P0", "P1"}
    ]
    calls, reports, cards = [], [], []
    for i in range(calls_count):
        # Exact 60/25/10/5 proportions for every full block of 20 calls.
        slot = i % 20
        kind = (
            "everyday"
            if slot < 12
            else "crisis"
            if slot < 17
            else "duplicate"
            if slot < 19
            else "hoax"
        )
        zone = zones[i % len(zones)]
        if kind == "everyday":
            case = routine[i % len(routine)]
        elif kind == "hoax":
            case = next(c for c in cases if c["id"] == "hazard-test")
        elif kind == "duplicate":
            case = next(c for c in cases if c["id"] == "hazard-smoke")
        else:
            case = crisis[i % len(crisis)]
        resident = residents[i % len(residents)]
        # Drill language mix deliberately differs from population weighting.
        language = "es" if i % 10 in (0, 1) else "ko" if i % 10 == 2 else "en"
        if language == "es" and kind == "everyday":
            case = next(c for c in cases if c["id"] == "everyday-es-appointment")
        if language == "ko":
            if kind == "crisis":
                case = next(c for c in cases if c["id"] == "language-ko-fire")
            else:
                case = {
                    "transcript": "사무실은 어디에 있나요?",
                    "fields": {"category": "info"},
                    "expected": {"severity": "P3", "functions": ["lookup_info"]},
                }
        fields = {**case.get("fields", {}), "language": language}
        label = classify(case["transcript"], fields)
        started = now - 1200 + (i * 17 % 1100)
        ended = started + rng.randint(30, 90)
        caller = resident["id"] if kind != "duplicate" else f"synthetic-repeat-{zone['id']}"
        call_id = f"synthetic-call-{i:04d}"
        calls.append(
            {
                "call_id": call_id,
                "caller_hash": caller,
                "source": "synthetic",
                "zone_id": zone["id"],
                "language": language,
                "started_at": started,
                "ended_at": ended,
                "ts": started,
                "severity": label.severity,
                "category": label.category,
                "expected_severity": case["expected"]["severity"],
                "outcome": "safety_911_988"
                if label.severity == "P0"
                else "human_transferred"
                if label.severity in {"P1", "P2"}
                else "ai_resolved",
                "human_at": started + 12 if label.severity in {"P1", "P2"} else None,
                "consent_analytics": resident["consent_analytics"],
                "safety_compliant": None,
                "verified": True,
                "drill_code": f"DIZA-{i:04d}",
            }
        )
        reports.append(
            {
                "id": f"synthetic-report-{i:04d}",
                "call_id": call_id,
                "caller_hash": caller,
                "zone_id": zone["id"],
                "category": label.category,
                "severity": label.severity,
                "hazard_here_now": label.hazard_here_now,
                "ts": started,
                "lat": zone["center"][0] + rng.uniform(-0.0005, 0.0005),
                "lon": zone["center"][1] + rng.uniform(-0.0005, 0.0005),
                "priority": score_priority(label),
                "source": "synthetic",
            }
        )
        cards.append(
            {
                "code": f"DIZA-{i:04d}",
                "kind": kind,
                "language": language,
                "role_text": case["transcript"],
                "expected": case["expected"],
            }
        )
    return {
        "schema_version": 1,
        "source": "synthetic",
        "seed": seed,
        "as_of": now,
        "profile_provenance": profiles["provenance"],
        "residents": residents,
        "responders": responders,
        "calls": calls,
        "reports": reports,
        "drill_cards": cards,
    }
