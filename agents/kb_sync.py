#!/usr/bin/env python3
"""Create / refresh the Retell knowledge bases from agents/kb/*.md.

    python agents/kb_sync.py            # create missing KBs; add sections not yet in Retell
    python agents/kb_sync.py --replace  # also delete Retell sources whose section was edited or removed

Each "## " section of agents/kb/<name>.md becomes one text source titled with the heading.
KB ids are saved in retell.ids.json under "knowledge_bases"; push.py attaches them to the LLMs
listed in each <agent>.llm.json `_knowledge_bases`. Facts only: never put caller data in a KB.
Uses the Retell CLI (multipart upload), so RETELL_API_KEY must be set.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys

from retell_api import AGENTS_DIR, RetellError, call, load_dotenv, load_ids, save_ids

KB_DIR = AGENTS_DIR / "kb"


def sections(path):
    text = re.sub(r"<!--.*?-->", "", path.read_text(), flags=re.S)
    out = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        title, _, body = block.partition("\n")
        body = body.strip()
        # Title carries a short content hash so an edited section is a new source.
        digest = hashlib.sha1(body.encode()).hexdigest()[:6]
        out.append({"title": f"{title.strip()} [{digest}]", "text": f"{title.strip()}\n\n{body}"})
    return out


def cli(*args):
    res = subprocess.run(["retell", *args], capture_output=True, text=True)
    if res.returncode != 0:
        raise RetellError(f"retell {args[0]} failed: {res.stderr.strip() or res.stdout.strip()}")
    return json.loads(res.stdout) if res.stdout.strip() else None


def text_flags(texts):
    flags = []
    for t in texts:
        flags += ["--knowledge-base-texts", json.dumps(t, ensure_ascii=False)]
    return flags


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--replace", action="store_true", help="delete stale sources (edited/removed sections)")
    args = p.parse_args()
    load_dotenv()
    ids = load_ids()
    kbs = ids.setdefault("knowledge_bases", {})
    for path in sorted(KB_DIR.glob("*.md")):
        name = path.stem
        wanted = sections(path)
        if name not in kbs:
            kb = cli("create-knowledge-base", "--knowledge-base-name", f"diza-{name}", *text_flags(wanted))
            kbs[name] = kb["knowledge_base_id"]
            save_ids(ids)
            print(f"+ created {name}: {kbs[name]} ({len(wanted)} sections)")
            continue
        kb = call("GET", f"/get-knowledge-base/{kbs[name]}")
        have = {s.get("title"): s.get("source_id") for s in kb.get("knowledge_base_sources") or []}
        new = [t for t in wanted if t["title"] not in have]
        if new:
            cli("add-knowledge-base-sources", kbs[name], *text_flags(new))
        stale = [sid for title, sid in have.items() if title not in {t["title"] for t in wanted}]
        if stale and args.replace:
            for sid in stale:
                call("DELETE", f"/delete-knowledge-base-source/{kbs[name]}/source/{sid}")
        print(f"= {name}: +{len(new)} sections, {len(stale)} stale"
              + (" removed" if args.replace else " kept (use --replace to remove)" if stale else ""))
    save_ids(ids)


if __name__ == "__main__":
    try:
        main()
    except RetellError as e:
        sys.exit(f"Retell error: {e}")
