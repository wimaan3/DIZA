#!/usr/bin/env python3
"""Push the agents in this folder to Retell. Git is the source of truth.

    python agents/push.py --env staging            # update drafts only
    python agents/push.py --env prod               # update drafts, then publish
    python agents/push.py --env staging --dry-run  # print payloads, call nothing
    python agents/push.py --env staging --only inbound crisis

For each agent name in AGENT_NAMES:
  1. create the Retell LLM + agent if retell.ids.json doesn't have them yet (ids are saved, commit them)
  2. build the LLM: prompts/<files> joined + tools.json entries named in `_tools`
  3. update-retell-llm, then update-agent (on a fresh draft if the latest version is published)
  4. prod only: publish-agent-version, append to CHANGELOG.md
If RETELL_FROM_NUMBER is set, the number is bound to inbound (inbound) / checkin (outbound),
with the inbound webhook and fallback number.
"""
import argparse
import copy
import datetime
import json
import os
import subprocess
import sys

from retell_api import (AGENT_NAMES, AGENTS_DIR, RetellError, call, items, load_dotenv,
                        load_ids, save_ids, substitute)

UNSET_BASE_URL = "https://backend-not-configured.invalid"


def read_json(name):
    return json.loads((AGENTS_DIR / name).read_text())


def git_rev():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=AGENTS_DIR, text=True).strip()
        dirty = subprocess.call(["git", "diff", "--quiet", "HEAD", "--", "."], cwd=AGENTS_DIR) != 0
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def resolve_env(env_name, allow_missing):
    env = read_json(f"envs/{env_name}.json")
    missing = set()
    values = substitute(env["values"], dict(os.environ), missing)
    if "PUBLIC_BASE_URL" in missing:
        print(f"! PUBLIC_BASE_URL not set: function and webhook URLs will point at {UNSET_BASE_URL}")
        values["BASE_URL"] = UNSET_BASE_URL
        missing.discard("PUBLIC_BASE_URL")
    for name in sorted(missing):
        if not allow_missing:
            sys.exit(f"Missing env var {name} (needed by envs/{env_name}.json). "
                     f"Set it in your shell or .env, or pass --allow-missing.")
        print(f"! {name} not set: leaving it empty")
    values = {k: ("" if "${" in v else v) for k, v in values.items()}
    return env, values


def build_llm(name, ids, env, values):
    spec = read_json(f"{name}.llm.json")
    tools_catalog = read_json("tools.json")
    prompt = "\n\n".join((AGENTS_DIR / "prompts" / f).read_text().strip() for f in spec["_prompt_files"])
    tools = []
    for tool_name in spec["_tools"]:
        tool = copy.deepcopy(tools_catalog[tool_name])
        if tool.get("type") == "agent_swap":
            target = tool["agent_id"].removeprefix("@agent:")
            if target not in ids:
                raise RetellError(f"{name}: tool {tool_name} swaps to '{target}', which has no id yet")
            tool["agent_id"] = ids[target]["agent_id"]
            tool["agent_version"] = env["swap_version"]
        tools.append(tool)
    body = {k: v for k, v in spec.items() if not k.startswith("_")}
    body["general_prompt"] = prompt
    body["general_tools"] = tools
    return check_placeholders(name, substitute(body, values, set()))


def build_agent(name, ids, values):
    spec = read_json(f"{name}.agent.json")
    body = {k: v for k, v in spec.items() if not k.startswith("_")}
    body["response_engine"] = {"type": "retell-llm", "llm_id": ids[name]["llm_id"]}
    return check_placeholders(name, substitute(body, values, set()))


def check_placeholders(name, body):
    text = json.dumps(body)
    if "${" in text:
        raise RetellError(f"{name}: unresolved placeholder in payload: ...{text[text.index('${'):][:60]}")
    return body


def ensure_exists(name, ids):
    if name in ids:
        return
    spec = read_json(f"{name}.agent.json")
    llm = call("POST", "/create-retell-llm", {"model": "gpt-4.1-mini", "general_prompt": "placeholder (push.py fills this in)"})
    agent = call("POST", "/create-agent", {
        "agent_name": spec["agent_name"], "voice_id": spec["voice_id"],
        "response_engine": {"type": "retell-llm", "llm_id": llm["llm_id"]},
    })
    ids[name] = {"agent_id": agent["agent_id"], "llm_id": llm["llm_id"]}
    save_ids(ids)
    print(f"+ created {name}: agent {agent['agent_id']}, llm {llm['llm_id']}")


