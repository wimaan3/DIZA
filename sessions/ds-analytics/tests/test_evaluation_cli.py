import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from diza_analysis.datasets import synthetic_data
from diza_analysis.evaluation import evaluate, load_cases
from diza_analysis.storage import read_sqlite
from diza_analysis.triage import classify


def passing_observations():
    rows = []
    for case in load_cases():
        expected = case["expected"]
        rows.append(
            {
                "case_id": case["id"],
                "severity": expected["severity"],
                "category": expected.get(
                    "category", classify(case["transcript"], case.get("fields")).category
                ),
                "response": "Please call " + expected.get("emergency_numbers", ["911"])[0]
                if expected["severity"] == "P0"
                else "I can help with your request.",
                "functions": expected.get("functions", []),
                "routed_pool": "emergency_services" if expected["severity"] == "P0" else "",
            }
        )
    return rows


class EvaluationTests(unittest.TestCase):
    def test_complete_observed_run_is_required_for_publish(self):
        rows = passing_observations()
        self.assertTrue(evaluate(load_cases(), rows)["publish_allowed"])
        self.assertFalse(evaluate(load_cases(), rows[:-1])["publish_allowed"])

    def test_missing_emergency_guidance_false_dispatch_and_volunteer_fail_closed(self):
        for change in (
            {"response": "Everything is fine"},
            {"response": "Call 911, help is on the way"},
            {"routed_pool": "general_helper"},
            {"severity": "P3"},
            {"functions": []},
        ):
            rows = passing_observations()
            rows[0].update(change)
            with self.subTest(change=change):
                self.assertFalse(evaluate(load_cases(), rows)["publish_allowed"])

    def test_self_harm_requires_988(self):
        rows = passing_observations()
        row = next(row for row in rows if row["case_id"] == "p0-self-harm")
        row["response"] = "Call 911"
        self.assertFalse(evaluate(load_cases(), rows)["publish_allowed"])

    def test_medical_emergency_cannot_pass_with_988_instead_of_911(self):
        rows = passing_observations()
        rows[0]["response"] = "Please call 988."
        self.assertFalse(evaluate(load_cases(), rows)["publish_allowed"])

    def test_duplicate_unknown_and_empty_observations(self):
        rows = passing_observations()
        with self.assertRaises(ValueError):
            evaluate(load_cases(), rows + rows[:1])
        with self.assertRaises(ValueError):
            evaluate(load_cases(), [{"case_id": "unknown"}])
        self.assertFalse(evaluate([], [])["publish_allowed"])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, *args, salt="test-private-salt-12345678"):
        environment = {**os.environ, "DIZA_ANALYTICS_SALT": salt}
        return subprocess.run(
            [sys.executable, "-m", "diza_analysis", *map(str, args)],
            capture_output=True,
            text=True,
            env=environment,
            timeout=30,
        )

    def test_demo_snapshot_public_and_evaluation_end_to_end(self):
        result = self.run_cli("demo", "--out-dir", self.directory, "--now", "2026-10-17T20:00:00Z")
        self.assertEqual(result.returncode, 0, result.stderr)
        fixture = json.loads((self.directory / "synthetic.json").read_text())
        self.assertEqual(len(fixture["residents"]), 500)
        self.assertEqual(len(fixture["responders"]), 10)
        self.assertEqual(len(fixture["calls"]), 200)
        for command in ("snapshot", "public"):
            result = self.run_cli(
                command,
                "--input",
                self.directory / "synthetic.json",
                "--output",
                self.directory / f"{command}-output.json",
                "--now",
                "2026-10-17T20:00:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.run_cli("evaluate").returncode, 0)
        self.assertEqual(self.run_cli("evaluate", "--require-publish").returncode, 1)

        result = self.run_cli(
            "snapshot",
            "--input",
            self.directory / "synthetic.json",
            "--output",
            self.directory / "before-calls.json",
            "--now",
            "0",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.directory / "before-calls.json").read_text())["calls"], 0)

    def test_missing_salt_invalid_json_and_nonexistent_db_fail_cleanly(self):
        fixture = self.directory / "fixture.json"
        fixture.write_text("[]")
        output = self.directory / "output.json"
        result = self.run_cli("snapshot", "--input", fixture, "--output", output, salt="")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())
        missing = self.directory / "missing.sqlite3"
        result = self.run_cli("snapshot", "--db", missing, "--output", output)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(missing.exists())

    def test_sqlite_adapter_readonly_and_consent_coverage(self):
        db = self.directory / "operations.sqlite3"
        with sqlite3.connect(db) as connection:
            connection.executescript("""
                CREATE TABLE calls(call_id TEXT PRIMARY KEY,caller_last4 TEXT,started REAL,
                                   ended REAL,summary TEXT);
                INSERT INTO calls VALUES('call-one','0100',100,200,'Sensitive summary');
                CREATE TABLE reports(dedupe TEXT,severity TEXT,category TEXT,language TEXT,
                                     source TEXT);
                INSERT INTO reports VALUES('call-one:abcdef','P1','smoke','es','retell');
                INSERT INTO reports VALUES('call-one:p0:medical','P0','medical','es','retell');
            """)
        original = db.read_bytes()
        rows, coverage = read_sqlite(db)
        self.assertEqual(coverage["calls_missing_consent"], 1)
        self.assertIsNone(rows[0]["consent_analytics"])
        self.assertEqual(rows[0]["severity"], "P0")
        self.assertNotIn("0100", json.dumps(rows))
        self.assertNotIn("Sensitive", json.dumps(rows))
        rows, _ = read_sqlite(db, consent_by_call={"call-one": True})
        self.assertTrue(rows[0]["consent_analytics"])
        self.assertEqual(db.read_bytes(), original)
        output = self.directory / "snapshot.json"
        result = self.run_cli("snapshot", "--db", db, "--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        metrics = json.loads(output.read_text())
        self.assertEqual(metrics["calls"], 0)
        self.assertEqual(metrics["excluded_consent_or_unknown"], 1)
        consent_file = self.directory / "consent.json"
        consent_file.write_text('{"call-one": true}')
        result = self.run_cli(
            "snapshot", "--db", db, "--consent-file", consent_file, "--output", output
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(output.read_text())["calls"], 1)

    def test_synthetic_seed_and_exact_drill_mix(self):
        first = synthetic_data(now=100_000)
        self.assertEqual(first, synthetic_data(now=100_000))
        kinds = [card["kind"] for card in first["drill_cards"]]
        self.assertEqual(
            {kind: kinds.count(kind) for kind in set(kinds)},
            {"everyday": 120, "crisis": 50, "duplicate": 20, "hoax": 10},
        )
        self.assertEqual(sum(card["language"] != "en" for card in first["drill_cards"]), 60)
        self.assertNotIn('"phone"', json.dumps(first["residents"]))


if __name__ == "__main__":
    unittest.main()
