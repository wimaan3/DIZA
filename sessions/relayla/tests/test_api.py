"""Boundary and integration tests; no test makes a provider network request."""

import json
from pathlib import Path
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric

from relayla.api import create_app
from relayla.settings import Settings


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / "test.sqlite3")
        self.settings = Settings(self.path)
        self.app = create_app(self.settings)
        self.client = self.enterContext(TestClient(self.app))

    def test_local_workflow_without_provider_credentials(self):
        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["integration"]["retell_configured"])
        self.assertGreaterEqual(len(data["cases"]), 6)
        self.assertEqual(data["cases"][0]["severity"], "P0")
        self.assertEqual(self.client.post("/api/retell/web-call", json={"case_id": data["cases"][0]["id"], "language": "en"}).status_code, 503)

    def test_can_mount_inside_diza_with_relative_assets_and_private_api_responses(self):
        parent = FastAPI()
        parent.mount("/relayla", self.app)
        with TestClient(parent) as client:
            self.assertIn('./static/app.js', client.get("/relayla/").text)
            self.assertEqual(client.get("/relayla/static/app.js").status_code, 200)
            response = client.get("/relayla/api/state")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_operator_auth_and_no_secret_in_health(self):
        settings = Settings(self.path, operator_token="test-operator-token", retell_api_key="test-provider-key")
        with TestClient(create_app(settings)) as client:
            self.assertEqual(client.get("/api/state").status_code, 401)
            self.assertEqual(client.get("/api/state", headers={"X-Operator-Token": "test-operator-token"}).status_code, 200)
            health = client.get("/health").text
            self.assertNotIn("test-operator-token", health)
            self.assertNotIn("test-provider-key", health)

    def test_public_host_and_cross_origin_mutations_rejected(self):
        self.assertEqual(self.client.get("/api/state", headers={"Host": "untrusted.example"}).status_code, 403)
        response = self.client.post("/api/actions/contact", headers={"Origin": "https://untrusted.example"}, json={"event_id": "cross-origin", "payload": {"case_id": "case-001", "outcome": "dropped"}})
        self.assertEqual(response.status_code, 403)

    def test_invalid_request_and_unknown_action_are_client_errors(self):
        self.assertEqual(self.client.post("/api/actions/contact", json={"payload": {}}).status_code, 422)
        self.assertIn(self.client.post("/api/actions/not-a-command", json={"event_id": "unknown", "payload": {}}).status_code, {400, 404, 422})

    def test_duplicate_contact_event_does_not_repeat_failure(self):
        body = {"event_id": "same-attempt", "payload": {"case_id": "case-001", "outcome": "no_answer"}}
        first = self.client.post("/api/actions/contact", json=body)
        self.assertEqual(first.status_code, 200, first.text)
        count = self.client.get("/api/cases/case-001").json()["contact_failures"]
        self.assertEqual(self.client.post("/api/actions/contact", json=body).status_code, 200)
        self.assertEqual(self.client.get("/api/cases/case-001").json()["contact_failures"], count)


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(str(Path(self.temp.name) / "provider.sqlite3"), operator_token="test-operator-token", retell_enabled=True, retell_api_key="test-signing-key", agent_id_en="test-agent-en", agent_id_es="test-agent-es")
        self.app = create_app(self.settings)
        self.client = self.enterContext(TestClient(self.app))
        self.call = {"call_id": "test-call-1", "agent_id": "test-agent-en", "metadata": {"relayla_case_id": "case-001"}}

    def signed(self, route, body, *, raw=None, timestamp=None):
        raw = raw or json.dumps(body, ensure_ascii=False)
        signature = symmetric["sign"](raw, "test-signing-key", timestamp)
        return self.client.post(route, content=raw, headers={"Content-Type": "application/json", "X-Retell-Signature": signature})

    def test_unsigned_and_expired_callback_rejected(self):
        payload = {"event": "call_ended", "call": self.call}
        self.assertEqual(self.client.post("/retell/webhook", json=payload).status_code, 401)
        self.assertEqual(self.signed("/retell/webhook", payload, timestamp=1).status_code, 401)

    def test_raw_body_signature_is_verified_before_parsing(self):
        raw = '{ "event": "call_started", "call": ' + json.dumps(self.call) + ' }'
        good = self.signed("/retell/webhook", {}, raw=raw)
        self.assertEqual(good.status_code, 200, good.text)
        signature = symmetric["sign"](raw, "test-signing-key")
        bad = self.client.post("/retell/webhook", content=raw + " ", headers={"X-Retell-Signature": signature})
        self.assertEqual(bad.status_code, 401)

    def test_provider_cannot_use_operator_commands_or_other_cases(self):
        body = {"name": "revise_notice", "call": self.call, "args": {}}
        self.assertEqual(self.signed("/retell/functions/revise_notice", body).status_code, 404)
        body = {"name": "check_status", "call": self.call, "args": {"case_id": "case-002"}}
        self.assertEqual(self.signed("/retell/functions/check_status", body).status_code, 403)

    def test_bound_call_cannot_detach_its_approved_notice(self):
        call = {**self.call, "metadata": {"relayla_case_id": "case-005"}}
        before = self.app.state.store.get_case("case-005")
        body = {"name": "submit_report", "call": call, "args": {"notice_id": None, "event_id": "detach-notice"}}
        response = self.signed("/retell/functions/submit_report", body)
        self.assertEqual(response.status_code, 403, response.text)
        after = self.app.state.store.get_case("case-005")
        self.assertEqual(after["notice_id"], before["notice_id"])
        self.assertEqual(after["communication_status"], "confirmed")

    def test_unconfigured_agent_rejected_even_with_valid_signature(self):
        call = {**self.call, "agent_id": "unconfigured-agent"}
        self.assertEqual(self.signed("/retell/webhook", {"event": "call_started", "call": call}).status_code, 403)

    def test_call_connection_is_not_acknowledgment_or_assistance_completion(self):
        before = self.app.state.store.get_case("case-001")
        response = self.signed("/retell/webhook", {"event": "call_started", "call": self.call})
        self.assertEqual(response.status_code, 200, response.text)
        after = self.app.state.store.get_case("case-001")
        self.assertEqual(after["acknowledged_version"], before["acknowledged_version"])
        self.assertEqual(after["assistance_status"], before["assistance_status"])

    def test_webhook_retries_do_not_multiply_failed_contact_attempts(self):
        call = {**self.call, "disconnection_reason": "dial_no_answer"}
        payload = {"event": "call_ended", "call": call}
        first = self.signed("/retell/webhook", payload)
        self.assertEqual(first.status_code, 200, first.text)
        count = self.app.state.store.get_case("case-001")["contact_failures"]
        self.assertEqual(self.signed("/retell/webhook", payload).status_code, 200)
        self.assertEqual(self.app.state.store.get_case("case-001")["contact_failures"], count)

    def test_late_start_cannot_erase_a_terminal_call_or_pending_retry(self):
        ended = {**self.call, "disconnection_reason": "error_network", "start_timestamp": 1000}
        self.assertEqual(self.signed("/retell/webhook", {"event": "call_ended", "call": ended}).status_code, 200)
        response = self.signed("/retell/webhook", {"event": "call_started", "call": {**self.call, "start_timestamp": 1000}})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["applied"])
        case = self.app.state.store.get_case("case-001")
        self.assertEqual(case["contact_status"], "dropped")
        self.assertEqual(case["callback_stage"], "retry_pending")
        self.assertEqual(case["contact_failures"], 1)

    def test_older_call_end_cannot_disconnect_a_newer_call(self):
        old_call = {**self.call, "start_timestamp": 1000}
        new_call = {**self.call, "call_id": "newer-call", "start_timestamp": 2000}
        for call in (old_call, new_call):
            response = self.signed("/retell/webhook", {"event": "call_started", "call": call})
            self.assertEqual(response.status_code, 200, response.text)
        response = self.signed("/retell/webhook", {"event": "call_ended", "call": {**old_call, "disconnection_reason": "error_network"}})
        self.assertFalse(response.json()["applied"])
        case = self.app.state.store.get_case("case-001")
        self.assertEqual(case["contact_status"], "connected")
        self.assertEqual(case["contact_failures"], 0)

    def test_unseen_older_call_is_ordered_by_provider_start_time(self):
        new_call = {**self.call, "call_id": "newer-call", "start_timestamp": 2000}
        self.signed("/retell/webhook", {"event": "call_started", "call": new_call})
        response = self.signed("/retell/webhook", {"event": "call_started", "call": {**self.call, "start_timestamp": 1000}})
        self.assertFalse(response.json()["applied"])
        self.assertEqual(self.app.state.store.get_case("case-001")["contact_status"], "connected")

    def test_call_lifecycle_guard_survives_process_restart(self):
        call = {**self.call, "disconnection_reason": "error_network", "start_timestamp": 1000}
        self.signed("/retell/webhook", {"event": "call_ended", "call": call})
        with TestClient(create_app(self.settings)) as client:
            raw = json.dumps({"event": "call_started", "call": self.call})
            response = client.post("/retell/webhook", content=raw, headers={"X-Retell-Signature": symmetric["sign"](raw, "test-signing-key")})
            self.assertFalse(response.json()["applied"])
            self.assertEqual(client.get("/api/cases/case-001", headers={"X-Operator-Token": "test-operator-token"}).json()["callback_stage"], "retry_pending")

    def test_intake_retries_keep_one_case_then_updates_use_same_binding(self):
        call = {"call_id": "new-test-call", "agent_id": "test-agent-en", "metadata": {}}
        args = {"summary": "Demo caller needs mobility help", "severity": "P2", "triage_source": "diza-test-intake", "language": "es", "notice_id": "notice-pickup", "event_id": "first-intake"}
        body = {"name": "submit_report", "call": call, "args": args}
        first = self.signed("/retell/functions/submit_report", body)
        self.assertEqual(first.status_code, 200, first.text)
        case_id = first.json()["case_id"]
        self.assertEqual(first.json()["case"]["triage_source"], "diza-test-intake")
        count = len(self.app.state.store.state()["cases"])
        retry = self.signed("/retell/functions/submit_report", body)
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(retry.json()["case_id"], case_id)
        self.assertEqual(len(self.app.state.store.state()["cases"]), count)
        args2 = {**args, "summary": "Demo caller needs a Spanish-speaking coordinator", "event_id": "updated-intake"}
        update = self.signed("/retell/functions/submit_report", {**body, "args": args2})
        self.assertEqual(update.status_code, 200, update.text)
        self.assertEqual(update.json()["case_id"], case_id)
        self.assertEqual(len(self.app.state.store.state()["cases"]), count)

    def test_route_to_human_records_request_without_accepting_or_dialing(self):
        original_details = self.app.state.store.get_case("case-001")["assistance_details"]
        response = self.signed("/retell/functions/route_to_human", {"name": "route_to_human", "call": self.call, "args": {"reason": "Accessibility help requested"}})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["handoff_status"], "requested")
        self.assertIsNone(response.json()["oncall_number"])
        self.assertNotEqual(self.app.state.store.get_case("case-001")["assistance_status"], "accepted")
        details = self.app.state.store.get_case("case-001")["assistance_details"]
        self.assertIn(original_details, details)
        self.assertIn("Accessibility help requested", details)

    def test_web_call_uses_server_agent_and_returns_only_connection_fields(self):
        class FakeCalls:
            async def create_web_call(inner, **kwargs):
                self.assertEqual(kwargs["agent_id"], "test-agent-es")
                self.assertEqual(kwargs["metadata"]["relayla_case_id"], "case-001")
                self.assertTrue(all(isinstance(v, str) for v in kwargs["retell_llm_dynamic_variables"].values()))
                return {"call_id": "mock-web-call", "access_token": "short-lived-test-token", "transport": "gateway", "ice_servers": [], "expires_at": 1, "unexpected": "must-not-leak"}
        class FakeClient:
            call = FakeCalls()
        with TestClient(create_app(self.settings, retell_client=FakeClient())) as client:
            response = client.post("/api/retell/web-call", json={"case_id": "case-001", "language": "es"}, headers={"X-Operator-Token": "test-operator-token"})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["transport"], "gateway")
            self.assertNotIn("unexpected", response.json())
            self.assertNotIn("test-signing-key", response.text)

    def test_repeated_human_request_preserves_and_reports_existing_acceptance(self):
        call = {**self.call, "metadata": {"relayla_case_id": "case-007"}}
        body = {"name": "route_to_human", "call": call, "args": {"reason": "Please keep my escort request open"}}
        response = self.signed("/retell/functions/route_to_human", body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["handoff_status"], "accepted")


if __name__ == "__main__":
    unittest.main()
