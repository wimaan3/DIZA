"""Domain checks for failure recovery, handoff boundaries, and durable retries."""

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from relayla.engine import DomainError, Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "relayla.sqlite3"
        self.store = Store(self.path)
        self.counter = 0

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def command(self, action, payload, *, event_id=None, actor="operator"):
        self.counter += 1
        return self.store.apply(action, payload, event_id or f"test-{self.counter}", actor)

    def assert_rejected(self, status, action, payload, **kwargs):
        with self.assertRaises(DomainError) as raised:
            self.command(action, payload, **kwargs)
        self.assertEqual(status, raised.exception.status_code)
        return raised.exception

    @staticmethod
    def revision(expected_version=1, action_key="east_gate"):
        return {"notice_id": "notice-pickup", "expected_version": expected_version,
                "body_en": "Demo pickup moved to the east gate.",
                "body_es": "La recogida de demostración se trasladó a la puerta este.",
                "action_key": action_key, "action_label_en": "East gate", "action_label_es": "Puerta este",
                "source_label": "Demo coordinator", "approved_by": "Demo supervisor"}

    def acknowledge(self, case_id="case-001", version=1, key="north_entrance", **extra):
        return self.command("acknowledge", {"case_id": case_id, "notice_version": version,
                            "action_key": key, "readback_text": "I will use that entrance.", **extra})

    def test_seed_has_both_languages_sorted_priorities_and_realistic_distinct_states(self):
        state = self.store.state()
        self.assertEqual(8, state["metrics"]["total_cases"])
        self.assertEqual({"en", "es"}, {case["language"] for case in state["cases"]})
        self.assertEqual(["P0", "P1", "P2", "P2", "P2", "P3", "P3", "P3"],
                         [case["severity"] for case in state["cases"]])
        self.assertEqual(3, state["metrics"]["current_confirmations"])
        self.assertEqual(5, state["metrics"]["open_assistance"])
        self.assertEqual("accepted", self.store.get_case("case-007")["assistance_status"])
        self.assertEqual([1, 0, 1], [responder["active_count"] for responder in state["responders"]])
        self.assertFalse(any(key.startswith("_") for case in state["cases"] for key in case))

    def test_identical_retry_is_persisted_and_does_not_repeat_failure_or_audit(self):
        payload = {"case_id": "case-001", "outcome": "dropped"}
        first = self.command("contact", payload, event_id="same-event")
        events = len(self.store.get_case("case-001")["events"])
        self.store.close()
        self.store = Store(self.path)
        replay = self.command("contact", payload, event_id="same-event")
        self.assertEqual(first, replay)
        self.assertEqual(1, self.store.get_case("case-001")["contact_failures"])
        self.assertEqual(events, len(self.store.get_case("case-001")["events"]))
        self.assertEqual(8, self.store.state()["metrics"]["total_cases"])

    def test_event_id_reuse_with_changed_payload_action_or_actor_is_conflict(self):
        payload = {"case_id": "case-001", "outcome": "dropped"}
        self.command("contact", payload, event_id="immutable-event")
        self.assert_rejected(409, "contact", {**payload, "outcome": "no_answer"}, event_id="immutable-event")
        self.assert_rejected(409, "callback", {"case_id": "case-001", "minutes": 5, "reason": "Check in"}, event_id="immutable-event")
        self.assert_rejected(409, "contact", payload, event_id="immutable-event", actor="retell_call")
        self.assertEqual(1, self.store.get_case("case-001")["contact_failures"])

    def test_current_confirmation_does_not_close_help_and_survives_failed_contact(self):
        self.acknowledge(needs_assistance=False)
        case = self.store.get_case("case-001")
        self.assertEqual("confirmed", case["communication_status"])
        self.assertTrue(case["needs_assistance"])
        self.assertEqual("requested", case["assistance_status"])
        self.command("contact", {"case_id": "case-001", "outcome": "dropped"})
        case = self.store.get_case("case-001")
        self.assertEqual("confirmed", case["communication_status"])
        self.assertEqual(1, case["acknowledged_version"])
        self.assertEqual("requested", case["assistance_status"])

    def test_notice_revision_preserves_history_and_requires_new_version_confirmation(self):
        self.acknowledge()
        revision = self.command("revise_notice", self.revision())
        self.assertEqual(2, revision["version"])
        self.assertEqual(6, len(revision["affected_case_ids"]))
        self.assertEqual(0, revision["messages_sent"])
        self.assertEqual(6, self.store.state()["metrics"]["pending_updates"])
        self.assertEqual(0, self.store.state()["metrics"]["current_confirmations"])
        stale = self.acknowledge(version=1)
        self.assertTrue(stale["matched"])
        self.assertTrue(stale["stale"])
        self.assertEqual("update_pending", stale["communication_status"])
        wrong = self.acknowledge(version=2, key="north_entrance")
        self.assertFalse(wrong["matched"])
        self.assertEqual("needs_clarification", wrong["communication_status"])
        self.command("contact", {"case_id": "case-001", "outcome": "dropped"})
        self.assertEqual("needs_clarification", self.store.get_case("case-001")["communication_status"])
        current = self.acknowledge(version=2, key="east_gate")
        self.assertEqual("confirmed", current["communication_status"])
        self.assertEqual(2, current["acknowledged_version"])
        history = self.store.get_case("case-001")["acknowledgment_history"]
        self.assertEqual([1, 1, 2, 2], [item["notice_version"] for item in history])
        self.assertEqual("north_entrance", history[0]["action_key"])
        self.assertEqual("requested", self.store.get_case("case-001")["assistance_status"])

    def test_late_older_acknowledgment_cannot_overwrite_newer_confirmation(self):
        self.command("revise_notice", self.revision())
        self.acknowledge(version=2, key="east_gate")
        late_correct = self.acknowledge(version=1, key="north_entrance")
        late_wrong = self.acknowledge(version=1, key="wrong_place")
        self.assertTrue(late_correct["ignored"])
        self.assertTrue(late_wrong["ignored"])
        case = self.store.get_case("case-001")
        self.assertEqual(2, case["acknowledged_version"])
        self.assertEqual("east_gate", case["acknowledged_action_key"])
        self.assertEqual("confirmed", case["communication_status"])
        self.assertEqual(3, len(case["acknowledgment_history"]))

    def test_bad_readback_requires_clarification_and_invalid_future_version_rolls_back(self):
        wrong = self.acknowledge(key="south_entrance")
        self.assertEqual("needs_clarification", wrong["communication_status"])
        self.assertIsNone(wrong["acknowledged_version"])
        before = self.store.get_case("case-001")
        self.assert_rejected(409, "acknowledge", {"case_id": "case-001", "notice_version": 99,
                             "action_key": "north_entrance", "readback_text": "North."})
        self.assertEqual(before, self.store.get_case("case-001"))
        self.assert_rejected(422, "acknowledge", {"case_id": "case-001", "notice_version": 1,
                             "action_key": "north_entrance", "readback_text": ""})

    def test_competing_notice_revisions_cannot_overwrite_each_other(self):
        another = Store(self.path)
        gate = threading.Barrier(2)

        def update(store, event_id, key):
            gate.wait()
            try:
                return store.apply("revise_notice", self.revision(action_key=key), event_id)
            except DomainError as error:
                return error

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                one = pool.submit(update, self.store, "editor-one", "east_gate")
                two = pool.submit(update, another, "editor-two", "west_gate")
                results = [one.result(timeout=15), two.result(timeout=15)]
            self.assertEqual(1, sum(isinstance(result, DomainError) for result in results))
            failure = next(result for result in results if isinstance(result, DomainError))
            self.assertEqual(409, failure.status_code)
            self.assertEqual(2, self.store.state()["notices"][0]["version"])
            self.assertEqual(1, sum(event["kind"] == "revise_notice" for event in self.store.state()["events"]))
        finally:
            another.close()

    def test_severity_cannot_downgrade_and_escalation_revokes_volunteer_and_timed_callback(self):
        self.command("callback", {"case_id": "case-004", "minutes": 5, "reason": "Check progress"})
        result = self.command("submit_report", {"case_id": "case-004", "severity": "P0"})
        self.assertEqual("P0", result["severity"])
        case = self.store.get_case("case-004")
        self.assertIsNone(case["owner_id"])
        self.assertIsNone(case["callback_due_at"])
        self.assertEqual("human_review", case["callback_stage"])
        self.assertEqual("requested", case["assistance_status"])
        self.command("submit_report", {"case_id": "case-004", "severity": "P3", "needs_assistance": False})
        self.assertEqual("P0", self.store.get_case("case-004")["severity"])
        self.assert_rejected(409, "assign", {"case_id": "case-004", "responder_id": "responder-03"})
        self.assert_rejected(409, "callback", {"case_id": "case-004", "minutes": 1, "reason": "Later"})
        self.assertEqual("confirmed", self.store.get_case("case-004")["communication_status"])
        responder = next(r for r in self.store.state()["responders"] if r["id"] == "responder-03")
        self.assertEqual(0, responder["active_count"])

    def test_all_upstream_priority_updates_escalate_only(self):
        for requested, expected in (("P1", "P1"), ("P3", "P1"), ("P2", "P1"), ("P0", "P0"), ("P1", "P0")):
            result = self.command("submit_report", {"case_id": "case-001", "severity": requested})
            self.assertEqual(expected, result["severity"])

    def test_acceptance_completion_and_confirmation_are_independent(self):
        self.assert_rejected(409, "resolve", {"case_id": "case-001", "note": "Done"})
        self.command("assign", {"case_id": "case-001", "responder_id": "responder-01"})
        self.assert_rejected(409, "resolve", {"case_id": "case-001", "note": "Assigned is not accepted"})
        self.assert_rejected(409, "accept", {"case_id": "case-001", "responder_id": "responder-02"})
        self.command("accept", {"case_id": "case-001", "responder_id": "responder-01"})
        self.assertEqual("accepted", self.store.get_case("case-001")["assistance_status"])
        self.assert_rejected(422, "resolve", {"case_id": "case-001", "note": " "})
        self.command("resolve", {"case_id": "case-001", "note": "Demo coordinator reports the requested escort is complete."})
        case = self.store.get_case("case-001")
        self.assertEqual("completed", case["assistance_status"])
        self.assertEqual("unreached", case["communication_status"])
        self.assertIsNone(case["acknowledged_version"])
        self.assertEqual(1, next(r for r in self.store.state()["responders"] if r["id"] == "responder-01")["active_count"])

    def test_callback_ladder_is_an_audited_task_not_automatic_contact(self):
        for failures, stage in enumerate(("retry_pending", "contact_review", "human_review"), 1):
            result = self.command("contact", {"case_id": "case-001", "outcome": "no_answer"})
            self.assertEqual(failures, result["contact_failures"])
            self.assertEqual(stage, result["callback_stage"])
        follow_up = self.command("callback", {"case_id": "case-001", "minutes": 15, "reason": "Operator will review the next attempt."})
        self.assertFalse(follow_up["sent"])
        self.assertEqual("human_review", follow_up["callback_stage"])
        self.assertIsNotNone(follow_up["callback_due_at"])
        case = self.store.get_case("case-001")
        self.assertEqual(3, case["contact_failures"])
        self.assertEqual("unreached", case["communication_status"])
        self.assertEqual("requested", case["assistance_status"])
        self.assert_rejected(422, "callback", {"case_id": "case-001", "minutes": 0, "reason": "Bad delay"})
        self.assert_rejected(422, "callback", {"case_id": "case-001", "minutes": 61, "reason": "Bad delay"})

    def test_resume_after_restart_preserves_identity_priority_help_and_ack_history(self):
        self.command("submit_report", {"case_id": "case-001", "summary": "Saved bilingual assistance details before interruption."})
        self.acknowledge()
        self.command("contact", {"case_id": "case-001", "outcome": "dropped"})
        self.store.close()
        self.store = Store(self.path)
        self.command("contact", {"case_id": "case-001", "outcome": "resumed"})
        case = self.store.get_case("case-001")
        self.assertEqual("demo-001", case["resident_id"])
        self.assertEqual("es", case["language"])
        self.assertEqual("Saved bilingual assistance details before interruption.", case["summary"])
        self.assertEqual("P2", case["severity"])
        self.assertEqual("requested", case["assistance_status"])
        self.assertEqual("confirmed", case["communication_status"])
        self.assertEqual(1, len(case["acknowledgment_history"]))
        self.assertEqual(8, self.store.state()["metrics"]["total_cases"])

    def test_normal_call_end_is_not_failure_acknowledgment_or_resolution(self):
        before = self.store.get_case("case-001")
        self.command("contact", {"case_id": "case-001", "outcome": "ended"}, actor="retell_call")
        case = self.store.get_case("case-001")
        self.assertEqual("ended", case["contact_status"])
        for key in ("contact_failures", "communication_status", "acknowledged_version", "assistance_status", "severity"):
            self.assertEqual(before[key], case[key])

    def test_provider_cannot_publish_accept_resolve_or_declare_zones(self):
        for action, payload in (
            ("revise_notice", self.revision()),
            ("zone", {"zone_id": "Campus West", "level": "crisis", "reason": "Untrusted tool text"}),
            ("accept", {"case_id": "case-004", "responder_id": "responder-03"}),
            ("resolve", {"case_id": "case-007", "note": "The caller sounds satisfied"}),
        ):
            with self.subTest(action=action):
                self.assert_rejected(403, action, payload, actor="retell_call")
        self.assertEqual(1, self.store.state()["notices"][0]["version"])
        self.assertEqual("assigned", self.store.get_case("case-004")["assistance_status"])
        self.assertEqual("accepted", self.store.get_case("case-007")["assistance_status"])
        self.command("zone", {"zone_id": "Campus West", "level": "crisis", "reason": "Operator-approved exercise change."})
        self.assertEqual("crisis", next(z for z in self.store.state()["zones"] if z["id"] == "Campus West")["level"])

    def test_failed_human_handoff_releases_capacity_without_counting_resident_nonresponse(self):
        before = self.store.get_case("case-004")
        payload = {"case_id": "case-004", "responder_id": "responder-03", "reason": "Demo volunteer did not accept."}
        result = self.command("handoff_failed", payload, event_id="handoff-attempt-1")
        replay = self.command("handoff_failed", payload, event_id="handoff-attempt-1")
        self.assertEqual(result, replay)
        case = self.store.get_case("case-004")
        self.assertIsNone(case["owner_id"])
        self.assertEqual("requested", case["assistance_status"])
        self.assertEqual(1, case["handoff_failures"])
        self.assertEqual(["responder-03"], case["failed_responder_ids"])
        self.assertEqual("responder-01", result["recommended_responder_id"])
        for key in ("contact_failures", "contact_status", "acknowledged_version", "communication_status", "severity"):
            self.assertEqual(before[key], case[key])
        self.assertEqual(0, next(r for r in self.store.state()["responders"] if r["id"] == "responder-03")["active_count"])
        self.assert_rejected(409, "handoff_failed", payload)
        self.assert_rejected(409, "handoff_failed", {"case_id": "case-007", "responder_id": "responder-01", "reason": "Already accepted"})

    def test_all_professional_handoffs_failed_keeps_p0_unresolved_without_volunteer_fallback(self):
        for responder_id in ("responder-02", "responder-01"):
            self.command("assign", {"case_id": "case-002", "responder_id": responder_id})
            result = self.command("handoff_failed", {"case_id": "case-002", "responder_id": responder_id, "reason": "Did not accept demo handoff."})
        case = self.store.get_case("case-002")
        self.assertIsNone(result["recommended_responder_id"])
        self.assertIsNone(case["recommended_responder_id"])
        self.assertEqual("requested", case["assistance_status"])
        self.assertEqual("P0", case["severity"])
        self.assertEqual(0, case["contact_failures"])
        self.assertEqual("human_review", case["callback_stage"])
        self.assertIsNone(case["callback_due_at"])

    def test_p0_contact_failure_never_enters_a_deferred_retry_stage(self):
        self.command("assign", {"case_id": "case-002", "responder_id": "responder-02"})
        self.command("accept", {"case_id": "case-002", "responder_id": "responder-02"})
        self.command("contact", {"case_id": "case-002", "outcome": "dropped"})
        case = self.store.get_case("case-002")
        self.assertEqual("accepted", case["assistance_status"])
        self.assertEqual("human_review", case["callback_stage"])
        self.assertIsNone(case["callback_due_at"])
        self.assertEqual("P0", case["severity"])

    def test_capacity_is_reserved_at_assignment_and_released_only_by_completion_or_failed_handoff(self):
        self.command("assign", {"case_id": "case-001", "responder_id": "responder-03"})
        self.assert_rejected(409, "assign", {"case_id": "case-003", "responder_id": "responder-03"})
        self.command("handoff_failed", {"case_id": "case-001", "responder_id": "responder-03", "reason": "No acceptance"})
        self.command("assign", {"case_id": "case-003", "responder_id": "responder-03"})
        self.assertEqual(2, next(r for r in self.store.state()["responders"] if r["id"] == "responder-03")["active_count"])

    def test_upstream_triage_fields_are_preserved_without_interpretation(self):
        payload = {"resident_id": "synthetic-new", "resident_name": "Demo new resident", "language": "es",
                   "zone": "New Demo Zone", "category": "power", "severity": "P2", "skills_needed": ["mobility", "spanish"],
                   "summary": "Synthetic report from DIZA.", "notice_id": None, "needs_assistance": True,
                   "assistance_details": "Requested a human follow-up.", "hazard_here_now": False, "location": "Demo building",
                   "people_at_risk": 2, "vulnerability": ["mobility"], "keyword_hits": ["synthetic term"], "confidence": 0.82}
        result = self.command("submit_report", payload, actor="retell_call")
        case = self.store.get_case(result["case_id"])
        for key in ("hazard_here_now", "location", "people_at_risk", "vulnerability", "keyword_hits", "confidence", "severity"):
            self.assertEqual(payload[key], case[key])
        self.assertEqual("normal", next(z for z in self.store.state()["zones"] if z["id"] == "New Demo Zone")["level"])
        self.assert_rejected(409, "submit_report", {"case_id": result["case_id"], "resident_id": "another-person"})

    def test_validation_rejection_leaves_no_partial_case_or_event(self):
        before = self.store.get_case("case-001")
        self.assert_rejected(422, "submit_report", {"case_id": "case-001", "summary": "This must roll back", "needs_assistance": "false"})
        self.assertEqual(before, self.store.get_case("case-001"))
        self.assert_rejected(422, "submit_report", {"case_id": "case-001", "confidence": float("nan")})
        self.assert_rejected(422, "acknowledge", {"case_id": "case-001", "notice_version": True,
                             "action_key": "north_entrance", "readback_text": "North"})
        self.assert_rejected(404, "contact", {"case_id": "missing", "outcome": "ended"})


if __name__ == "__main__":
    unittest.main()
