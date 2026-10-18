import json
import os
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

os.environ["CARE_INCLUDE_LEGACY"] = "false"
os.environ["DRILL_MODE"] = "true"
from fastapi.testclient import TestClient
from app import create_app


class CareFlowTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = str(Path(self.folder.name) / "care.sqlite3")
        self.app = create_app(self.db, include_legacy=False)
        self.context = TestClient(self.app)
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        self.folder.cleanup()

    def request(self, **changes):
        body = dict(idempotency_key=str(uuid.uuid4()), resident_id="r1", category="meal",
                    summary="Would like some water", reported_by="Amira Patel")
        body.update(changes)
        response = self.client.post("/api/care/requests", json=body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def state(self):
        return self.client.get("/api/care/state").json()

    def action(self, request, action, staff="nurse-jordan", note=""):
        return self.client.post(f'/api/care/requests/{request["id"]}/actions', json={
            "staff_id": staff, "action": action, "version": request["version"], "note": note,
        })

    def test_staff_dashboard_and_assets(self):
        for path, kind in (("/", "text/html"), ("/care", "text/html"),
                           ("/care-assets/app.js", "javascript"), ("/care-assets/style.css", "text/css")):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn(kind, response.headers["content-type"])
        self.assertEqual(self.client.get("/healthz").json(), {"status": "ok"})

    def test_daily_care_full_lifecycle_and_audit(self):
        request = self.request()
        self.assertEqual(request["urgency"], "routine")
        self.assertEqual(request["location"], "Room 101 · Garden wing")
        request = self.action(request, "accept", "care-amira").json()
        request = self.action(request, "start", "care-amira").json()
        response = self.action(request, "resolve", "care-amira", "Water provided; resident comfortable.")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "resolved")
        self.assertIn("Water provided", self.state()["events"][0]["message"])
        self.assertEqual(self.action(response.json(), "note", note="More information").status_code, 409)

    def test_original_quote_can_only_raise_urgency(self):
        for phrase in ("I fell beside my bed", "I can't breathe", "There is smoke", "not breathing"):
            with self.subTest(phrase=phrase):
                request = self.request(quote=phrase)
                self.assertEqual(request["urgency"], "urgent")
                self.assertEqual(self.action(request, "accept", "care-amira").status_code, 403)
                self.assertEqual(self.action(request, "accept").status_code, 200)
        self.assertEqual(self.request(category="urgent_help")["urgency"], "urgent")
        self.assertEqual(self.request(urgency="urgent")["urgency"], "urgent")

    def test_medication_needs_a_nurse(self):
        request = self.request(category="medication")
        self.assertEqual(self.action(request, "accept", "care-amira").status_code, 403)
        self.assertEqual(self.action(request, "accept", "lead-morgan").status_code, 200)

    def test_facilities_scope_and_ownership(self):
        request = self.request()
        self.assertEqual(self.action(request, "accept", "facilities-alex").status_code, 403)
        request = self.request(category="maintenance")
        request = self.action(request, "accept", "facilities-alex").json()
        self.assertEqual(self.action(request, "start").status_code, 403)
        self.assertEqual(self.action(request, "resolve", "facilities-alex", "Fixed").status_code, 409)

    def test_simultaneous_acceptance_has_one_owner(self):
        request = self.request()
        with ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(lambda staff: self.action(request, "accept", staff), ["care-amira", "nurse-jordan"]))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        self.assertEqual(len([e for e in self.state()["events"] if "Accepted responsibility" in e["message"]]), 1)

    def test_escalation_releases_ineligible_owner_and_rejects_stale_update(self):
        request = self.action(self.request(), "accept", "care-amira").json()
        response = self.action(request, "escalate", "care-amira", "Resident reports a new concern.")
        self.assertEqual(response.status_code, 200)
        urgent = response.json()
        self.assertEqual((urgent["urgency"], urgent["assignee"], urgent["status"]), ("urgent", None, "new"))
        self.assertEqual(self.action(request, "start", "care-amira").status_code, 409)
        self.assertEqual(self.action(urgent, "accept", "care-amira").status_code, 403)
        self.assertEqual(self.action(urgent, "accept").status_code, 200)

    def test_repeat_submission_does_not_duplicate_or_change_content(self):
        request = self.request(idempotency_key="same")
        repeated = self.request(idempotency_key="same")
        self.assertEqual(request["id"], repeated["id"])
        response = self.client.post("/api/care/requests", json={
            "idempotency_key": "same", "resident_id": "r2", "category": "meal",
            "summary": "Would like some water", "reported_by": "Amira Patel",
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.state()["requests"]), 1)

    def test_no_response_checkin_creates_one_followup_and_keeps_history(self):
        body = dict(staff_id="care-amira", outcome="no_response", note="Knocked; no response. Please check.", idempotency_key="check-1")
        for _ in range(2):
            response = self.client.post("/api/care/residents/r1/checkins", json=body)
            self.assertEqual(response.status_code, 201, response.text)
        state = self.state()
        self.assertEqual(len(state["checkins"]), 1)
        self.assertEqual(len(state["requests"]), 1)
        self.assertEqual(state["residents"][0]["checkin"]["outcome"], "no_response")
        body.update(outcome="seen_well", note="Seen at breakfast.", idempotency_key="check-2")
        self.assertEqual(self.client.post("/api/care/residents/r1/checkins", json=body).status_code, 201)
        state = self.state()
        self.assertEqual(state["residents"][0]["checkin"]["outcome"], "seen_well")
        self.assertEqual(len(state["checkins"]), 2)
        self.assertEqual(state["requests"][0]["status"], "new")  # Check-in never silently resolves a concern.

    def test_urgent_checkin_cannot_be_marked_well(self):
        body = dict(staff_id="nurse-jordan", outcome="seen_well", note="Resident fell by the bed.", idempotency_key="fall")
        self.assertEqual(self.client.post("/api/care/residents/r1/checkins", json=body).status_code, 422)
        body["outcome"] = "follow_up"
        self.assertEqual(self.client.post("/api/care/residents/r1/checkins", json=body).status_code, 201)
        self.assertEqual(self.state()["requests"][0]["urgency"], "urgent")

    def test_facilities_cannot_record_wellbeing(self):
        response = self.client.post("/api/care/residents/r1/checkins", json={
            "staff_id": "facilities-alex", "outcome": "seen_well", "idempotency_key": "not-care",
        })
        self.assertEqual(response.status_code, 403)

    def test_validation_and_token_guard(self):
        response = self.client.post("/api/care/requests", json={
            "idempotency_key": "invalid", "resident_id": "r1", "category": "meal",
            "summary": "   ", "reported_by": "Amira", "urgency": "low",
        })
        self.assertEqual(response.status_code, 422)
        with patch.dict(os.environ, {"OPS_API_TOKEN": "test-staff-token"}):
            self.assertEqual(self.client.get("/api/care/state").status_code, 401)
            self.assertEqual(self.client.get("/api/care/state", headers={"Authorization": "Bearer test-staff-token"}).status_code, 200)

    def test_database_survives_restart(self):
        request = self.request()
        with TestClient(create_app(self.db, include_legacy=False)) as restarted:
            state = restarted.get("/api/care/state").json()
            self.assertEqual(state["requests"][0]["id"], request["id"])
            self.assertEqual(len(state["residents"]), 6)

    def test_checkin_due_uses_facility_local_time(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        timezone = ZoneInfo("America/Los_Angeles")
        for hour, expected in ((9, False), (10, True), (18, True)):
            with patch("app.datetime") as date:
                date.now.return_value = datetime(2026, 10, 17, hour, tzinfo=timezone)
                self.assertTrue(all(r["checkin_due"] == expected for r in self.state()["residents"]))

    def test_demo_is_idempotent_and_disableable(self):
        self.client.post("/api/care/demo")
        self.client.post("/api/care/demo")
        self.assertEqual(len(self.state()["requests"]), 8)
        with patch.dict(os.environ, {"DRILL_MODE": "false"}):
            with TestClient(create_app(self.db, include_legacy=False)) as client:
                self.assertEqual(client.post("/api/care/demo").status_code, 403)

    def test_voice_intake_checks_signature_and_deduplicates(self):
        body = {"call": {"call_id": "call-care-demo"}, "args": {
            "resident_id": "r2", "category": "urgent_help", "urgency": "urgent",
            "summary": "Needs a nurse", "quote": "I fell", "reported_by": "Voice intake",
        }}
        self.assertEqual(self.client.post("/retell/fn/create_care_request", json=body).status_code, 503)
        from retell.lib.webhook_auth import symmetric
        raw = json.dumps(body)
        with patch.dict(os.environ, {"RETELL_API_KEY": "test-voice-key"}):
            headers = {"x-retell-signature": symmetric["sign"](raw, "test-voice-key")}
            self.assertEqual(self.client.post("/retell/fn/create_care_request", content=raw + " ", headers=headers).status_code, 401)
            for _ in range(2):
                response = self.client.post("/retell/fn/create_care_request", content=raw, headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["urgency"], "urgent")
        self.assertEqual(len(self.state()["requests"]), 1)

    def test_signed_voice_room_lookup_never_guesses_an_unknown_resident(self):
        from retell.lib.webhook_auth import symmetric
        with patch.dict(os.environ, {"RETELL_API_KEY": "test-voice-key"}):
            for room, expected in (("102", "r2"), ("999", None)):
                raw = json.dumps({"call": {"call_id": "care-lookup"}, "args": {"room": room}})
                headers = {"x-retell-signature": symmetric["sign"](raw, "test-voice-key")}
                response = self.client.post("/retell/fn/lookup_care_resident", content=raw, headers=headers)
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertEqual(result["found"], expected is not None)
                self.assertEqual(result["resident"]["id"] if result["resident"] else None, expected)

    def profile(self, **changes):
        body = dict(id="apartment-resident", staff_id="manager-taylor", version=0,
                    name="Jamie Rivers", room="2D", wing="East", language="English",
                    preferences="Please text before visiting", checkin_enabled=False)
        body.update(changes)
        return self.client.post("/api/care/residents", json=body)

    def test_apartment_and_care_residents_use_the_same_units_and_intake(self):
        response = self.profile()
        self.assertEqual(response.status_code, 200, response.text)
        person = next(r for r in self.state()["residents"] if r["id"] == "apartment-resident")
        self.assertFalse(person["checkin_enabled"])
        self.assertFalse(person["checkin_due"])
        self.assertTrue(any(room["unit"] == "2D" for room in self.state()["facility_workflow"]["rooms"]))
        item = self.request(resident_id=person["id"], category="maintenance", summary="The kitchen lamp needs replacing")
        self.assertEqual(self.state()["facility_workflow"]["tickets"][0]["unit"], "2D")
        self.assertEqual(self.action(item, "accept", "manager-taylor").status_code, 200)
        self.assertEqual(self.client.post(f'/api/care/residents/{person["id"]}/checkins', json=dict(
            staff_id="manager-taylor", outcome="seen_well", idempotency_key="no-schedule",
        )).status_code, 409)
        self.assertEqual(self.profile(version=1, checkin_enabled=True).status_code, 200)
        self.assertEqual(self.client.post(f'/api/care/residents/{person["id"]}/checkins', json=dict(
            staff_id="manager-taylor", outcome="follow_up", note="Resident requested company", idempotency_key="scheduled",
        )).status_code, 201)
        self.assertTrue(any(r["category"] == "wellbeing" and r["resident_id"] == person["id"] for r in self.state()["requests"]))

    def test_profile_permissions_versions_and_moves_preserve_physical_repairs(self):
        self.assertEqual(self.profile(staff_id="facilities-alex").status_code, 403)
        self.assertEqual(self.profile(staff_id="care-amira").status_code, 403)
        self.assertEqual(self.profile().status_code, 200)
        item = self.request(resident_id="apartment-resident", category="maintenance")
        self.assertEqual(self.profile(version=1, room="3A").status_code, 200)
        self.assertEqual(self.profile(version=1, room="4B").status_code, 409)
        state = self.state()
        self.assertEqual(next(r for r in state["residents"] if r["id"] == "apartment-resident")["room"], "3A")
        self.assertEqual(next(t for t in state["facility_workflow"]["tickets"] if t["code"] == item["facility_code"])["unit"], "2D")
        self.assertEqual(self.profile(id="r1", version=0).status_code, 409)
        with TestClient(create_app(self.db, include_legacy=False)) as restarted:
            person = next(r for r in restarted.get("/api/care/state").json()["residents"] if r["id"] == "apartment-resident")
            self.assertFalse(person["checkin_enabled"])
            self.assertEqual(person["profile_version"], 2)

    def test_building_manager_coordinates_repairs_but_cannot_accept_clinical_care(self):
        item = self.request(category="maintenance", summary="Reading lamp needs replacement")
        ticket = self.state()["facility_workflow"]["tickets"][0]
        response = self.client.post(f'/api/care/facility/tickets/{ticket["code"]}/actions', json=dict(
            staff_id="manager-taylor", version=ticket["version"], action="assign", assignee="facilities-alex"))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.action(item, "accept", "manager-taylor").status_code, 200)
        self.assertEqual(self.action(self.request(category="medication"), "accept", "manager-taylor").status_code, 403)
        self.assertEqual(self.action(self.request(quote="I fell in the hallway"), "accept", "manager-taylor").status_code, 403)


if __name__ == "__main__":
    unittest.main()
