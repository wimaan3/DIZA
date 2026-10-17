#!/usr/bin/env python3
"""Create/update the SMS chat agent (people text the DIZA number) and bind it to the number's inbound SMS.

    python agents/sms_push.py            # uses PUBLIC_BASE_URL and RETELL_FROM_NUMBER from env / .env

Reuses push.py's LLM builder (shared rules + tools.json), so texting and calling follow the same rules.
"""
import os
import sys

from push import build_llm, resolve_env
from retell_api import RetellError, call, load_dotenv, load_ids, save_ids


def main():
    load_dotenv()
    env, values = resolve_env("staging", allow_missing=True)
    ids = load_ids()
    llm_body = build_llm("sms", ids, env, values)
    if "sms" not in ids:
        llm = call("POST", "/create-retell-llm", llm_body)
        agent = call("POST", "/create-chat-agent", {"agent_name": "diza-sms", "response_engine": {"type": "retell-llm", "llm_id": llm["llm_id"]}})
        ids["sms"] = {"chat_agent_id": agent["agent_id"], "llm_id": llm["llm_id"]}
        save_ids(ids)
        print(f"+ created sms chat agent {agent['agent_id']}")
    else:
        call("PATCH", f"/update-retell-llm/{ids['sms']['llm_id']}", llm_body)
    call("PATCH", f"/update-chat-agent/{ids['sms']['chat_agent_id']}", {
        "agent_name": "diza-sms", "language": "multi", "end_chat_after_silence_ms": 3600000,
        "webhook_url": f"{values['BASE_URL']}/retell/webhook", "data_storage_setting": "everything_except_pii",
        "data_storage_retention_days": 7})
    print(f"= sms chat agent updated ({len(llm_body['general_tools'])} tools)")
    number = os.environ.get("RETELL_FROM_NUMBER")
    if number:
        try:
            call("PATCH", f"/update-phone-number/{number.replace('+', '%2B')}",
                 {"inbound_sms_agents": [{"agent_id": ids["sms"]["chat_agent_id"], "weight": 1}]})
            print("= number inbound SMS -> diza-sms")
        except RetellError as e:
            # US numbers need A2P 10DLC registration (Retell dashboard) before they can receive texts.
            print(f"! number not bound for SMS yet (needs A2P registration): {str(e)[:120]}")
            print("  The /text web chat on the backend uses this agent meanwhile.")


if __name__ == "__main__":
    try:
        main()
    except RetellError as e:
        sys.exit(f"Retell error: {e}")
