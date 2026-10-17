#!/usr/bin/env python3
"""Snapshot what's live in Retell into agents/remote/, so dashboard edits show up as a git diff.

    python agents/pull.py

Writes remote/<name>.agent.json and remote/<name>.llm.json for every agent in retell.ids.json.
If something changed in the dashboard, copy the change into the source files
(prompts/*.md, tools.json, <name>.*.json) and push again; remote/ is only the mirror.
"""
import json
import sys

from retell_api import AGENTS_DIR, RetellError, call, load_dotenv, load_ids

# Fields that change on every save and would only add noise to diffs.
VOLATILE = {"last_modification_timestamp", "version", "is_published", "version_title", "llm_websocket_url"}


def clean(obj):
    return {k: v for k, v in sorted(obj.items()) if k not in VOLATILE}


def main():
    load_dotenv()
    ids = load_ids()
    if not ids:
        sys.exit("retell.ids.json is empty: run push.py first")
    out = AGENTS_DIR / "remote"
    out.mkdir(exist_ok=True)
    for name, ref in ids.items():
        agent = call("GET", f"/get-agent/{ref['agent_id']}")
        llm = call("GET", f"/get-retell-llm/{ref['llm_id']}")
        (out / f"{name}.agent.json").write_text(json.dumps(clean(agent), indent=2, ensure_ascii=False) + "\n")
        (out / f"{name}.llm.json").write_text(json.dumps(clean(llm), indent=2, ensure_ascii=False) + "\n")
        print(f"pulled {name}: agent v{agent.get('version')} published={agent.get('is_published')}")
    print("Review with: git diff agents/remote/")


if __name__ == "__main__":
    try:
        main()
    except RetellError as e:
        sys.exit(f"Retell error: {e}")
