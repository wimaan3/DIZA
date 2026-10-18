"""Start the isolated hotel demo on localhost without loading provider credentials."""

import argparse
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path

import uvicorn

from diza_analysis.hotel.api import create_app

SESSION = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18772)
    parser.add_argument("--db", type=Path, default=SESSION / "artifacts/hotel-demo.sqlite3")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--ephemeral", action="store_true")
    args = parser.parse_args()
    with ExitStack() as stack:
        database = (
            Path(stack.enter_context(tempfile.TemporaryDirectory())) / "hotel.sqlite3"
            if args.ephemeral
            else args.db
        )
        app = create_app(
            database, os.environ.get("HOTEL_DEMO_TOKEN", "hotel-demo-local"), seed=args.demo
        )
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
