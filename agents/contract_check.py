#!/usr/bin/env python3
"""Check that a running backend accepts every call our Retell agents will make (no Retell, no cost).

    python agents/contract_check.py --base-url http://localhost:8000 --key <the key the backend verifies with>

Sends signed requests shaped exactly like Retell's: the inbound webhook, and every custom function in
tools.json with a realistic example ({name, call, args} body, X-Retell-Signature over the raw body).
Fails on any non-2xx, a missing signature check, or responses the prompts can't use.
Needs `pip install retell-sdk` for the signer.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

from retell.lib.webhook_auth import make_secure_webhooks, symmetric_get_signer, symmetric_get_verifier

from retell_api import AGENTS_DIR

SIGN = make_secure_webhooks(symmetric_get_signer, symmetric_get_verifier)["sign"]
CALL = {"call_id": "call_contract_check", "from_number": "+15555550100", "to_number": "+15555550199",
        "transcript": "User: there's smoke coming from my neighbor's garage"}
EXAMPLES = {
    "submit_report": {"hazard": "smoke from garage", "location_text": "Lake Ave and Altadena Dr", "people_at_risk": 2,
                      "injured_or_trapped": False, "vulnerability": ["wheelchair"], "language": "es", "drill_code": ""},
    "flag_urgent": {"reason": "trapped", "keyword": "mi abuela está atrapada"},
    "route_to_human": {"needs": ["evac_logistics", "lang:es"], "language": "es", "severity": "P1", "summary": "Smoke next door, wheelchair user"},
    "schedule_callback": {"reason": "no_responder_available", "preferred_time": ""},
    "lookup_info": {"question": "where is the nearest open shelter", "zone_id": ""},
    "create_request": {"type": "errand", "details": "pick up medication", "location_text": "Exposition Park"},
    "set_reminder": {"when": "tomorrow 9 AM", "message": "take medication"},
    "enroll_checkin": {"person_name": "Rosa", "person_phone": "5555550123", "language": "es", "needs": ["mobility"],
                       "frequency": "weekly", "enrolled_by": "granddaughter"},
    "notify_contact": {"contact_name": "Ana", "contact_phone": "5555550124", "message": "Rosa is safe at the shelter", "consent": True},
    "check_status": {"code": "D-417", "phone_last4": "0100"},
    "opt_out": {"scope": "calls"},
    "register_volunteer": {"name": "Min", "skills": ["translation"], "languages": ["ko", "en"], "availability": "evenings", "area": "Koreatown"},
    "start_form": {"form_type": "maintenance_request", "known_fields": {"location": "Birnkrant 214", "issue": "heater blows cold air"}},
    "fill_form": {"case_code": "M-102", "fields": {"best_time": "tomorrow morning"}},
    "submit_form": {"case_code": "M-102", "confirmed": True},
    "request_escort": {"from": "Leavey Library", "to": "Parkside", "time": "now"},
    "book_appointment": {"with_skill": "mental_health", "preferred_times": ["tomorrow afternoon"]},
    "send_link": {"code": "D-417"},
    "record_consent": {"feature_consent": True, "analytics_consent": True},
    "request_location": {},
}
# Response fields the prompts rely on (00_CONTRACTS.md).
EXPECT = {
    "submit_report": ["report_id", "cluster_match", "severity"],
    "flag_urgent": ["instruction"],
    "route_to_human": ["oncall_number"],
    "schedule_callback": ["code", "eta_text"],
    "lookup_info": ["answer"],
    "start_form": ["case_code", "next_fields"],
    "fill_form": ["missing", "invalid", "complete"],
    "submit_form": ["code", "next_step_text"],
    "check_status": ["status_text"],
}


def post(url, body, key, signature=None):
    raw = json.dumps(body)
    req = urllib.request.Request(url, data=raw.encode(), method="POST", headers={
        "Content-Type": "application/json", "X-Retell-Signature": signature or SIGN(raw, key)})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            text = r.read().decode()
            return r.status, (json.loads(text) if text.strip() else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", required=True)
    p.add_argument("--key", required=True, help="the API key the backend verifies signatures with (webhook-badged key)")
    a = p.parse_args()
    base = a.base_url.rstrip("/")
    tools = json.loads((AGENTS_DIR / "tools.json").read_text())
    problems = []

    inbound = {"event": "call_inbound", "call_inbound": {"call_id": CALL["call_id"], "from_number": CALL["from_number"], "to_number": CALL["to_number"]}}
    code, resp = post(f"{base}/retell/inbound", inbound, a.key)
    ok = code == 200 and isinstance(resp, dict) and "call_inbound" in resp
    dv = (resp or {}).get("call_inbound", {}).get("dynamic_variables", {}) if ok else {}
    if ok and any(not isinstance(v, str) for v in dv.values()):
        ok = False
        problems.append("inbound: dynamic_variables must all be strings")
    print(f"{'PASS' if ok else 'FAIL'} inbound webhook ({code})")
    if not ok:
        problems.append(f"inbound: {code} {str(resp)[:120]}")
    code, _ = post(f"{base}/retell/inbound", inbound, a.key, signature="v=1,d=forged")
    print(f"{'PASS' if code in (401, 403) else 'FAIL'} inbound rejects a forged signature ({code})")
    if code not in (401, 403):
        problems.append("inbound accepts forged signatures")

    for name, tool in tools.items():
        if tool.get("type") != "custom":
            continue
        code, resp = post(f"{base}/retell/fn/{name}", {"name": name, "call": CALL, "args": EXAMPLES.get(name, {})}, a.key)
        issue = ""
        if not 200 <= code < 300:
            issue = f"HTTP {code}"
        elif name in EXPECT:
            missing = [f for f in EXPECT[name] if not isinstance(resp, dict) or f not in resp]
            if missing:
                issue = f"missing fields {missing}"
        if name == "submit_report" and isinstance(resp, dict) and resp.get("cluster_match") and "know" not in resp["cluster_match"].lower():
            issue = f"cluster_match should be '' unless there's a real match (got {resp['cluster_match']!r})"
        print(f"{'FAIL' if issue else 'PASS'} {name:20} {issue or str(resp)[:90]}")
        if issue:
            problems.append(f"{name}: {issue}")

    print(f"\n{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