def latest_version(agent_id):
    versions = items(call("GET", f"/list-agent-versions/{agent_id}?limit=1&sort_order=descending"))
    return versions[0] if versions else call("GET", f"/get-agent/{agent_id}")


def push_one(name, ids, env, values, rev, dry_run):
    llm_body = build_llm(name, ids, env, values)
    agent_body = build_agent(name, ids, values)
    agent_body["version_title"] = rev
    if dry_run:
        print(f"--- {name}.llm\n{json.dumps(llm_body, indent=2, ensure_ascii=False)}")
        print(f"--- {name}.agent\n{json.dumps(agent_body, indent=2, ensure_ascii=False)}")
        return None
    agent_id, llm_id = ids[name]["agent_id"], ids[name]["llm_id"]
    latest = latest_version(agent_id)
    if latest.get("is_published"):
        call("POST", f"/create-agent-version/{agent_id}", {"base_version": latest["version"]})
    call("PATCH", f"/update-retell-llm/{llm_id}", llm_body)
    call("PATCH", f"/update-agent/{agent_id}", agent_body)
    draft = latest_version(agent_id)
    print(f"= {name}: draft v{draft['version']} updated ({len(llm_body['general_tools'])} tools)")
    if env["publish"]:
        call("POST", f"/publish-agent-version/{agent_id}", {"version": draft["version"], "version_title": rev})
        print(f"^ {name}: published v{draft['version']}")
    return draft["version"]


def bind_number(ids, env, values, dry_run):
    number = os.environ.get("RETELL_FROM_NUMBER")
    if not number:
        print("· RETELL_FROM_NUMBER not set: skipping phone-number binding")
        return
    version = env["swap_version"]
    body = {
        "inbound_agents": [{"agent_id": ids["inbound"]["agent_id"], "agent_version": version, "weight": 1}],
        "outbound_agents": [{"agent_id": ids["checkin"]["agent_id"], "agent_version": version, "weight": 1}],
        "inbound_webhook_url": f"{values['BASE_URL']}/retell/inbound",
        "nickname": "DIZA line",
    }
    if os.environ.get("RETELL_FALLBACK_NUMBER"):
        body["fallback_number"] = os.environ["RETELL_FALLBACK_NUMBER"]
    if dry_run:
        print(f"--- phone number\n{json.dumps(body, indent=2)}")
        return
    call("PATCH", f"/update-phone-number/{number}", body)
    print(f"= number bound: inbound -> inbound@{version}, outbound -> checkin@{version}")


def append_changelog(env_name, rev, versions):
    line = (f"- {datetime.datetime.now().isoformat(timespec='minutes')} · `{env_name}` · git `{rev}` · "
            + ", ".join(f"{n} v{v}" for n, v in versions.items()) + "\n")
    with open(AGENTS_DIR / "CHANGELOG.md", "a") as f:
        f.write(line)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", required=True, choices=["staging", "prod"])
    p.add_argument("--only", nargs="+", choices=AGENT_NAMES)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--allow-missing", action="store_true", help="leave unset env values empty instead of failing")
    p.add_argument("--no-bind", action="store_true", help="don't touch the phone number")
    args = p.parse_args()

    load_dotenv()
    env, values = resolve_env(args.env, args.allow_missing)
    ids = load_ids()
    rev = git_rev()
    names = args.only or AGENT_NAMES

    if not args.dry_run:
        for name in AGENT_NAMES:  # all must exist so swap tools can resolve
            ensure_exists(name, ids)
    elif any(n not in ids for n in AGENT_NAMES):
        for n in AGENT_NAMES:
            ids.setdefault(n, {"agent_id": f"<new {n} agent>", "llm_id": f"<new {n} llm>"})

    versions = {}
    for name in names:
        versions[name] = push_one(name, ids, env, values, rev, args.dry_run)
    if not args.no_bind:
        bind_number(ids, env, values, args.dry_run)
    if env["publish"] and not args.dry_run:
        append_changelog(args.env, rev, versions)


if __name__ == "__main__":
    try:
        main()
    except RetellError as e:
        sys.exit(f"Retell error: {e}")
