"""Run the existing backend test modules in separate processes.

Their module-level environment mutations select conflicting live/demo settings
when discovered together. Process isolation preserves each module's intended app
configuration without changing another session's files or contacting Retell.
Run against a disposable copy with its dashboard already built.
"""

import argparse
import subprocess
import sys
from pathlib import Path

RUNNER = """
import sys, unittest
from unittest.mock import patch
suite = unittest.TestLoader().discover('tests', pattern=sys.argv[1])
with patch('backend.app.main.sync_calls', return_value=None), \\
     patch('backend.app.resources.geocode', return_value=None):
    result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mvp_copy", type=Path)
    args = parser.parse_args()
    failed = []
    for test in sorted((args.mvp_copy / "tests").glob("test_*.py")):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                RUNNER,
                test.name,
            ],
            cwd=args.mvp_copy,
            timeout=60,
        )
        if result.returncode:
            failed.append(test.name)
    if not list((args.mvp_copy / "tests").glob("test_*.py")):
        parser.error("No test modules found")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
