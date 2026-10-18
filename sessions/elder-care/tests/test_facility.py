import hashlib
import json
import os
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

os.environ["CARE_INCLUDE_LEGACY"] = "false"
from app import create_app
from fastapi.testclient import TestClient


class CombinedWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = str(Path(self.folder.name) / "care.sqlite3")
        self.context = TestClient(create_app(self.db, include_legacy=False))
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        self.folder.cleanup()

    def state(self):
        return self.client.get("/api/care/state").json()

    def report(self, **changes):
        payload = dict(idempotency_key=str(uuid.uuid4()), resident_id="r1", category="maintenance",
                       facility_category="appliance", summary="Reading lamp will not turn on", reported_by="Care staff")
        payload.update(changes)
        response = self.client.post("/api/care/requests", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def ticket(self, code):
        return next(t for t in self.state()["facility_workflow"]["tickets"] if t["code"] == code)

    def act(self, ticket, action, **changes):
        payload = dict(staff_id="facilities-alex", version=ticket["version"], action=action)
        payload.update(changes)
        return self.client.post(f'/api/care/facility/tickets/{ticket["code"]}/actions', json=payload)

    def test_same_room_duplicate_has_one_work_order_and_two_care_requests(self):
        first = self.report(access_ok=True)
        second = self.report(summary="Second lamp report", quote="Still not working", access_ok=False)
        self.assertEqual(first["facility_code"], second["facility_code"])
        ticket = self.ticket(first["facility_code"])
        self.assertEqual(len(ticket["reporters"]), 2)
        self.assertEqual(len(ticket["care_requests"]), 2)
        self.assertFalse(ticket["access_ok"])
        self.assertEqual(len(self.state()["requests"]), 2)

    def test_shared_system_uses_original_building_rules(self):
        first = self.report(facility_category="no_hot_water", summary="Hot water not working")
        second = self.report(resident_id="r3", facility_category="no_hot_water", summary="No hot water here either")
        one, two = self.ticket(first["facility_code"]), self.ticket(second["facility_code"])
        self.assertEqual(first["urgency"], "urgent")
        self.assertEqual(second["urgency"], "urgent")
        self.assertEqual(one["related"][0]["code"], two["code"])
        self.assertIn("Garden", one["related"][0]["reason"])
        self.assertNotIn("ca_clock", one)

    def test_dangerous_room_issue_requires_nurse_for_resident_and_facilities_for_repair(self):
        item = self.report(facility_category="gas_smell", summary="A gas smell in the room")
        ticket = self.ticket(item["facility_code"])
        self.assertEqual(ticket["urgency"], "emergency")
        self.assertEqual(item["urgency"], "urgent")
        response = self.client.post(f'/api/care/requests/{item["id"]}/actions', json={
            "staff_id": "facilities-alex", "version": item["version"], "action": "accept",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.act(ticket, "assign", assignee="facilities-alex").status_code, 200)

    def test_repair_resolution_keeps_resident_followup_open(self):
        item = self.report()
        ticket = self.ticket(item["facility_code"])
        self.assertEqual(self.act(ticket, "resolve", note="Done").status_code, 409)
        self.assertEqual(self.act(ticket, "assign", assignee="vendor-electrical").status_code, 200)
        ticket = self.ticket(ticket["code"])
        self.assertEqual(self.act(ticket, "start").status_code, 200)
        ticket = self.ticket(ticket["code"])
        self.assertEqual(self.act(ticket, "resolve", note="Lamp replaced; care team to check comfort.").status_code, 200)
        self.assertEqual(self.ticket(ticket["code"])["status"], "closed")
        self.assertEqual(self.state()["requests"][0]["status"], "new")
        ticket = self.ticket(ticket["code"])
        self.assertEqual(self.act(ticket, "reopen", note="Replacement failed.").status_code, 200)

    def test_conflicting_assignments_reject_stale_version(self):
        ticket = self.ticket(self.report()["facility_code"])
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda assignee: self.act(ticket, "assign", assignee=assignee), ["facilities-alex", "vendor-electrical"]))
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])

    def test_manual_merge_preserves_children_and_unmerge(self):
        first = self.ticket(self.report()["facility_code"])
        second = self.ticket(self.report(resident_id="r3")["facility_code"])
        response = self.act(second, "merge", target_code=first["code"], target_version=first["version"], note="Same repair job.")
        self.assertEqual(response.status_code, 200, response.text)
        second = self.ticket(second["code"])
        self.assertEqual(second["merged_into"], first["code"])
        self.assertEqual(self.act(second, "start").status_code, 409)
        self.assertEqual(self.act(second, "unmerge", note="Separate causes confirmed.").status_code, 200)
        self.assertIsNone(self.ticket(second["code"])["merged_into"])

    def test_split_reporter_moves_only_that_resident_link(self):
        first, second = self.report(), self.report(summary="A second lamp report")
        ticket = self.ticket(first["facility_code"])
        response = self.act(ticket, "split", reporter_id="care:" + second["id"], note="Separate fixture.")
        self.assertEqual(response.status_code, 200, response.text)
        new_code = response.json()["code"]
        requests = {r["id"]: r for r in self.state()["requests"]}
        self.assertEqual(requests[first["id"]]["facility_code"], ticket["code"])
        self.assertEqual(requests[second["id"]]["facility_code"], new_code)
        self.assertEqual(len(self.ticket(new_code)["reporters"]), 1)
        self.assertEqual(self.ticket(new_code)["status"], "new")

    def test_unmerging_never_silently_lowers_shared_urgency(self):
        parent = self.ticket(self.report(urgency="urgent")["facility_code"])
        child = self.ticket(self.report(resident_id="r3")["facility_code"])
        self.assertEqual(child["urgency"], "routine")
        response = self.act(child, "merge", target_code=parent["code"], target_version=parent["version"], note="Shared hazard confirmed.")
        self.assertEqual(response.status_code, 200, response.text)
        child = self.ticket(child["code"])
        self.assertEqual(child["urgency"], "urgent")
        self.assertEqual(self.act(child, "unmerge", note="Separate repairs needed.").status_code, 200)
        self.assertEqual(self.ticket(child["code"])["urgency"], "urgent")

    def test_room_edit_rename_and_stale_protection(self):
        item = self.report()
        room = self.state()["facility_workflow"]["rooms"][0]
        payload = dict(staff_id="facilities-alex", version=room["version"], room="101", rename_to="101A", floor=1, stack="R1", hvac_zone="Garden")
        response = self.client.post("/api/care/facility/rooms", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.state()["residents"][0]["room"], "101A")
        self.assertEqual(self.ticket(item["facility_code"])["unit"], "101A")
        self.assertEqual(self.client.post("/api/care/facility/rooms", json=payload).status_code, 409)
        payload.update(room="101A", rename_to="102", version=2)
        self.assertEqual(self.client.post("/api/care/facility/rooms", json=payload).status_code, 409)

    def test_caregiver_can_note_but_cannot_manage_vendor_work(self):
        ticket = self.ticket(self.report()["facility_code"])
        self.assertEqual(self.act(ticket, "assign", staff_id="care-amira", assignee="facilities-alex").status_code, 403)
        self.assertEqual(self.act(ticket, "note", staff_id="care-amira", note="Resident requests a knock before entry.").status_code, 200)

    def test_old_demo_fingerprints_remain_idempotent_after_upgrade(self):
        import sqlite3
        payload = dict(idempotency_key="old-demo", resident_id="r1", category="meal", summary="Water please", reported_by="Care staff")
        response = self.client.post("/api/care/requests", json=payload)
        original = {**payload, "urgency": "routine", "quote": "", "location": "", "source": "staff"}
        # Use the old model's field order, exactly as model_dump_json encoded it.
        original = {k: original[k] for k in ("idempotency_key", "resident_id", "category", "urgency", "summary", "quote", "location", "reported_by", "source")}
        with closing(sqlite3.connect(self.db)) as c:
            c.execute("UPDATE care_requests SET payload_hash=? WHERE id=?", (hashlib.sha256(json.dumps(original, separators=(",", ":")).encode()).hexdigest(), response.json()["id"]))
            c.commit()
        repeated = self.client.post("/api/care/requests", json=payload)
        self.assertEqual(repeated.status_code, 201, repeated.text)
        self.assertEqual(repeated.json()["id"], response.json()["id"])

    def test_combined_demo_is_repeatable_and_contains_call_context(self):
        for _ in range(2):
            response = self.client.post("/api/care/demo")
            self.assertEqual(response.status_code, 200, response.text)
        state = self.state()
        self.assertEqual(len(state["requests"]), 8)
        self.assertEqual(len(state["facility_workflow"]["tickets"]), 3)
        self.assertEqual(len(state["calls"]), 3)
        self.assertTrue(any(len(t["reporters"]) == 2 for t in state["facility_workflow"]["tickets"]))

    def test_explicit_location_does_not_get_misgrouped_under_the_reporters_room(self):
        known = self.report(location="Room 103")
        self.assertEqual(self.ticket(known["facility_code"])["unit"], "103")
        one = self.report(location="Garden lounge")
        two = self.report(location="Garden lounge")
        self.assertNotEqual(one["facility_code"], two["facility_code"])
        self.assertEqual(self.ticket(one["facility_code"])["unit"], "Garden lounge")
        self.assertFalse(self.ticket(one["facility_code"])["unit_verified"])


if __name__ == "__main__":
    unittest.main()
