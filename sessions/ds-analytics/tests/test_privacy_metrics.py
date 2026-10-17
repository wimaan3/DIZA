import copy
import json
import unittest

from diza_analysis.cli import prepare_records
from diza_analysis.metrics import judge_agreement, mine_failures, reach_metrics, snapshot
from diza_analysis.privacy import anonymize_row, public_aggregates
from diza_analysis.timeutil import timestamp

SALT = "private-test-salt-1234567890"
NOW = 100_000


def call(i=0, **changes):
    return {
        "call_id": f"call-{i}",
        "caller_hash": f"caller-{i}",
        "consent_analytics": True,
        "zone_id": "altadena",
        "category": "smoke",
        "severity": "P1",
        "language": "en",
        "source": "observed",
        "started_at": NOW - 1200 + i,
        "ended_at": NOW - 1100 + i,
        "ts": NOW - 1200 + i,
        "verified": True,
        **changes,
    }


class PrivacyTests(unittest.TestCase):
    def test_only_allowlisted_fields_survive_without_mutating_input(self):
        raw = call(
            name="Sensitive Name",
            transcript="Call me at 202-555-0100",
            phone="+1 (202) 555-0100",
            location="123 Sample Street",
            lat=34.19,
            lon=-118.13,
            email="person@example.test",
            nested={"secret": "value"},
        )
        original = copy.deepcopy(raw)
        output = anonymize_row(raw, salt=SALT)
        serialized = json.dumps(output)
        for secret in ("Sensitive", "555", "Sample", "34.19", "example.test", "secret"):
            self.assertNotIn(secret, serialized)
        self.assertNotEqual(output["call_id"], raw["call_id"])
        self.assertEqual(raw, original)

    def test_opt_out_missing_consent_and_weak_salt(self):
        for value in (False, 0, "false", None):
            self.assertIsNone(anonymize_row(call(consent_analytics=value), salt=SALT))
        with self.assertRaises(ValueError):
            anonymize_row(call(), salt="short")

    def test_stable_keyed_identity_and_salt_rotation(self):
        first = anonymize_row(call(phone="+1 (202) 555-0100"), salt=SALT)
        second = anonymize_row(call(phone="2025550100"), salt=SALT)
        self.assertEqual(first["caller_hash"], second["caller_hash"])
        self.assertNotEqual(
            first["caller_hash"],
            anonymize_row(call(phone="2025550100"), salt="another-secret-salt")["caller_hash"],
        )

    def test_outbound_identity_uses_recipient(self):
        one = anonymize_row(
            call(direction="outbound", from_number="+12025550100", to_number="+12025550101"),
            salt=SALT,
        )
        two = anonymize_row(call(direction="inbound", from_number="+12025550101"), salt=SALT)
        self.assertEqual(one["caller_hash"], two["caller_hash"])

    def test_public_k_counts_people_per_cell_and_obeys_delay(self):
        self.assertEqual(public_aggregates([call(i) for i in range(4)], now=NOW), [])
        self.assertEqual(
            public_aggregates([call(i, caller_hash="same") for i in range(100)], now=NOW), []
        )
        cells = public_aggregates([call(i) for i in range(5)], now=NOW)
        self.assertEqual(cells[0]["distinct_callers"], 5)
        self.assertNotIn("caller_hash", json.dumps(cells))
        self.assertEqual(public_aggregates([call(i, ts=NOW - 599) for i in range(5)], now=NOW), [])
        self.assertEqual(
            public_aggregates([call(i, verified=False) for i in range(5)], now=NOW), []
        )

    def test_no_subtraction_total_and_separate_synthetic_cells(self):
        rows = [call(i) for i in range(5)] + [call(8, severity="P0")]
        result = public_aggregates(rows, now=NOW)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["reports"], 5)
        for row in rows[:3]:
            row["source"] = "synthetic"
        self.assertEqual(public_aggregates(rows, now=NOW), [])
        with self.assertRaises(ValueError):
            public_aggregates(rows, now=NOW, k=4)

    def test_duplicate_opt_out_cannot_be_revived(self):
        self.assertEqual(prepare_records([call(), call(consent_analytics=False)], salt=SALT), [])
        self.assertEqual(prepare_records([call(consent_analytics=False), call()], salt=SALT), [])

    def test_untrusted_failure_text_never_exported(self):
        rows = prepare_records([call(failure_flags=["Sensitive Name", "missed_p0"])], salt=SALT)
        self.assertNotIn("Sensitive", json.dumps(rows))


