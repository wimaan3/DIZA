"""Minimal operational links for consent-aware live analysis.

The link table lives alongside the operational call/consent tables, not in public
exports. It stores no phone, name, transcript, address, or precise coordinates.
Legacy calls are not backfilled by guessing caller identity.
"""

import hashlib
import re
import time
from collections import Counter

from .cli import prepare_records
from .config import load_config
from .metrics import snapshot
from .privacy import pseudonym
from .triage import CATEGORIES, SEVERITIES, classify, language_code, score_priority


def caller_text(call: dict, args: dict) -> str:
    """Exclude agent speech so emergency instructions cannot become caller evidence."""
    turns = call.get("transcript_object")
    if isinstance(turns, list):
        return "\n".join(turn.get("content", "") for turn in turns if turn.get("role") == "user")[
            -20_000:
        ]
    transcript = call.get("transcript") or ""
    if re.search(r"^(?:Agent|User):", transcript, re.MULTILINE | re.IGNORECASE):
        current, lines = None, []
        for line in transcript.splitlines():
            speaker = re.match(r"^(Agent|User):\s*(.*)", line, re.IGNORECASE)
            if speaker:
                current = speaker[1].lower()
                line = speaker[2]
            if current == "user":
                lines.append(line)
        return "\n".join(lines)[-20_000:]
    return (transcript or args.get("summary") or "")[-20_000:]


