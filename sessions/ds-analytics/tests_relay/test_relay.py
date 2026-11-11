import importlib
import json
import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cs2-backend" / "mvp"))


class RelayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.env = patch.dict(
            os.environ,
            {
                "DIZA_DB": str(Path(cls.directory.name) / "relay.sqlite3"),
                "OPS_API_TOKEN": "relay-test-operator",
                "RETELL_API_KEY": "relay-test-provider",
                "DRILL_MODE": "true",
                "DIZA_RESPONDERS": "[]",
                "RELAY_RETELL_AGENT_ID": "test-agent",
            },
        )
        cls.env.start()
        cls.backend = importlib.import_module("backend.app.main")
        cls.backend.DB = os.environ["DIZA_DB"]
        cls.jobs = patch.multiple(
            cls.backend, sync_calls=lambda: None, geocode_pending=lambda: None
        )
        cls.jobs.start()

    @classmethod
    def tearDownClass(cls):
        cls.jobs.stop()
        cls.env.stop()
        cls.directory.cleanup()

    def setUp(self):
        from diza_analysis.live import create_app

        self.app = create_app()
        self.context = TestClient(self.app)
        self.client = self.context.__enter__()
        self.key = 0
        with self.backend.connect() as connection:
            for table in (
                "relay_receipts",
                "relay_events",
                "relay_attempts",
                "relay_followups",
                "relay_assistance",
                "relay_confirmations",
                "relay_records",
                "relay_residents",
                "relay_notice_versions",
                "relay_notices",
            ):
                connection.execute(f"DELETE FROM {table}")
        response = self.client.post("/api/relay/demo", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.data = self.dashboard()
        self.record = next(
            r for r in self.data["records"] if r["resident"]["name"].startswith("Marisol")
        )
        self.record_id = self.record["record_id"]
        self.resident_headers = {"x-relay-token": self.app.state.relay_store.token(self.record_id)}

    @property
    def headers(self):
        return {"Authorization": "Bearer relay-test-operator"}

    def tearDown(self):
        self.context.__exit__(None, None, None)

    def next_key(self):
        self.key += 1
        return f"test-request-{self.key:05d}"

    def dashboard(self):
        response = self.client.get("/api/relay/dashboard", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def response(self, **changes):
        body = {
            "idempotency_key": self.next_key(),
            "notice_version": 1,
            "next_step": "Usaré la entrada norte",
            "confirm_instruction": True,
            "needs_clarification": False,
            "assistance_needed": False,
            "assistance_details": "",
            "confirm_assistance": False,
            **changes,
        }
        return self.client.post(
            f"/api/relay/resident/{self.record_id}/response",
            headers=self.resident_headers,
            json=body,
        )

    def publish(self, **changes):
        notice = self.dashboard()["notice"]
        body = {
            "idempotency_key": self.next_key(),
            "expected_version": notice["version"],
            "title": notice["title"],
            "reason": "The north entrance is unavailable",
            "published_by": "Test coordinator",
            "content": {
                "en": {
                    "text": "The shuttle pickup has moved to the east entrance.",
                    "question": "Which entrance will you use?",
                    "next_steps": ["east entrance"],
                },
                "es": {
                    "text": "La recogida del transporte se ha trasladado a la entrada este.",
                    "question": "¿Qué entrada usarás?",
                    "next_steps": ["entrada este"],
                },
            },
            **changes,
        }
        return self.client.post(
            f"/api/relay/notices/{notice['id']}/publish", headers=self.headers, json=body
        )

    def test_end_to_end_update_preserves_history_and_assistance(self):
        result = self.response(
            assistance_needed=True,
            assistance_details="Uso un andador y necesito ayuda.",
            confirm_assistance=True,
        )
        self.assertEqual(result.status_code, 200, result.text)
        first = result.json()["context"]
        self.assertEqual(first["communication_status"], "confirmed_current")
        self.assertEqual(first["assistance"]["status"], "requested")
        task_id = first["assistance"]["id"]
        self.assertEqual(self.publish().status_code, 200)
        updated = self.app.state.relay_store.context(self.record_id)
        self.assertEqual(updated["communication_status"], "updated_notice_awaiting_confirmation")
        self.assertEqual(updated["confirmed_version"], 1)
        self.assertEqual(updated["assistance"]["id"], task_id)
        self.assertEqual(updated["assistance"]["status"], "requested")
        result = self.response(
            notice_version=2, next_step="I will use the east entrance", assistance_needed=None
        )
        self.assertEqual(result.json()["context"]["communication_status"], "confirmed_current")
        self.assertEqual(len(result.json()["context"]["confirmation_history"]), 2)

    def test_stale_response_is_saved_to_its_original_version(self):
        self.publish()
        result = self.response(
            assistance_needed=True, assistance_details="Need a hand", confirm_assistance=True
        )
        self.assertTrue(result.json()["stale"])
        self.assertEqual(result.json()["context"]["confirmed_version"], 1)
        self.assertEqual(
            result.json()["context"]["communication_status"], "updated_notice_awaiting_confirmation"
        )

    def test_duplicate_submissions_do_not_duplicate_assistance_or_events(self):
        key = self.next_key()
        for _ in range(3):
            result = self.response(
                idempotency_key=key,
                assistance_needed=True,
                assistance_details="Please help me get to the entrance",
                confirm_assistance=True,
            )
            self.assertEqual(result.status_code, 200)
        with self.backend.connect() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM relay_assistance WHERE record_id=?", (self.record_id,)
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    """SELECT COUNT(*) FROM relay_events
                       WHERE record_id=? AND type='assistance_confirmed'""",
                    (self.record_id,),
                ).fetchone()[0],
                1,
            )

    def test_cached_retry_rechecks_the_current_notice(self):
        key = self.next_key()
        self.assertFalse(self.response(idempotency_key=key).json()["stale"])
        self.publish()
        self.assertTrue(self.response(idempotency_key=key).json()["stale"])

    def test_reusing_request_key_with_different_details_is_rejected(self):
        key = self.next_key()
        self.assertEqual(self.response(idempotency_key=key).status_code, 200)
        self.assertEqual(self.response(idempotency_key=key, next_step="different").status_code, 409)

    def test_generic_yes_wrong_step_and_negation_do_not_confirm(self):
        for step in (
            "yes",
            "sí",
            "east entrance",
            "I will not use the north entrance",
            "The north entrance is closed",
            "Maybe the north entrance",
            "La entrada norte no es correcta",
        ):
            result = self.response(next_step=step)
            self.assertEqual(result.status_code, 200)
            self.assertFalse(result.json()["instruction_confirmed"])
            self.assertEqual(
                result.json()["context"]["communication_status"], "needs_clarification"
            )

    def test_uncertainty_after_confirmation_reopens_followup(self):
        self.response()
        result = self.response(confirm_instruction=False, needs_clarification=True)
        self.assertEqual(result.json()["context"]["communication_status"], "needs_clarification")
        with self.backend.connect() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT status FROM relay_followups WHERE record_id=? AND version=1",
                    (self.record_id,),
                ).fetchone()[0],
                "open",
            )

    def test_save_progress_does_not_confirm_an_assistance_request(self):
        result = self.response(
            confirm_instruction=False,
            assistance_needed=True,
            assistance_details="I use a walker",
            confirm_assistance=False,
        )
        self.assertIsNone(result.json()["context"]["assistance"])
        self.assertIn("assistance_confirmation", result.json()["context"]["missing"])

    def test_assistance_requires_acceptance_before_completion(self):
        result = self.response(
            assistance_needed=True,
            assistance_details="Help reaching pickup",
            confirm_assistance=True,
        )
        task = result.json()["context"]["assistance"]
        path = f"/api/relay/assistance/{task['id']}/decision"
        body = {
            "idempotency_key": self.next_key(),
            "expected_revision": 1,
            "action": "complete",
            "owner": "Coordinator A",
        }
        self.assertEqual(self.client.post(path, headers=self.headers, json=body).status_code, 409)
        body.update(action="accept", idempotency_key=self.next_key())
        self.assertEqual(self.client.post(path, headers=self.headers, json=body).status_code, 200)
        body.update(
            action="complete",
            expected_revision=2,
            idempotency_key=self.next_key(),
            owner="Wrong owner",
        )
        self.assertEqual(self.client.post(path, headers=self.headers, json=body).status_code, 409)
        body.update(owner="Coordinator A", idempotency_key=self.next_key())
        self.assertEqual(self.client.post(path, headers=self.headers, json=body).status_code, 200)

    def test_simultaneous_acceptance_has_one_owner(self):
        result = self.response(
            assistance_needed=True,
            assistance_details="Help reaching pickup",
            confirm_assistance=True,
        )
        task = result.json()["context"]["assistance"]

        def accept(owner):
            return self.client.post(
                f"/api/relay/assistance/{task['id']}/decision",
                headers=self.headers,
                json={
                    "idempotency_key": "concurrent-" + owner,
                    "expected_revision": 1,
                    "action": "accept",
                    "owner": owner,
                },
            ).status_code

        with ThreadPoolExecutor(2) as pool:
            statuses = list(pool.map(accept, ("Coordinator A", "Coordinator B")))
        self.assertEqual(sorted(statuses), [200, 409])

    def test_missed_call_remains_no_response(self):
        result = self.client.post(
            f"/api/relay/records/{self.record_id}/attempts",
            headers=self.headers,
            json={"idempotency_key": self.next_key(), "result": "no_answer"},
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(
            self.app.state.relay_store.context(self.record_id)["communication_status"],
            "no_response",
        )

    def test_concurrent_notice_publish_is_guarded(self):
        self.assertEqual(self.publish(expected_version=1).status_code, 200)
        self.assertEqual(self.publish(expected_version=1).status_code, 409)

    def test_opt_in_and_explicit_boolean_fields_are_required(self):
        result = self.client.post(
            "/api/relay/residents",
            headers=self.headers,
            json={
                "idempotency_key": self.next_key(),
                "name": "Not opted in",
                "language": "en",
                "opt_in": False,
            },
        )
        self.assertEqual(result.status_code, 422)
        self.assertEqual(self.response(confirm_instruction="false").status_code, 422)

    def test_private_link_cannot_access_another_resident_or_coordinator_data(self):
        other = next(r for r in self.data["records"] if r["record_id"] != self.record_id)
        self.assertEqual(
            self.client.get(
                f"/api/relay/resident/{other['record_id']}/context", headers=self.resident_headers
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.get("/api/relay/dashboard", headers=self.resident_headers).status_code, 401
        )

    def test_future_notice_version_is_rejected(self):
        self.assertEqual(self.response(notice_version=99).status_code, 409)

    def test_voice_progress_survives_disconnect_and_resumes_same_record(self):
        voice = self.app.state.relay_voice
        with patch.object(
            voice,
            "create_call",
            return_value={"call_id": "web-call-1", "access_token": "test-access"},
        ):
            result = self.client.post(
                f"/api/relay/resident/{self.record_id}/voice",
                headers=self.resident_headers,
                json={
                    "idempotency_key": self.next_key(),
                    "language": "es",
                    "consent_to_voice": True,
                },
            )
        self.assertEqual(result.status_code, 200, result.text)
        args = {
            "notice_version": 1,
            "assistance_needed": True,
            "assistance_details": "Uso un andador",
            "confirmed": True,
        }
        self.assertEqual(self.voice_function("confirm_assistance", args).status_code, 200)
        voice.end("web-call-1")
        with patch.object(
            voice,
            "create_call",
            return_value={"call_id": "web-call-2", "access_token": "test-access"},
        ):
            result = self.client.post(
                f"/api/relay/resident/{self.record_id}/voice",
                headers=self.resident_headers,
                json={
                    "idempotency_key": self.next_key(),
                    "language": "es",
                    "consent_to_voice": True,
                },
            )
        self.assertEqual(result.status_code, 200)
        context = voice.context("web-call-2")
        self.assertEqual(context["record_id"], self.record_id)
        self.assertIsNotNone(context["assistance"])
        self.assertEqual(context["missing"], ["instruction_confirmation"])

    def voice_function(self, action, args, call_id="web-call-1", signature=True):
        raw = json.dumps({"call": {"call_id": call_id}, "args": args})
        return self.client.post(
            "/retell/relay/fn/" + action,
            content=raw,
            headers={
                "x-retell-signature": symmetric["sign"](raw, "relay-test-provider")
                if signature
                else "bad"
            },
        )

    def test_voice_mid_call_update_requires_new_context_and_new_confirmation(self):
        voice = self.app.state.relay_voice
        with patch.object(
            voice,
            "create_call",
            return_value={"call_id": "web-call-1", "access_token": "test-access"},
        ):
            self.client.post(
                f"/api/relay/resident/{self.record_id}/voice",
                headers=self.resident_headers,
                json={
                    "idempotency_key": self.next_key(),
                    "language": "en",
                    "consent_to_voice": True,
                },
            )
        self.publish()
        result = self.voice_function(
            "confirm_instruction",
            {"notice_version": 1, "next_step": "north entrance", "confirmed": True},
        )
        self.assertTrue(result.json()["stale"])
        self.assertEqual(
            self.voice_function(
                "confirm_instruction",
                {"notice_version": 2, "next_step": "east entrance", "confirmed": True},
            ).status_code,
            409,
        )
        self.assertEqual(self.voice_function("context", {}).json()["notice"]["version"], 2)
        self.assertEqual(
            self.voice_function(
                "confirm_instruction",
                {"notice_version": 2, "next_step": "east entrance", "confirmed": True},
            ).json()["context"]["communication_status"],
            "confirmed_current",
        )

    def test_rejected_or_unbound_voice_functions_cannot_write(self):
        self.assertEqual(self.voice_function("context", {}, signature=False).status_code, 401)
        self.assertEqual(self.voice_function("context", {}).status_code, 403)

    def test_demo_never_overwrites_existing_notice(self):
        self.assertEqual(self.client.post("/api/relay/demo", headers=self.headers).status_code, 409)
        self.assertEqual(self.dashboard()["notice"]["id"], self.data["notice"]["id"])

    def test_old_confirmation_does_not_clear_newer_clarification(self):
        self.publish()
        self.response(notice_version=2, confirm_instruction=False, needs_clarification=True)
        self.response(notice_version=1)
        self.assertEqual(
            self.app.state.relay_store.context(self.record_id)["communication_status"],
            "needs_clarification",
        )

    def test_completed_help_is_not_reopened_by_repeating_the_same_request(self):
        body = {
            "assistance_needed": True,
            "assistance_details": "Help reaching the entrance",
            "confirm_assistance": True,
        }
        task = self.response(**body).json()["context"]["assistance"]
        for revision, action in ((1, "accept"), (2, "complete")):
            result = self.client.post(
                f"/api/relay/assistance/{task['id']}/decision",
                headers=self.headers,
                json={
                    "idempotency_key": self.next_key(),
                    "expected_revision": revision,
                    "action": action,
                    "owner": "Ana",
                },
            )
            self.assertEqual(result.status_code, 200)
        self.assertEqual(
            self.response(**body).json()["context"]["assistance"]["status"], "completed"
        )

    def test_voice_start_retry_creates_one_provider_call_and_passes_transport(self):
        voice = self.app.state.relay_voice
        body = {"idempotency_key": self.next_key(), "language": "es", "consent_to_voice": True}
        provider = {
            "call_id": "retry-call",
            "access_token": "ephemeral-session-token",
            "transport": "gateway",
            "url": "wss://voice.example.test",
            "ice_servers": [],
        }
        with patch.object(voice, "create_call", return_value=provider) as create:
            path = f"/api/relay/resident/{self.record_id}/voice"
            first = self.client.post(path, headers=self.resident_headers, json=body)
            retry = self.client.post(path, headers=self.resident_headers, json=body)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["transport"], "gateway")
        self.assertEqual(retry.status_code, 409)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(create.call_args.args[0]["agent_override"]["agent"]["language"], "es-ES")

    def test_resident_link_survives_app_restart_and_notices_remain(self):
        from diza_analysis.relay.store import RelayStore

        recreated = RelayStore(self.backend.connect)
        recreated.initialize()
        self.assertEqual(recreated.token(self.record_id), self.resident_headers["x-relay-token"])
        self.assertEqual(recreated.context(self.record_id)["notice"]["version"], 1)

    def test_voice_configuration_targets_only_signed_relay_endpoints(self):
        from diza_analysis.relay.voice_config import configuration

        config = configuration("https://relay.example.test", "selected-voice")
        self.assertEqual(config["agent"]["data_storage_setting"], "basic_attributes_only")
        tools = config["llm"]["general_tools"]
        self.assertEqual(len(tools), 6)
        for tool in tools[:-1]:
            self.assertTrue(tool["url"].startswith("https://relay.example.test/retell/relay/fn/"))
            self.assertFalse(tool["args_at_root"])
        with self.assertRaises(ValueError):
            configuration("http://insecure.example.test", "selected-voice")

    def test_late_started_webhook_cannot_revive_an_ended_session(self):
        voice = self.app.state.relay_voice
        with patch.object(
            voice, "create_call", return_value={"call_id": "web-call-1", "access_token": "temp"}
        ):
            voice.start(
                self.record_id,
                {"idempotency_key": self.next_key(), "language": "en", "consent_to_voice": True},
            )
        voice.end("web-call-1")
        raw = json.dumps({"event": "call_started", "call": {"call_id": "web-call-1"}})
        result = self.client.post(
            "/retell/relay/webhook",
            content=raw,
            headers={"x-retell-signature": symmetric["sign"](raw, "relay-test-provider")},
        )
        self.assertEqual(result.status_code, 204)
        self.assertEqual(voice.session("web-call-1")["status"], "disconnected")

    def test_revised_title_and_content_do_not_overwrite_the_old_notice(self):
        original = self.data["notice"]
        self.publish(title="Updated shuttle pickup")
        versions = self.dashboard()["versions"]
        self.assertEqual(versions[0]["title"], "Updated shuttle pickup")
        self.assertEqual(versions[1]["title"], original["title"])
        self.assertEqual(versions[1]["content"], original["content"])


if __name__ == "__main__":
    unittest.main()
