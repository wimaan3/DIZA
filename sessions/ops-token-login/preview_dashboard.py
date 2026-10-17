"""Build the isolated dashboard fix and update an existing local preview."""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


SESSION = Path(__file__).resolve().parent
REPO = SESSION.parents[1]
DASHBOARD = REPO / "sessions/cs2-backend/mvp/dashboard"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-root", type=Path, required=True)
    parser.add_argument("--node-modules", type=Path)
    args = parser.parse_args()
    target = args.preview_root.resolve() / "source/sessions/cs2-backend/mvp/dashboard/dist"
    if args.preview_root.resolve().is_relative_to(REPO):
        parser.error("Use a temporary preview outside the repository.")
    if not (target / "index.html").is_file():
        parser.error("The preview must already contain the built dashboard.")

    with tempfile.TemporaryDirectory(prefix="diza-dashboard-auth-") as temporary:
        work = Path(temporary) / "dashboard"
        shutil.copytree(DASHBOARD, work, ignore=shutil.ignore_patterns("node_modules", "dist"))
        subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(SESSION / "dashboard-auth.patch")],
            cwd=work,
            check=True,
        )
        if args.node_modules:
            modules = args.node_modules.resolve()
            if not (modules / ".bin/vite").is_file():
                parser.error("The supplied node_modules must contain Vite.")
            (work / "node_modules").symlink_to(modules, target_is_directory=True)
        else:
            subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=work, check=True)
        subprocess.run(["npm", "run", "build"], cwd=work, check=True)

        # Keep the old assets for existing tabs and publish the new HTML last.
        built = work / "dist"
        for source in built.rglob("*"):
            if not source.is_file() or source == built / "index.html":
                continue
            destination = target / source.relative_to(built)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        staging = target / ".index.html.next"
        shutil.copy2(built / "index.html", staging)
        os.replace(staging, target / "index.html")
    print("Updated the local dashboard preview; backend and phone tunnel remain running.")


if __name__ == "__main__":
    main()
