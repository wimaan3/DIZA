"""Integration checks against the real host app, with all provider jobs mocked."""

import importlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from retell.lib.webhook_auth import symmetric

MVP = Path(__file__).resolve().parents[2] / "cs2-backend" / "mvp"
sys.path.insert(0, str(MVP))


class LiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.db = str(Path(cls.temporary.name) / "operations.sqlite3")
        cls.environment = patch.dict(
            os.environ,
            {
                "DIZA_DB": cls.db,
                "RETELL_API_KEY": "test-retell-key",
                "OPS_API_TOKEN": "test-operator-token",
                "DRILL_MODE": "true",
                "DIZA_ANALYTICS_SALT": "test-private-analysis-salt-123456",
                "DIZA_RESPONDERS": "[]",
            },
        )
        cls.environment.start()
        cls.backend = importlib.import_module("backend.app.main")
        cls.backend.DB = cls.db
        cls.jobs = patch.multiple(
            cls.backend, sync_calls=lambda: None, geocode_pending=lambda: None
        )
        cls.jobs.start()

    @classmethod
    def tearDownClass(cls):
        cls.jobs.stop()
        cls.environment.stop()
        cls.temporary.cleanup()

    def setUp(self):
        from diza_analysis.live import create_app

        self.app = create_app()
        self.context = TestClient(self.app)
        self.client = self.context.__enter__()
        with self.backend.connect() as connection:
            for table in ("analysis_call_links", "calls", "reports", "consents", "webhook_events"):
                connection.execute(f"DELETE FROM {table}")
        self.call = {
            "call_id": "call-live-test",
            "from_number": "+12025550100",
            "direction": "inbound",
            "start_timestamp": 1_700_000_000_000,
            "retell_llm_dynamic_variables": {"language": "es", "zone_id": "altadena"},
        }

    def tearDown(self):
        self.context.__exit__(None, None, None)

    def signed(self, path, payload, *, valid=True):
        raw = json.dumps(payload)
        signature = symmetric["sign"](raw, "test-retell-key") if valid else "invalid"
        return self.client.post(
            path,
            content=raw,
            headers={"x-retell-signature": signature, "content-type": "application/json"},
        )

    def webhook(self, event="call_started", **extra):
        return self.signed("/retell/webhook", {"event": event, "call": {**self.call, **extra}})

    def consent(self, value=True):
        return self.signed(
            "/retell/fn/record_consent",
            {
                "call": self.call,
                "args": {"analytics_consent": value},
            },
        )

    def dashboard(self):
        response = self.client.get(
            "/api/analytics",
            headers={
                "authorization": "Bearer test-operator-token",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        return response.json()

    def test_health_page_and_assets_are_real_routes_not_spa_fallback(self):
        health = self.client.get("/health/analysis")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["analysis"], "enabled")
        page = self.client.get("/analytics")
        self.assertIn("From conversations to evidence.", page.text)
        self.assertEqual(page.headers["cache-control"], "no-store")
        for filename in ("app.js", "style.css"):
            response = self.client.get("/analytics/assets/" + filename)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("text/html", response.headers["content-type"])
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertIn("/api/analytics", paths)

    def test_authentication_fails_closed(self):
        self.assertEqual(self.client.get("/api/analytics").status_code, 401)
        with patch.dict(os.environ, {"OPS_API_TOKEN": ""}):
            self.assertEqual(self.client.get("/api/analytics").status_code, 503)

    def test_original_api_and_webhook_signature_remain_functional(self):
        self.assertEqual(self.client.get("/api/state").status_code, 401)
        self.assertEqual(self.webhook().status_code, 204)
        with self.backend.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0], 1)
        rejected = self.signed(
            "/retell/webhook",
            {
                "event": "call_started",
                "call": {
                    **self.call,
                    "call_id": "forged-call",
                },
            },
            valid=False,
        )
        self.assertEqual(rejected.status_code, 401)
        with self.backend.connect() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM analysis_call_links WHERE call_id='forged-call'"
                ).fetchone()[0],
                0,
            )

    def test_unknown_consent_is_excluded_and_explicit_consent_enables_metrics(self):
        self.webhook()
        data = self.dashboard()
        self.assertEqual(data["coverage"]["operational_calls"], 1)
        self.assertEqual(data["metrics"]["calls"], 0)
        self.assertEqual(data["coverage"]["missing_consent_link"], 1)
        self.assertEqual(self.consent().status_code, 200)
        self.webhook("transcript_updated", transcript="Hay humo y uso una silla de ruedas.")
        data = self.dashboard()
        self.assertEqual(data["metrics"]["calls"], 1)
        self.assertEqual(data["triage_predictions"], {"P1": 1})
        self.assertEqual(data["languages"], {"es": 1})
        self.assertIsNone(data["metrics"]["safety_compliance"]["value"])
        self.assertIsNone(data["metrics"]["p0_recall"]["value"])

    def test_opt_out_removes_prior_calls_and_predictions(self):
        self.webhook()
        self.consent()
        self.webhook("transcript_updated", transcript="I can't breathe")
        self.assertEqual(self.dashboard()["triage_predictions"], {"P0": 1})
        self.consent(False)
        data = self.dashboard()
        self.assertEqual(data["metrics"]["calls"], 0)
        self.assertEqual(data["coverage"]["opted_out_calls"], 1)
        self.assertEqual(data["triage_predictions"], {})
        with self.backend.connect() as connection:
            link = connection.execute("SELECT * FROM analysis_call_links").fetchone()
            self.assertIsNone(link["predicted_severity"])
            self.assertIsNone(link["caller_hash"])

    def test_analysis_does_not_change_operational_classification_or_routing(self):
        self.webhook()
        self.consent()
        self.webhook("transcript_updated", transcript="I can't breathe")
        with self.backend.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM routings").fetchone()[0], 0)

    def test_call_without_phone_on_later_event_keeps_consent_link(self):
        self.webhook()
        self.consent()
        self.signed(
            "/retell/webhook",
            {
                "event": "transcript_updated",
                "call": {
                    "call_id": self.call["call_id"],
                    "transcript": "I can't breathe",
                },
            },
        )
        self.assertEqual(self.dashboard()["triage_predictions"], {"P0": 1})

    def test_missing_key_keeps_operations_running_and_analytics_disabled(self):
        self.app.state.analysis_store.salt = ""
        self.assertEqual(self.webhook().status_code, 204)
        self.assertFalse(self.dashboard()["configured"])
        self.assertEqual(self.dashboard()["metrics"]["calls"], 0)

    def test_agent_emergency_guidance_is_not_caller_evidence(self):
        self.webhook()
        self.consent()
        self.webhook(
            "transcript_updated",
            transcript=(
                "Agent: If you have chest pain, call 911.\nUser: What are the dining hours?"
            ),
        )
        self.assertEqual(self.dashboard()["triage_predictions"], {"P3": 1})

    def test_structured_transcript_uses_only_user_turns(self):
        self.webhook()
        self.consent()
        self.webhook(
            "transcript_updated",
            transcript_object=[
                {"role": "agent", "content": "If you can't breathe, call 911."},
                {"role": "user", "content": "Hay humo afuera."},
            ],
        )
        self.assertEqual(self.dashboard()["triage_predictions"], {"P1": 1})

    def test_anonymous_phone_marker_cannot_share_consent_across_callers(self):
        self.call["from_number"] = "anonymous"
        self.webhook()
        self.consent()
        self.call["call_id"] = "another-anonymous-call"
        self.webhook()
        self.assertEqual(self.dashboard()["metrics"]["calls"], 0)

    def test_outbound_consent_links_the_recipient(self):
        self.call.update(direction="outbound", from_number="+12025550102", to_number="+12025550101")
        self.webhook()
        self.consent()
        self.assertEqual(self.dashboard()["metrics"]["calls"], 1)

    def test_dashboard_and_links_do_not_include_private_text_or_phone(self):
        self.webhook()
        self.consent()
        self.webhook("transcript_updated", transcript="My name is Sensitive Name, 123 Private St.")
        text = json.dumps(self.dashboard())
        for private in ("Sensitive Name", "123 Private", "2025550100", "call-live-test"):
            self.assertNotIn(private, text)
        with self.backend.connect() as connection:
            text = json.dumps(
                dict(connection.execute("SELECT * FROM analysis_call_links").fetchone())
            )
        self.assertNotIn("Sensitive Name", text)
        self.assertNotIn("2025550100", text)

    def test_existing_rows_survive_additive_startup(self):
        self.webhook()
        store = self.app.state.analysis_store
        store.initialize()
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
