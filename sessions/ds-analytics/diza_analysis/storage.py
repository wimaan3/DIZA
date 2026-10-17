"""Read-only adapter for the currently deployed CS#2 SQLite schema."""

import sqlite3
from collections.abc import Mapping
from pathlib import Path


def read_sqlite(path: str | Path, *, consent_by_call: Mapping | None = None) -> tuple[list, dict]:
    """Read one consistent snapshot, never altering or creating an operational DB.

    The current schema stores only caller_last4 on calls. That is insufficient to
    join consents safely. Missing direct consent requires a trusted per-call map;
    we never infer consent, a zone, ground truth, or an AI-resolution outcome.
    """
    path = Path(path).resolve(strict=True)
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "calls" not in tables:
            raise ValueError("SQLite database has no calls table")
        calls = [dict(row) for row in connection.execute("SELECT * FROM calls")]
        reports = (
            [dict(row) for row in connection.execute("SELECT * FROM reports")]
            if "reports" in tables
            else []
        )
    finally:
        connection.close()
    by_call = {}
    for report in reports:
        dedupe = report.get("dedupe", "")
        call_id = report.get("call_id") or (
            dedupe.split(":p0:", 1)[0] if ":p0:" in dedupe else dedupe.rsplit(":", 1)[0]
        )
        by_call.setdefault(call_id, []).append(report)
    records, missing_consent = [], 0
    for call in calls:
        call_id = call.get("call_id", call.get("id"))
        related = sorted(by_call.get(call_id, []), key=lambda r: r.get("severity") or "P9")
        report = related[0] if related else {}
        consent = call.get("consent_analytics")
        # A persisted opt-out cannot be overridden by a supplementary map.
        if consent is None:
            consent = (consent_by_call or {}).get(call_id)
        missing_consent += consent is None
        records.append(
            {
                "call_id": call_id,
                "caller_hash": call.get("from_hash"),
                "consent_analytics": consent,
                "started_at": call.get("started_at", call.get("started")),
                "ended_at": call.get("ended_at", call.get("ended")),
                "ts": call.get("started_at", call.get("started")),
                "severity": report.get("severity", call.get("severity")),
                "category": report.get("category", call.get("category")),
                "language": report.get("language", call.get("language")),
                "zone_id": call.get("zone_id", report.get("zone_id")),
                "outcome": call.get("outcome", "unknown"),
                "source": report.get("source", "observed"),
                "verified": bool(report.get("verified", False)),
            }
        )
    return records, {
        "adapter": "cs2_sqlite_readonly",
        "calls_observed": len(calls),
        "reports_observed": len(reports),
        "calls_missing_consent": missing_consent,
        "limitations": [
            "Legacy caller_last4 cannot establish caller identity or consent linkage.",
            "Zone, routing acceptance, outcomes and evaluation labels are used only when recorded.",
        ],
    }
