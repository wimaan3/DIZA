#!/usr/bin/env python3
"""Send an approved alert as automated calls to opted-in contacts (Retell batch call).

    python agents/send_alert.py --alert agents/alerts/drill_altadena_evac_warning.yaml --contacts agents/alerts/team.csv          # dry run
    python agents/send_alert.py --alert ... --contacts ... --send                                                                 # really call

Safety rails (never-automate rules + TCPA):
- A person must approve the exact text: the alert file needs approved_by and approved_at.
- Dry run by default; --send places real calls. At most --max contacts (default 10).
- mode: drill is spoken as "This is a drill" first. mode: live also needs --live.
- Calls only between 8 AM and 9 PM Pacific unless --emergency.
- Contacts are opted-in people only (CSV: name,phone,language[,opted_out]); CSVs are git-ignored.
- Reserves inbound capacity so the line keeps answering during the batch.
Each call uses the `alert` agent, which reads the alert word for word, answers questions, and routes
anyone who needs help to intake → a person or a callback.
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys

from retell_api import AGENTS_DIR, RetellError, call, items, load_dotenv, load_ids

LOCALES = {"ko": "ko-KR", "zh": "zh-CN", "hy": "hy-AM", "tl": "fil-PH"}  # en/es use the agent's own languages
DRILL_PREFIX = {"en": "This is a drill for a USC student project. ", "es": "Esto es un simulacro de un proyecto estudiantil de USC. "}
INTRO = {"en": "Hi {name}, this is the DIZA Community Line with an urgent safety message for {zone}.",
         "es": "Hola {name}, le llama la Línea Comunitaria DIZA con un mensaje urgente de seguridad para {zone}."}


def load_alert(path):
    import yaml
    alert = yaml.safe_load(open(path))
    problems = [k for k in ("id", "mode", "zone_name", "source", "approved_by", "approved_at") if not str(alert.get(k) or "").strip()]
    if "en" not in (alert.get("messages") or {}):
        problems.append("messages.en")
    if problems:
        sys.exit(f"Alert {path} is missing {', '.join(problems)}. A person must approve the exact text before sending.")
    if alert["mode"] not in ("drill", "live"):
        sys.exit("mode must be drill or live")
    return alert


def load_contacts(path, limit):
    rows, skipped = [], []
    for row in csv.DictReader(open(path, newline="")):
        phone = re.sub(r"[^\d+]", "", row.get("phone", ""))
        if (row.get("opted_out") or "").strip().lower() in ("1", "true", "yes"):
            skipped.append((row.get("name"), "opted out"))
        elif not re.fullmatch(r"\+1\d{10}", phone):
            skipped.append((row.get("name"), "phone is not +1XXXXXXXXXX"))
        else:
            rows.append({"name": (row.get("name") or "").strip(), "phone": phone, "language": (row.get("language") or "en").strip().lower()})
    if len(rows) > limit:
        sys.exit(f"{len(rows)} contacts exceeds --max {limit}. Raise --max deliberately if you mean it.")
    return rows, skipped


def task_for(contact, alert, agent_id, version):
    lang = contact["language"]
    text = alert["messages"].get(lang) or alert["messages"]["en"]
    used_lang = lang if lang in alert["messages"] else "en"
    message = text["message"].strip()
    first = contact["name"].split(" ")[0] if contact["name"] else ""
    intro = INTRO.get(used_lang, INTRO["en"]).format(name=first or ("there" if used_lang != "es" else ""), zone=alert["zone_name"])
    task = {
        "to_number": contact["phone"],
        "override_agent_id": agent_id,
        "override_agent_version": version,
        "retell_llm_dynamic_variables": {
            "caller_name": first or "there", "alert_intro": re.sub(r"\s+,", ",", intro),
            "drill_prefix": DRILL_PREFIX.get(used_lang, DRILL_PREFIX["en"]) if alert["mode"] == "drill" else "",
            "language": used_lang, "zone_name": alert["zone_name"], "alert_message": message,
            "alert_action": text.get("action", "").strip(), "alert_source": alert["source"],
            "alert_id": alert["id"], "drill_mode": "true" if alert["mode"] == "drill" else "false",
        },
        "metadata": {"alert_id": alert["id"], "approved_by": alert["approved_by"]},
    }
    if used_lang in LOCALES:
        task["agent_override"] = {"agent": {"language": LOCALES[used_lang]}}
    return task


def mask(phone):
    return phone[:-4].replace(phone[2:-4], "•" * len(phone[2:-4])) + phone[-4:]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--alert", required=True)
    p.add_argument("--contacts", required=True)
    p.add_argument("--send", action="store_true", help="place real calls (default: dry run)")
    p.add_argument("--live", action="store_true", help="required for mode: live alerts")
    p.add_argument("--emergency", action="store_true", help="skip the 8 AM-9 PM calling window (emergency-purpose calls)")
    p.add_argument("--max", type=int, default=10)
    p.add_argument("--version", default="", help="alert agent version (default: latest_published, or the draft if nothing is published yet)")
    a = p.parse_args()
    load_dotenv()

    alert = load_alert(a.alert)
    if alert["mode"] == "live" and not a.live:
        sys.exit("This is a LIVE alert. Pass --live only if officials issued it and the team approved sending.")
    contacts, skipped = load_contacts(a.contacts, a.max)
    ids = load_ids()
    if "alert" not in ids:
        sys.exit("No alert agent yet: run push.py first")
    if not a.version:
        # 'latest' includes drafts, so a staging push would change what prod alerts say. Prefer the published version.
        versions = items(call("GET", f"/list-agent-versions/{ids['alert']['agent_id']}?limit=50"))
        a.version = "latest_published" if any(v.get("is_published") for v in versions) else "latest"
        if a.version == "latest":
            print("! alert agent has no published version yet: using the draft ('latest')")
    from_number = os.environ.get("RETELL_FROM_NUMBER")
    if not from_number:
        sys.exit("Set RETELL_FROM_NUMBER (the DIZA line) to send from.")

    body = {
        "name": f"{alert['id']} ({alert['mode']}) approved by {alert['approved_by']}",
        "from_number": from_number,
        "tasks": [task_for(c, alert, ids["alert"]["agent_id"], a.version) for c in contacts],
        "reserved_concurrency": 8,  # keep inbound answering during the batch
    }
    if not a.emergency:
        body["call_time_window"] = {"windows": [{"start": 8 * 60, "end": 21 * 60}], "timezone": "America/Los_Angeles"}

    print(f"Alert {alert['id']} [{alert['mode'].upper()}] for {alert['zone_name']}, approved by {alert['approved_by']} at {alert['approved_at']}")
    for t in body["tasks"]:
        v = t["retell_llm_dynamic_variables"]
        print(f"  → {mask(t['to_number'])} ({v['language']}): {v['drill_prefix']}{v['alert_intro']} {v['alert_message']} {v['alert_action']}")
    missing = sorted({c["language"] for c in contacts} - set(alert["messages"]))
    if missing:
        print(f"  ⚠ no approved text in {', '.join(missing)}: those contacts hear the English text. Add messages.<lang> to the alert file.")
    for name, why in skipped:
        print(f"  skipped {name}: {why}")
    if not a.send:
        print(f"\nDRY RUN: {len(body['tasks'])} call(s) would be placed. Add --send to call.")
        return
    resp = call("POST", "/create-batch-call", body)
    print(f"\nSENT batch {resp.get('batch_call_id')}: {len(body['tasks'])} call(s)")
    with open(AGENTS_DIR / "alerts" / "SENT.md", "a") as f:  # counts only, no phone numbers
        f.write(f"- {datetime.datetime.now().isoformat(timespec='minutes')} · {alert['id']} [{alert['mode']}] · "
                f"{len(body['tasks'])} calls · approved by {alert['approved_by']} · batch {resp.get('batch_call_id')}\n")


if __name__ == "__main__":
    try:
        main()
    except RetellError as e:
        sys.exit(f"Retell error: {e}")
