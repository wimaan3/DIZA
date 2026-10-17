"""CLI for demo fixtures, evaluations, operational snapshots, and public aggregates."""

import argparse
import csv
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from .config import load_config
from .datasets import synthetic_data
from .evaluation import evaluate, load_cases, retell_cases
from .metrics import mine_failures, snapshot, unique_calls
from .privacy import anonymize_row, public_aggregates
from .sources import fetch_acs, fetch_myla311, myla311_baseline
from .storage import read_sqlite
from .timeutil import timestamp
from .zones import detect_zone_level


def write_json(path: Path, data) -> None:
    """Atomic writes with owner-only permissions for internal analytics artifacts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_json(path: Path):
    return json.loads(path.read_text())


def load_input(args) -> tuple[list, dict]:
    if args.db:
        consent = read_json(args.consent_file) if args.consent_file else None
        if consent is not None and not isinstance(consent, dict):
            raise ValueError("Consent file must map call IDs to explicit booleans")
        if consent is not None and any(not isinstance(v, bool) for v in consent.values()):
            raise ValueError("Consent file values must be booleans")
        return read_sqlite(args.db, consent_by_call=consent)
    data = read_json(args.input)
    rows = data.get("calls") if isinstance(data, dict) else data
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Input must be a list of call records or an object with calls: []")
    return rows, {"adapter": "json"}


def prepare_records(rows: list, *, salt: str) -> list:
    # Deduplicate BEFORE filtering so a later opt-out cannot leave an earlier copy behind.
    records = []
    failures = {r["call_id"]: r["reasons"] for r in mine_failures(rows)}
    for row in unique_calls(rows):
        record = anonymize_row(row, salt=salt)
        if record:
            record["failure_flags"] = failures.get(row.get("call_id", row.get("id")), [])
            records.append(record)
    return records


def require_salt() -> str:
    salt = os.environ.get("DIZA_ANALYTICS_SALT", "")
    if len(salt.encode()) < 16:
        raise ValueError("Set DIZA_ANALYTICS_SALT to a private random value of at least 16 bytes")
    return salt


def demo(args) -> int:
    now = timestamp(args.now) if args.now else time.time()
    fixture = synthetic_data(
        now=now, seed=args.seed, profiles=read_json(args.profiles) if args.profiles else None
    )
    write_json(args.out_dir / "synthetic.json", fixture)
    evaluation = evaluate(load_cases())
    write_json(args.out_dir / "classifier-evaluation.json", evaluation)
    write_json(args.out_dir / "retell-cases.json", retell_cases(load_cases()))
    # A fixed salt is acceptable ONLY for these explicitly synthetic fixtures.
    records = prepare_records(fixture["calls"], salt="synthetic-demo-only-salt")
    write_json(args.out_dir / "snapshot.json", snapshot(records, now=now, prompt_version="demo"))
    write_json(args.out_dir / "public.json", public_aggregates(records, now=now))
    zone_evidence = {}
    for zone in load_config("zones"):
        level, evidence = detect_zone_level(zone["id"], now, reports=fixture["reports"])
        zone_evidence[zone["id"]] = {"level": level, "evidence": evidence}
    write_json(args.out_dir / "zones.json", zone_evidence)
    fields = [
        "id",
        "language",
        "zone_id",
        "needs",
        "consent_checkin",
        "consent_analytics",
        "do_not_call",
        "source",
    ]
    with (args.out_dir / "residents.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in fixture["residents"]:
            writer.writerow(
                {
                    key: json.dumps(row[key]) if isinstance(row[key], list) else row[key]
                    for key in fields
                }
            )
    print(
        json.dumps(
            {
                "source": "synthetic",
                "residents": len(fixture["residents"]),
                "responders": len(fixture["responders"]),
                "calls": len(fixture["calls"]),
                "classifier_cases_passed": evaluation["passed"],
                "artifacts": str(args.out_dir),
            }
        )
    )
    return 0 if evaluation["classifier_gate_passed"] else 1


def run_evaluation(args) -> int:
    observations = read_json(args.observations) if args.observations else None
    result = evaluate(load_cases(), observations)
    if args.output:
        write_json(args.output, result)
    print(json.dumps({key: value for key, value in result.items() if key != "results"}))
    gate = "publish_allowed" if args.require_publish else "classifier_gate_passed"
    return 0 if result[gate] else 1


def run_snapshot(args) -> int:
    rows, coverage = load_input(args)
    records = prepare_records(rows, salt=require_salt())
    now = timestamp(args.now) if args.now else time.time()
    if args.command == "public":
        result = {
            "visibility": "public",
            "k": 5,
            "delay_minutes": 10,
            "cells": public_aggregates(records, now=now),
        }
    else:
        result = snapshot(records, now=now, prompt_version=args.prompt_version)
        # Filtering occurred before the metric reducer; retain accurate exclusion coverage.
        result["excluded_consent_or_unknown"] = len(unique_calls(rows)) - len(records)
        result["input_coverage"] = coverage
    write_json(args.output, result)
    print(json.dumps({"output": str(args.output), "visibility": result["visibility"]}))
    return 0


def run_source(args) -> int:
    if args.command == "acs":
        result = fetch_acs(year=args.year, state=args.state, county=args.county, tract=args.tract)
    else:
        rows = fetch_myla311(start=args.start, end=args.end, max_rows=args.max_rows)
        result = myla311_baseline(rows, start=args.start, end=args.end)
    write_json(args.output, result)
    print(json.dumps({"output": str(args.output), "source": result["source"]}))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    demo_parser = commands.add_parser("demo", help="Generate explicitly synthetic demo artifacts")
    demo_parser.add_argument("--out-dir", type=Path, default=Path("artifacts/demo"))
    demo_parser.add_argument("--seed", type=int, default=42)
    demo_parser.add_argument(
        "--profiles", type=Path, help="Explicit per-zone language/age profiles"
    )
    demo_parser.add_argument("--now", help="UTC ISO timestamp or Unix seconds")
    demo_parser.set_defaults(run=demo)
    evaluation = commands.add_parser("evaluate", help="Run classifier or observed-agent checks")
    evaluation.add_argument("--observations", type=Path)
    evaluation.add_argument("--require-publish", action="store_true")
    evaluation.add_argument("--output", type=Path)
    evaluation.set_defaults(run=run_evaluation)
    for command in ("snapshot", "public"):
        snapshot_parser = commands.add_parser(command, help="Analyze JSON or read-only SQLite")
        inputs = snapshot_parser.add_mutually_exclusive_group(required=True)
        inputs.add_argument("--input", type=Path)
        inputs.add_argument("--db", type=Path)
        snapshot_parser.add_argument("--consent-file", type=Path)
        snapshot_parser.add_argument("--output", type=Path, required=True)
        snapshot_parser.add_argument("--now")
        snapshot_parser.add_argument("--prompt-version", default="unversioned")
        snapshot_parser.set_defaults(run=run_snapshot)
    acs = commands.add_parser("acs", help="Fetch an ACS tract language/age profile")
    acs.add_argument("--year", type=int, default=2024)
    acs.add_argument("--state", required=True)
    acs.add_argument("--county", required=True)
    acs.add_argument("--tract", required=True)
    acs.add_argument("--output", type=Path, required=True)
    acs.set_defaults(run=run_source)
    baseline = commands.add_parser("baseline", help="Fetch a bounded 2025 MyLA311 baseline")
    baseline.add_argument("--start", required=True)
    baseline.add_argument("--end", required=True)
    baseline.add_argument("--max-rows", type=int, default=100_000)
    baseline.add_argument("--output", type=Path, required=True)
    baseline.set_defaults(run=run_source)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.run(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"diza-analysis: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
