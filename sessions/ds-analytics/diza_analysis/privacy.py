"""Allowlist-based pseudonymization; public output contains delayed aggregates only."""

import hashlib
import hmac
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence

from .config import load_config
from .timeutil import timestamp
from .triage import CATEGORIES, SEVERITIES, language_code

OUTCOMES = {
    "ai_resolved",
    "human_transferred",
    "callback_queued",
    "safety_911_988",
    "abandoned",
    "voicemail",
    "busy",
    "unknown",
}


def pseudonym(value: str, salt: str, *, domain: str = "caller") -> str:
    if len(salt.encode()) < 16:
        raise ValueError("Analytics salt must contain at least 16 bytes")
    return hmac.new(salt.encode(), f"{domain}:{value}".encode(), hashlib.sha256).hexdigest()


def analytics_allowed(value) -> bool:
    return value is True or value == 1 or value == "true"


def anonymize_row(row: Mapping, *, salt: str) -> dict | None:
    """Drop opted-out records and ALL free text, identities, exact locations and extra keys.

    This is pseudonymization, not a claim that individual records are anonymous.
    Missing consent is excluded until the operational adapter can establish it.
    """
    if not analytics_allowed(row.get("consent_analytics")):
        return None
    phone = row.get("phone") or (
        row.get("to_number") if row.get("direction") == "outbound" else row.get("from_number")
    )
    identity = re.sub(r"\D", "", str(phone)) if phone else None
    if identity and len(identity) == 10:
        identity = "1" + identity
    identity = identity or row.get("caller_hash") or row.get("from_hash")
    caller = pseudonym(str(identity), salt) if identity else None
    zones = {zone["id"] for zone in load_config("zones")}
    language = language_code(str(row.get("language") or "und"))
    if not re.fullmatch(r"[a-z]{2,3}", language):
        language = "und"
    result = {
        "caller_hash": caller,
        "zone_id": row.get("zone_id") if row.get("zone_id") in zones else "unknown",
        "language": language,
        "category": row.get("category") if row.get("category") in CATEGORIES else "other",
        "severity": row.get("severity") if row.get("severity") in SEVERITIES else None,
        "outcome": row.get("outcome") if row.get("outcome") in OUTCOMES else "unknown",
        "source": "synthetic" if row.get("source") in {"synthetic", "simulated"} else "observed",
        "consent_analytics": True,
        "verified": row.get("verified") is True,
    }
    for key in ("id", "call_id"):
        if row.get(key):
            result[key] = pseudonym(str(row[key]), salt, domain="record")
    for key in ("started_at", "ended_at", "human_at", "ts"):
        result[key] = timestamp(row.get(key))
    expected = row.get("expected_severity")
    result["expected_severity"] = expected if expected in SEVERITIES else None
    for key in ("routing_match", "form_complete", "safety_compliant", "reached_via_contact"):
        result[key] = row[key] if isinstance(row.get(key), bool) else None
    return result


def public_aggregates(rows: Sequence[Mapping], *, now, k: int = 5, delay_min: int = 10) -> list:
    """Count each cell's contributors, never substituting call counts for people.

    No totals or suppressed-cell counts are returned, avoiding subtraction leaks.
    Only verified, consented observations with a caller pseudonym can contribute.
    """
    if k < 5 or delay_min < 10:
        raise ValueError("Public aggregates require k >= 5 and delay >= 10 minutes")
    now = timestamp(now)
    if now is None:
        raise ValueError("now is required")
    cells = defaultdict(list)
    for row in rows:
        ts = timestamp(row.get("ts") if row.get("ts") is not None else row.get("started_at"))
        if (
            not analytics_allowed(row.get("consent_analytics"))
            or not row.get("caller_hash")
            or row.get("verified") is not True
            or ts is None
            or ts > now - delay_min * 60
        ):
            continue
        zone, category, severity = row.get("zone_id"), row.get("category"), row.get("severity")
        if zone not in {z["id"] for z in load_config("zones")}:
            continue
        if category not in CATEGORIES or severity not in SEVERITIES:
            continue
        source = "synthetic" if row.get("source") in {"synthetic", "simulated"} else "observed"
        key = (zone, category, severity, source)
        cells[key].append(row)
    output = []
    for (zone, category, severity, source), group in sorted(cells.items()):
        distinct = len({r["caller_hash"] for r in group})
        if distinct >= k:
            output.append(
                {
                    "zone_id": zone,
                    "category": category,
                    "severity": severity,
                    "source": source,
                    "distinct_callers": distinct,
                    "reports": len(group),
                }
            )
    return output