class MetricTests(unittest.TestCase):
    def test_no_data_is_null_not_a_perfect_score(self):
        result = snapshot([], now=NOW)
        self.assertEqual(result["calls"], 0)
        self.assertIsNone(result["peak_concurrent"])
        for key in (
            "p0_recall",
            "severity_accuracy",
            "routing_match",
            "form_completion",
            "safety_compliance",
            "ai_resolved_nonurgent",
            "non_en_es",
        ):
            self.assertIsNone(result[key]["value"])
        self.assertIsNone(result["time_to_human"]["P0"]["median_seconds"])

    def test_denominators_missing_predictions_and_ground_truth(self):
        result = snapshot(
            [
                call(0, expected_severity="P0", severity="P0", safety_compliant=True),
                call(1, expected_severity="P0", severity=None, safety_compliant=False),
                call(
                    2, expected_severity="P3", severity="P3", outcome="ai_resolved", language="ko"
                ),
                call(3, severity="P3", outcome="unknown", language="und"),
            ],
            now=NOW,
        )
        self.assertEqual(result["p0_recall"]["value"], 0.5)
        self.assertEqual(result["severity_accuracy"]["denominator"], 3)
        self.assertEqual(result["safety_compliance"]["value"], 0.5)
        self.assertEqual(result["ai_resolved_nonurgent"]["denominator"], 1)
        self.assertEqual(result["non_en_es"]["denominator"], 3)

    def test_peak_concurrency_ties_zero_duration_and_active_calls(self):
        rows = [
            call(0, started_at=1, ended_at=5),
            call(1, started_at=5, ended_at=10),
            call(2, started_at=5, ended_at=5),
            call(3, started_at=8, ended_at=None),
        ]
        result = snapshot(rows, now=20)
        self.assertEqual(result["peak_concurrent"], 2)
        self.assertEqual(result["coverage"]["intervals"], 4)

    def test_duplicate_calls_and_opt_out(self):
        result = snapshot(
            [call(), call(ended_at=NOW - 1000), call(1, consent_analytics=False)], now=NOW
        )
        self.assertEqual(result["calls"], 1)
        self.assertEqual(result["excluded_consent_or_unknown"], 1)

    def test_as_of_excludes_future_starts_without_counting_them_as_opt_outs(self):
        result = snapshot([call(), call(1, started_at=NOW + 1)], now=NOW)
        self.assertEqual(result["calls"], 1)
        self.assertEqual(result["excluded_future"], 1)
        self.assertEqual(result["excluded_consent_or_unknown"], 0)

    def test_failure_mining_uses_reason_codes_and_drops_opt_outs(self):
        row = call(
            expected_severity="P0",
            form_complete=False,
            transcript="Can I talk to a real person?",
            questions=["Where?", "Where?"],
            outcome="abandoned",
            started_at=NOW - 10,
            ended_at=NOW - 1,
        )
        failures = mine_failures([row, call(1, consent_analytics=False, form_complete=False)])
        self.assertEqual(len(failures), 1)
        self.assertEqual(
            set(failures[0]["reasons"]),
            {
                "missed_p0",
                "severity_mismatch",
                "human_requested",
                "repeated_question",
                "form_incomplete",
                "early_hangup",
            },
        )
        self.assertNotIn("real person", json.dumps(failures))

    def test_reach_deduplicates_contacts_and_excludes_nonconsenting_residents(self):
        residents = [
            {"id": "a", "needs": ["oxygen"], "consent_checkin": True},
            {"id": "b", "needs": ["mobility"], "consent_checkin": True},
            {"id": "c", "needs": ["alone"], "consent_checkin": False},
        ]
        attempts = [
            {"resident_id": "a", "result": "reached", "via": "contact", "ts": NOW + 900},
            {"resident_id": "a", "result": "reached", "via": "resident", "ts": NOW + 2},
            {"resident_id": "b", "result": "reached", "via": "resident", "ts": NOW + 901},
        ]
        result = reach_metrics(residents, attempts, declared_at=NOW)
        self.assertEqual(result["high_risk_reached_within_15_min"]["value"], 0.5)
        self.assertEqual(result["reached_via_contact"], 1)

    def test_judge_calibration_requires_forty_and_eighty_percent(self):
        labels = [{"criterion": "tone", "human": 4, "judge": 4 if i < 32 else 3} for i in range(40)]
        self.assertTrue(judge_agreement(labels)["tone"]["trusted"])
        self.assertFalse(judge_agreement(labels[:10])["tone"]["trusted"])

    def test_timezone_and_nonfinite_timestamps(self):
        self.assertEqual(timestamp("1970-01-01T00:00:00Z"), 0)
        for value in ("2026-10-17T00:00:00", float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                timestamp(value)


if __name__ == "__main__":
    unittest.main()
