import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from diza_analysis.hotel.api import create_app


class HotelTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "hotel.sqlite3"
        self.app = create_app(self.database, "hotel-test-staff", seed=True)
        self.client = TestClient(self.app)
        self.headers = {"Authorization": "Bearer hotel-test-staff"}
        self.identity = self.start()
        self.guest_headers = {"X-Guest-Token": self.identity["token"]}
        self.path = "/api/hotel/guest/" + self.identity["session_id"]

    def tearDown(self):
        self.client.close()
        self.directory.cleanup()

    def key(self):
        return str(uuid.uuid4())

    def start(self, room="402", language="en"):
        result = self.client.post(
            "/api/hotel/guest/start",
            json={"idempotency_key": self.key(), "room": room, "language": language},
        )
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def dashboard(self):
        return self.client.get("/api/hotel/state", headers=self.headers).json()

    def message(self, text="I would like two extra towels", **changes):
        result = self.client.post(
            self.path + "/message",
            headers=self.guest_headers,
            json={"idempotency_key": self.key(), "text": text, **changes},
        )
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def confirm(self, **changes):
        context = self.client.get(self.path, headers=self.guest_headers).json()
        return self.client.post(
            self.path + "/confirm",
            headers=self.guest_headers,
            json={
                "idempotency_key": self.key(),
                "expected_revision": context["revision"],
                "confirmed": True,
                "access_ok": False,
                **changes,
            },
        )

    def task(self):
        return next(
            t for t in self.dashboard()["tickets"] if t["session_id"] == self.identity["session_id"]
        )

    def decision(self, task, action, **changes):
        return self.client.post(
            f"/api/hotel/tickets/{task['id']}",
            headers=self.headers,
            json={
                "idempotency_key": self.key(),
                "expected_revision": task["revision"],
                "action": action,
                **changes,
            },
        )

    def test_approved_answer_resolves_question_without_a_task(self):
        result = self.message("How do I connect to wifi?")
        self.assertIn("HarborHouse-Guest", result["messages"][-1]["text"])
        self.assertIsNone(result["pending"])
        self.assertEqual(len(self.dashboard()["tickets"]), 5)
        self.assertEqual(self.dashboard()["counts"]["answered"], 1)

    def test_greetings_are_not_counted_as_answered_questions(self):
        result = self.message("Hello")
        self.assertIn("Welcome", result["messages"][-1]["text"])
        self.assertIsNone(result["pending"])
        self.assertEqual(self.dashboard()["counts"]["answered"], 0)

    def test_followup_failure_of_wifi_answer_offers_a_staff_request(self):
        self.message("wifi")
        result = self.message("The wifi still doesn't work. I need a person.")
        self.assertEqual(result["pending"]["department"], "front_desk")
        self.assertEqual(len(self.dashboard()["tickets"]), 5)

    def test_request_requires_confirmation_and_entry_permission_is_explicit(self):
        result = self.message()
        self.assertEqual(result["pending"]["department"], "housekeeping")
        self.assertEqual(len(self.dashboard()["tickets"]), 5)
        saved = self.confirm(access_ok=True)
        self.assertEqual(saved.status_code, 200)
        task = self.task()
        self.assertTrue(task["access_ok"])
        self.assertEqual(task["status"], "new")
        self.assertIsNone(task["owner"])
        self.assertIsNone(task["completed"])

    def test_declining_the_readback_does_not_create_a_task(self):
        self.message()
        result = self.confirm(confirmed=False)
        self.assertIsNone(result.json()["pending"])
        self.assertEqual(len(self.dashboard()["tickets"]), 5)

    def test_timeout_retry_creates_one_task_and_one_creation_event(self):
        context = self.message()
        key = self.key()
        for _ in range(3):
            result = self.confirm(idempotency_key=key, expected_revision=context["revision"])
            self.assertEqual(result.status_code, 200)
        self.assertEqual(len(self.dashboard()["tickets"]), 6)
        detail = self.app.state.hotel_store.detail(self.task()["id"])
        self.assertEqual(len(detail["events"]), 1)

    def test_message_retries_do_not_repeat_the_conversation(self):
        key = self.key()
        first = self.message("wifi", idempotency_key=key)
        second = self.message("wifi", idempotency_key=key)
        self.assertEqual(first["messages"], second["messages"])
        self.assertEqual(self.dashboard()["counts"]["answered"], 1)
        changed = self.client.post(
            self.path + "/message",
            headers=self.guest_headers,
            json={"idempotency_key": key, "text": "Different request"},
        )
        self.assertEqual(changed.status_code, 409)

    def test_stale_readback_and_implicit_confirmation_are_rejected(self):
        first = self.message()
        self.message("Actually I need help with the air conditioning")
        self.assertEqual(self.confirm(expected_revision=first["revision"]).status_code, 409)
        self.assertEqual(self.confirm(confirmed="true").status_code, 422)
        self.assertEqual(len(self.dashboard()["tickets"]), 5)

    def test_guest_sessions_cannot_read_each_other_or_staff_data(self):
        other = self.start("403")
        result = self.client.get(
            "/api/hotel/guest/" + other["session_id"], headers=self.guest_headers
        )
        self.assertEqual(result.status_code, 401)
        self.assertEqual(
            self.client.get("/api/hotel/state", headers=self.guest_headers).status_code, 401
        )
        self.assertEqual(self.client.get(self.path).status_code, 401)

    def test_guest_tickets_do_not_disclose_other_rooms_or_related_sessions(self):
        self.message("The AC is blowing warm air")
        saved = self.confirm().json()
        self.assertEqual(len(saved["tickets"]), 1)
        self.assertNotIn("related", saved["tickets"][0])
        self.assertNotIn("token", saved)
        self.assertNotIn("session_id", saved["tickets"][0])

    def test_task_requires_an_owner_and_work_started_before_completion(self):
        self.message()
        self.confirm()
        task = self.task()
        self.assertEqual(self.decision(task, "complete").status_code, 409)
        self.assertEqual(self.decision(task, "assign", staff_id="eli").status_code, 422)
        self.assertEqual(self.decision(task, "assign", staff_id="ana").status_code, 200)
        self.assertEqual(self.decision(self.task(), "complete").status_code, 409)
        self.assertEqual(self.decision(self.task(), "start").status_code, 200)
        self.assertEqual(self.decision(self.task(), "complete").status_code, 200)
        self.assertEqual(self.task()["status"], "completed")

    def test_competing_staff_acceptances_have_one_winner(self):
        self.message()
        self.confirm()
        task = self.task()
        with ThreadPoolExecutor(2) as pool:
            futures = [
                pool.submit(self.decision, task, "assign", staff_id=person)
                for person in ("ana", "noa")
            ]
            statuses = sorted(f.result().status_code for f in futures)
        self.assertEqual(statuses, [200, 409])

    def test_spanish_questions_and_requests_use_the_same_persistent_flow(self):
        identity = self.start("404", "es")
        self.identity = identity
        self.guest_headers = {"X-Guest-Token": identity["token"]}
        self.path = "/api/hotel/guest/" + identity["session_id"]
        result = self.message("¿A qué hora es el desayuno?")
        self.assertIn("desayuno", result["messages"][-1]["text"])
        self.message("Necesito dos toallas")
        self.assertIn("registrada", self.confirm().json()["messages"][-1]["text"])
        self.assertEqual(self.task()["language"], "es")

    def test_safety_concern_is_flagged_without_claiming_dispatch(self):
        key = self.key()
        result = self.message("There is smoke in my room", idempotency_key=key)
        self.assertIn("cannot place calls or send help", result["messages"][-1]["text"])
        self.assertIsNone(result["pending"])
        self.assertEqual(self.task()["urgency"], "emergency")
        self.assertEqual(self.task()["status"], "new")
        self.message("There is smoke in my room", idempotency_key=key)
        self.assertEqual(len(self.dashboard()["tickets"]), 6)

    def test_related_reports_keep_each_room_separate(self):
        data = self.dashboard()
        first = next(t for t in data["tickets"] if t["room"] == "412")
        second = next(t for t in data["tickets"] if t["room"] == "409")
        self.assertEqual(first["related"][0]["room"], "409")
        self.assertNotEqual(first["id"], second["id"])

    def test_restart_keeps_conversations_tasks_and_private_session_access(self):
        self.message()
        self.confirm()
        task_id = self.task()["id"]
        recreated = create_app(self.database, "hotel-test-staff", seed=True)
        recreated.state.hotel_store.authenticate(
            self.identity["session_id"], self.identity["token"]
        )
        self.assertEqual(len(recreated.state.hotel_store.dashboard()["tickets"]), 6)
        self.assertEqual(
            recreated.state.hotel_store.session(self.identity["session_id"])["tickets"][0]["code"],
            f"H-{1000 + task_id}",
        )

    def test_unknown_room_is_rejected_and_api_responses_are_not_cached(self):
        result = self.client.post(
            "/api/hotel/guest/start",
            json={"idempotency_key": self.key(), "room": "999", "language": "en"},
        )
        self.assertEqual(result.status_code, 422)
        self.assertEqual(
            self.client.get(self.path, headers=self.guest_headers).headers["cache-control"],
            "no-store",
        )


if __name__ == "__main__":
    unittest.main()
