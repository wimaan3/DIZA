"""Run an isolated localhost RelayLA preview without reading the repository .env."""

import argparse
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

import uvicorn

SESSION = Path(__file__).resolve().parents[1]
REPO = SESSION.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18772)
    parser.add_argument("--db", type=Path, default=SESSION / "artifacts/relay-preview.sqlite3")
    parser.add_argument("--ephemeral", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    with ExitStack() as stack:
        database = (
            Path(stack.enter_context(tempfile.TemporaryDirectory())) / "relay.sqlite3"
            if args.ephemeral
            else args.db.resolve()
        )
        database.parent.mkdir(parents=True, exist_ok=True)
        os.environ["DIZA_DB"] = str(database)
        os.environ.setdefault("OPS_API_TOKEN", "relay-demo-local")
        os.environ["DRILL_MODE"] = "true"
        os.environ["RELAY_LEGACY_WORKERS"] = "false"
        os.environ["DIZA_RESPONDERS"] = "[]"
        backend_root = REPO / "sessions/cs2-backend/mvp"
        sys.path.insert(0, str(backend_root))
        os.chdir(backend_root)
        from diza_analysis.live import create_app

        app = create_app()
        if args.demo:
            from backend.app.main import init

            init()
            store = app.state.relay_store
            store.initialize()
            if not store.dashboard()["notice"]:
                store.seed_demo()
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