class LiveStore:
    def __init__(self, connect, *, salt: str):
        self.connect = connect
        self.salt = salt

    def initialize(self):
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS analysis_call_links(
                    call_id TEXT PRIMARY KEY,
                    consent_hash TEXT,
                    caller_hash TEXT,
                    language TEXT,
                    zone_id TEXT,
                    predicted_severity TEXT,
                    predicted_category TEXT,
                    priority INTEGER,
                    updated REAL NOT NULL
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS analysis_links_consent_hash
                ON analysis_call_links(consent_hash)
            """)

    def observe(self, payload: dict):
        """Called only AFTER the existing signed handler has accepted the request."""
        if len(self.salt.encode()) < 16:
            return
        call = payload.get("call") or payload.get("chat") or {}
        call_id = call.get("call_id") or call.get("chat_id")
        if not isinstance(call_id, str) or not call_id or len(call_id) > 200:
            return
        phone = (
            call.get("to_number")
            if call.get("direction") == "outbound"
            else call.get("from_number")
        )
        if (
            not isinstance(phone, str)
            or not re.fullmatch(r"\+?[\d ().-]+", phone)
            or not 10 <= len(re.sub(r"\D", "", phone)) <= 15
        ):
            phone = None
        # Must match the operational consents hash exactly; never use caller_last4.
        consent_hash = hashlib.sha256(str(phone or call_id).encode()).hexdigest()
        caller = pseudonym(str(phone), self.salt) if phone else None
        args = payload.get("args") or {}
        dynamic = call.get("retell_llm_dynamic_variables") or call.get("dynamic_variables") or {}
        zone = args.get("zone_id") or dynamic.get("zone_id")
        if zone not in {z["id"] for z in load_config("zones")}:
            zone = None
        language = args.get("language") or dynamic.get("language")
        language = language_code(language) if isinstance(language, str) else None
        label = None
        text = caller_text(call, args)
        if args.get("hazard") or text:
            fields = {
                key: args[key]
                for key in (
                    "hazard",
                    "category",
                    "vulnerability",
                    "severity",
                    "immediate_danger",
                    "injured_or_trapped",
                    "needs_assistance",
                    "language",
                )
                if key in args
            }
            label = classify(text, fields)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not phone:
                existing = connection.execute(
                    "SELECT consent_hash FROM analysis_call_links WHERE call_id=?", (call_id,)
                ).fetchone()
                consent_hash = existing["consent_hash"] if existing else consent_hash
            consent = connection.execute(
                "SELECT analytics FROM consents WHERE caller_hash=?", (consent_hash,)
            ).fetchone()
            if not consent or consent["analytics"] != 1:
                label = None
                caller = None
                if consent and consent["analytics"] == 0:
                    connection.execute(
                        """
                        UPDATE analysis_call_links SET caller_hash=NULL,
                            predicted_severity=NULL,predicted_category=NULL,priority=NULL
                        WHERE consent_hash=?
                    """,
                        (consent_hash,),
                    )
            connection.execute(
                """
                INSERT INTO analysis_call_links VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(call_id) DO UPDATE SET
                    consent_hash=COALESCE(excluded.consent_hash,analysis_call_links.consent_hash),
                    caller_hash=COALESCE(excluded.caller_hash,analysis_call_links.caller_hash),
                    language=COALESCE(excluded.language,analysis_call_links.language),
                    zone_id=COALESCE(excluded.zone_id,analysis_call_links.zone_id),
                    predicted_severity=CASE
                        WHEN analysis_call_links.predicted_severity IS NULL
                            THEN excluded.predicted_severity
                        WHEN excluded.predicted_severity IS NULL
                            THEN analysis_call_links.predicted_severity
                        ELSE MIN(analysis_call_links.predicted_severity,excluded.predicted_severity)
                    END,
                    predicted_category=CASE
                        WHEN excluded.predicted_severity IS NOT NULL AND
                            (analysis_call_links.predicted_severity IS NULL OR
                             excluded.predicted_severity<=analysis_call_links.predicted_severity)
                        THEN excluded.predicted_category
                        ELSE analysis_call_links.predicted_category
                    END,
                    priority=MAX(COALESCE(excluded.priority,0),
                                 COALESCE(analysis_call_links.priority,0)),
                    updated=excluded.updated
            """,
                (
                    call_id,
                    consent_hash,
                    caller,
                    language,
                    zone,
                    label.severity if label else None,
                    label.category if label else None,
                    score_priority(label) if label else None,
                    time.time(),
                ),
            )

    def dashboard(self, *, now: float) -> dict:
        with self.connect() as connection:
            connection.execute("BEGIN")
            calls = [
                dict(row) for row in connection.execute("SELECT call_id,started,ended FROM calls")
            ]
            reports = [
                dict(row)
                for row in connection.execute(
                    "SELECT dedupe,severity,category,language,source FROM reports"
                )
            ]
            links = {
                row["call_id"]: dict(row)
                for row in connection.execute("SELECT * FROM analysis_call_links")
            }
            consents = {
                row["caller_hash"]: row["analytics"]
                for row in connection.execute("SELECT caller_hash,analytics FROM consents")
            }
        by_call = {}
        for report in reports:
            dedupe = report.get("dedupe") or ""
            call_id = dedupe.split(":p0:", 1)[0] if ":p0:" in dedupe else dedupe.rsplit(":", 1)[0]
            by_call.setdefault(call_id, []).append(report)
        rows, missing_consent, opted_out = [], 0, 0
        for call in calls:
            call_id = call["call_id"]
            link = links.get(call_id, {})
            consent = consents.get(link.get("consent_hash"))
            missing_consent += consent is None
            opted_out += consent == 0
            related = sorted(by_call.get(call_id, []), key=lambda r: r.get("severity") or "P9")
            report = related[0] if related else {}
            rows.append(
                {
                    "call_id": call_id,
                    "caller_hash": link.get("caller_hash"),
                    "consent_analytics": consent == 1,
                    "language": report.get("language") or link.get("language"),
                    "zone_id": link.get("zone_id"),
                    "severity": report.get("severity"),
                    "category": report.get("category"),
                    "started_at": call.get("started"),
                    "ended_at": call.get("ended"),
                    "ts": call.get("started"),
                    "outcome": "unknown",
                    "source": report.get("source", "observed"),
                }
            )
        configured = len(self.salt.encode()) >= 16
        records = prepare_records(rows, salt=self.salt) if configured else []
        metrics = snapshot(records, now=now, prompt_version="live")
        metrics["excluded_consent_or_unknown"] = len(calls) - len(records)
        eligible_ids = {row["call_id"] for row in rows if row["consent_analytics"]}
        predictions = (
            [
                links[call_id]
                for call_id in eligible_ids
                if call_id in links and links[call_id].get("predicted_severity") in SEVERITIES
            ]
            if configured
            else []
        )
        categories = Counter(
            r["category"]
            for r in rows
            if configured and r["consent_analytics"] and r["category"] in CATEGORIES
        )
        languages = Counter(r["language"] for r in records)
        return {
            "schema_version": 1,
            "mode": "live",
            "configured": configured,
            "metrics": metrics,
            "coverage": {
                "operational_calls": len(calls),
                "analytics_calls": len(records),
                "missing_consent_link": missing_consent,
                "opted_out_calls": opted_out,
                "calls_with_zone": sum(r["zone_id"] != "unknown" for r in records),
            },
            "categories": dict(categories),
            "languages": dict(languages),
            "triage_predictions": dict(Counter(r["predicted_severity"] for r in predictions)),
            "limitations": [
                "Only calls with a recorded consent link contribute to analytics.",
                "Predictions are separate from operational triage and human ground truth.",
                "Zone detection needs explicit reviewed zone assignments.",
            ],
        }
