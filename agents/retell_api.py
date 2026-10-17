"""Tiny Retell REST client + config helpers shared by push.py / pull.py.

Stdlib only, so it runs anywhere without installing anything.
"""
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.retellai.com"
AGENTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = AGENTS_DIR.parent
IDS_FILE = AGENTS_DIR / "retell.ids.json"

# Order matters: agents that others swap to are created first.
AGENT_NAMES = ["crisis", "inbound", "inbound_ko", "inbound_zh", "checkin", "welfare", "alert"]


def load_dotenv():
    """Load KEY=VALUE lines from the repo-root .env (never committed) without overriding real env vars."""
    path = REPO_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class RetellError(RuntimeError):
    pass


def call(method, path, body=None):
    key = os.environ.get("RETELL_API_KEY")
    if not key:
        raise RetellError("RETELL_API_KEY is not set (export it or put it in the repo-root .env)")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise RetellError(f"{method} {path} -> {e.code}: {e.read().decode(errors='replace')[:2000]}") from None
    return json.loads(raw) if raw else None


def items(resp):
    """List endpoints return either a bare list or {items: [...]}."""
    return resp.get("items", []) if isinstance(resp, dict) else (resp or [])


def load_ids():
    return json.loads(IDS_FILE.read_text()) if IDS_FILE.exists() else {}


def save_ids(ids):
    IDS_FILE.write_text(json.dumps(ids, indent=2) + "\n")


_PLACEHOLDER = re.compile(r"\$\{([A-Z0-9_]+)\}")


def substitute(obj, values, missing):
    """Replace ${VAR} placeholders in every string of a JSON-like object. Unknown names go into `missing`."""
    if isinstance(obj, str):
        def repl(m):
            name = m.group(1)
            if name in values and values[name] is not None:
                return str(values[name])
            missing.add(name)
            return m.group(0)
        return _PLACEHOLDER.sub(repl, obj)
    if isinstance(obj, list):
        return [substitute(x, values, missing) for x in obj]
    if isinstance(obj, dict):
        return {k: substitute(v, values, missing) for k, v in obj.items()}
    return obj
