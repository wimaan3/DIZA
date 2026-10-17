"""Run the standalone demo: python run.py [--port 8787]."""

import argparse
import os
from pathlib import Path
import shlex

import uvicorn

from relayla.api import create_app
from relayla.settings import Settings


def load_local_env():
    """Read simple NAME=value lines without executing shell expansion."""
    path = Path(__file__).with_name(".env")
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key.startswith(("RELAYLA_", "RETELL_")):
            continue
        parts = shlex.split(value, comments=True)
        os.environ.setdefault(key, " ".join(parts))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DIZA / RelayLA local supervisor workbench")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    load_local_env()
    config = Settings.from_env()
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not config.operator_token:
        parser.error("Set RELAYLA_OPERATOR_TOKEN before binding a public network interface.")
    uvicorn.run(create_app(config), host=args.host, port=args.port, proxy_headers=False, access_log=False)
