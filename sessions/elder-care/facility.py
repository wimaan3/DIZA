"""Adapt Imaan's building engine to the care home's rooms and staff workflow.

Building rules and ticket helpers are reused directly. Repairs share work orders;
individual care requests retain their own responsibility and resolution history.
"""

import json
import time
import uuid
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

BUILDING_ID = "care-home"
CATEGORIES = {
    "water_leak": "Water leak", "no_heat": "Heating", "no_hot_water": "Hot water",
    "electrical": "Electrical", "gas_smell": "Gas smell", "lockout": "Lockout",
    "pest": "Pests", "appliance": "Appliance", "noise": "Noise",
    "security": "Security", "other": "Other room issue",
}


class FacilityAction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    staff_id: str = Field(min_length=1, max_length=80)
    version: int = Field(ge=1)
    action: Literal["assign", "start", "waiting", "resolve", "reopen", "note", "notified", "merge", "unmerge", "split"]
    assignee: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=1200)
    target_code: str = Field(default="", max_length=40)
    target_version: int | None = Field(default=None, ge=1)
    reporter_id: str = Field(default="", max_length=120)


class RoomEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    staff_id: str = Field(min_length=1, max_length=80)
    version: int = Field(ge=1)
    room: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    rename_to: str = Field(default="", max_length=20, pattern=r"^[A-Za-z0-9-]*$")
    floor: int = Field(ge=0, le=30)
    stack: str = Field(max_length=20)
    hvac_zone: str = Field(max_length=40)


def initialize(c, rules, name):
    # Keep the ticket schema compatible with building.file_ticket and its helpers.
    c.executescript("""
        CREATE TABLE IF NOT EXISTS buildings(id TEXT PRIMARY KEY,name TEXT,address TEXT,lat REAL,lon REAL,manager_name TEXT,after_hours_phone TEXT,line_number TEXT);
        CREATE TABLE IF NOT EXISTS units(building_id TEXT,unit TEXT,floor INTEGER,stack TEXT,hvac_zone TEXT,tenant_language TEXT,PRIMARY KEY(building_id,unit));
        CREATE TABLE IF NOT EXISTS staff_vendors(id TEXT PRIMARY KEY,building_id TEXT,name TEXT,role TEXT,phone TEXT,skills TEXT);
        CREATE TABLE IF NOT EXISTS tickets(code TEXT PRIMARY KEY,building_id TEXT,unit TEXT,unit_verified INTEGER,category TEXT,urgency TEXT,urgency_reason TEXT,
            summary TEXT,caller_quote TEXT,language TEXT,access_ok INTEGER,reporters TEXT,status TEXT,assignee TEXT,created REAL,updated REAL,
            first_human_action_at REAL,closed_at REAL,related TEXT,merged_into TEXT,tenant_notified_at REAL,source TEXT);
        CREATE TABLE IF NOT EXISTS ticket_events(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT,ts REAL,kind TEXT,actor TEXT,message TEXT);
        CREATE TABLE IF NOT EXISTS care_ticket_versions(code TEXT PRIMARY KEY,version INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS care_room_versions(room TEXT PRIMARY KEY,version INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS care_call_context(call_id TEXT PRIMARY KEY,summary TEXT,transcript TEXT,source TEXT);
        CREATE INDEX IF NOT EXISTS care_tickets_open ON tickets(building_id,category,created);
    """)
    c.execute("INSERT OR IGNORE INTO buildings(id,name,address,manager_name) VALUES(?,?,?,?)",
              (BUILDING_ID, name, "Fictional care-home demo", "Care lead"))
    c.execute("UPDATE buildings SET name=? WHERE id=?", (name, BUILDING_ID))
    for person in c.execute("SELECT * FROM residents").fetchall():
        room = person["room"]
        c.execute("INSERT OR IGNORE INTO units VALUES(?,?,?,?,?,?)", (
            BUILDING_ID, room, int(room[0]) if room[0].isdigit() else 1,
            "R" + room[-1], person["wing"], person["language"],
        ))
        c.execute("INSERT OR IGNORE INTO care_room_versions VALUES(?,1)", (room,))
    for sid, title, role, skills in [
        ("facilities-alex", "Alex Chen", "facilities", "all"),
        ("vendor-plumbing", "Willow Plumbing (demo)", "plumber", "water_leak,no_hot_water"),
        ("vendor-electrical", "Willow Electrical (demo)", "electrician", "electrical"),
        ("vendor-hvac", "Willow Heating (demo)", "maintenance", "no_heat,no_hot_water"),
    ]:
        c.execute("INSERT OR IGNORE INTO staff_vendors VALUES(?,?,?,?,?,?)", (sid, BUILDING_ID, title, role, "", skills))
    for item in c.execute("SELECT * FROM care_requests WHERE category='maintenance' AND facility_code IS NULL").fetchall():
        link_request(c, rules, dict(item), "other", None)


def bump(c, code):
    c.execute("INSERT INTO care_ticket_versions VALUES(?,1) ON CONFLICT(code) DO UPDATE SET version=version+1", (code,))


def escalate_linked(c, codes, reason):
    for code in codes:
        rows = c.execute("SELECT q.*,s.role FROM care_requests q LEFT JOIN care_staff s ON q.assignee=s.id WHERE facility_code=? AND q.status!='resolved'", (code,)).fetchall()
        for item in rows:
            reset = item["assignee"] and item["role"] not in {"nurse", "care_lead"}
            if item["urgency"] != "urgent" or reset:
                c.execute("UPDATE care_requests SET urgency='urgent',reason=?,status=?,assignee=?,updated=?,version=version+1 WHERE id=?", (
                    "Room incident: " + reason, "new" if reset else item["status"],
                    None if reset else item["assignee"], time.time(), item["id"],
                ))
                c.execute("INSERT INTO care_events VALUES(?,?,?,?,?)", (
                    str(uuid.uuid4()), item["id"], "Room incident rules", "Raised to urgent human review: " + reason, time.time(),
                ))


def link_request(c, rules, item, category, access_ok, location_override=""):
    person = dict(c.execute("SELECT * FROM residents WHERE id=?", (item["resident_id"],)).fetchone())
    building = dict(c.execute("SELECT * FROM buildings WHERE id=?", (BUILDING_ID,)).fetchone())
    unit_text = person["room"]
    unverified_location = False
    if location_override:
        known = rules.find_unit(c, BUILDING_ID, location_override)
        unit_text = known["unit"] if known else "area-" + item["id"]
        unverified_location = known is None
    ticket, duplicate = rules.file_ticket(
        c, building, unit_text, category, item["summary"], item["quote"],
        language=person["language"], access_ok=access_ok,
        hint="urgent" if item["urgency"] == "urgent" else "", call_id="care:" + item["id"],
        source="care intake", now=item["created"],
    )
    if unverified_location:
        # Unknown shared areas stay separate until staff confirm a common location.
        c.execute("UPDATE tickets SET unit=? WHERE code=?", (location_override, ticket["code"]))
    if duplicate:
        # Permission from one report must never overwrite a refusal or an unknown.
        old = ticket["access_ok"]
        access = 0 if old == 0 or access_ok is False else None if old is None or access_ok is None else 1
        c.execute("UPDATE tickets SET access_ok=? WHERE code=?", (access, ticket["code"]))
    c.execute("UPDATE care_requests SET facility_code=? WHERE id=?", (ticket["code"], item["id"]))
    bump(c, ticket["code"])
    if ticket["urgency"] != "routine":
        escalate_linked(c, [ticket["code"]], ticket["urgency_reason"])
    return dict(c.execute("SELECT * FROM tickets WHERE code=?", (ticket["code"],)).fetchone())


def snapshot(c, rules):
    now = time.time()
    events = {}
    for row in c.execute("SELECT * FROM ticket_events ORDER BY ts,id"):
        events.setdefault(row["code"], []).append(dict(row))
    tickets = []
    for row in c.execute("SELECT * FROM tickets WHERE building_id=? ORDER BY created", (BUILDING_ID,)):
        ticket = rules.ticket_view(row, now, events)
        ticket.pop("ca_clock", None)  # Tenancy-law clocks are not care-home clinical policy.
        ticket["version"] = c.execute("SELECT version FROM care_ticket_versions WHERE code=?", (ticket["code"],)).fetchone()[0]
        ticket["care_requests"] = [dict(item) for item in c.execute(
            "SELECT q.id,q.code,q.resident_id,q.status,q.call_id,q.access_ok,r.name FROM care_requests q JOIN residents r ON r.id=q.resident_id WHERE q.facility_code=?",
            (ticket["code"],),
        )]
        tickets.append(ticket)
    units = []
    for row in c.execute("SELECT * FROM units WHERE building_id=? ORDER BY floor,unit", (BUILDING_ID,)):
        room = dict(row)
        room["version"] = c.execute("SELECT version FROM care_room_versions WHERE room=?", (room["unit"],)).fetchone()[0]
        units.append(room)
    return {
        "tickets": tickets, "rooms": units, "categories": CATEGORIES,
        "staff": [dict(row) for row in c.execute("SELECT id,name,role,skills FROM staff_vendors WHERE building_id=? ORDER BY name", (BUILDING_ID,))],
        "insights": rules.insights(tickets, now), "targets": rules.TARGETS,
    }


def register_routes(app, connect, staff, rules):
    def get(c, code):
        row = c.execute("SELECT * FROM tickets WHERE code=? AND building_id=?", (code, BUILDING_ID)).fetchone()
        if row is None:
            raise HTTPException(404, "Room incident not found")
        return dict(row)

    def check_version(c, code, version):
        row = c.execute("SELECT version FROM care_ticket_versions WHERE code=?", (code,)).fetchone()
        if row is None or row[0] != version:
            raise HTTPException(409, "This room incident changed. Refresh and review before acting.")

    @app.post("/api/care/facility/tickets/{code}/actions")
    def action(code: str, data: FacilityAction):
        with connect() as c:
            c.execute("BEGIN IMMEDIATE")
            actor = staff(c, data.staff_id)
            ticket = get(c, code)
            check_version(c, code, data.version)
            if data.action not in {"note", "notified"} and actor["role"] not in {"care_lead", "facilities", "manager"}:
                raise HTTPException(403, "Facilities staff or the care lead must coordinate repairs")
            if data.action in {"resolve", "reopen", "note", "merge", "unmerge", "split", "waiting"} and not data.note:
                raise HTTPException(422, "Record an outcome or reason for this action")
            if ticket["merged_into"] and data.action not in {"unmerge", "note"}:
                raise HTTPException(409, "Use the parent incident, or unmerge this incident first")
            if ticket["status"] == "closed" and data.action not in {"reopen", "note", "unmerge"}:
                raise HTTPException(409, "Reopen the room incident before changing it")
            now, extra, result_code = time.time(), [], code
            if data.action == "assign":
                person = c.execute("SELECT * FROM staff_vendors WHERE id=? AND building_id=?", (data.assignee, BUILDING_ID)).fetchone()
                if person is None:
                    raise HTTPException(422, "Choose an existing facilities team member or vendor")
                c.execute("UPDATE tickets SET assignee=?,status=CASE WHEN status='new' THEN 'assigned' ELSE status END WHERE code=?", (data.assignee, code))
                message = "Assigned to " + person["name"] + "; no call or page sent"
            elif data.action == "start":
                if ticket["status"] not in {"assigned", "waiting_tenant"} or not ticket["assignee"]:
                    raise HTTPException(409, "Assign the incident before starting repair work")
                c.execute("UPDATE tickets SET status='in_progress' WHERE code=?", (code,))
                message = "Repair work in progress"
            elif data.action in {"waiting", "resolve"}:
                if ticket["status"] != "in_progress":
                    raise HTTPException(409, "Start repair work before recording a wait or outcome")
                status = "closed" if data.action == "resolve" else "waiting_tenant"
                c.execute("UPDATE tickets SET status=?,closed_at=? WHERE code=?", (status, now if status == "closed" else None, code))
                message = "Repair outcome recorded; individual resident care stays open" if status == "closed" else "Waiting to arrange room access"
            elif data.action == "reopen":
                if ticket["status"] != "closed":
                    raise HTTPException(409, "Only closed incidents can be reopened")
                c.execute("UPDATE tickets SET status=?,closed_at=NULL WHERE code=?", ("assigned" if ticket["assignee"] else "new", code))
                message = "Room incident reopened"
            elif data.action == "notified":
                c.execute("UPDATE tickets SET tenant_notified_at=? WHERE code=?", (now, code))
                message = "Resident update recorded by staff; no message sent by DIZA"
            elif data.action == "merge":
                if data.target_code == code:
                    raise HTTPException(422, "Choose a different incident")
                parent = get(c, data.target_code)
                check_version(c, parent["code"], data.target_version)
                if parent["merged_into"] or parent["status"] == "closed" or parent["category"] != ticket["category"]:
                    raise HTTPException(409, "Merge into an open incident of the same kind")
                children = [row[0] for row in c.execute("SELECT code FROM tickets WHERE merged_into=?", (code,))]
                parent_children = [row[0] for row in c.execute("SELECT code FROM tickets WHERE merged_into=?", (parent["code"],))]
                c.execute("UPDATE tickets SET merged_into=? WHERE code=? OR merged_into=?", (parent["code"], code, code))
                access = 0 if 0 in (parent["access_ok"], ticket["access_ok"]) else 1 if parent["access_ok"] == ticket["access_ok"] == 1 and parent["unit"] == ticket["unit"] else None
                c.execute("UPDATE tickets SET access_ok=? WHERE code=?", (access, parent["code"]))
                group = [get(c, key) for key in {code, parent["code"], *children, *parent_children}]
                highest = min(group, key=lambda item: rules.URGENCIES.index(item["urgency"]))
                for member in group:
                    if rules.URGENCIES.index(member["urgency"]) > rules.URGENCIES.index(highest["urgency"]):
                        c.execute("UPDATE tickets SET urgency=?,urgency_reason=? WHERE code=?", (highest["urgency"], "Shared incident: " + highest["urgency_reason"], member["code"]))
                        rules.tlog(c, member["code"], "urgency", "Urgency raised by the shared incident; unmerging does not lower it", actor["name"], now)
                if highest["urgency"] != "routine":
                    escalate_linked(c, [member["code"] for member in group], "Shared room incident requires urgent review")
                rules.touch(c, parent, now, actor["name"], "merge", f"{code} linked into this shared incident: {data.note}")
                message, extra = "Merged into " + parent["code"], [parent["code"], *children, *parent_children]
            elif data.action == "unmerge":
                if not ticket["merged_into"]:
                    raise HTTPException(409, "This incident is not merged")
                parent = get(c, ticket["merged_into"])
                c.execute("UPDATE tickets SET merged_into=NULL WHERE code=?", (code,))
                rules.touch(c, parent, now, actor["name"], "merge", f"{code} unmerged: {data.note}")
                message, extra = "Unmerged from " + parent["code"], [parent["code"]]
            elif data.action == "split":
                reporters = json.loads(ticket["reporters"])
                mine = [reporter for reporter in reporters if reporter["call_id"] == data.reporter_id]
                if not mine or len(reporters) < 2:
                    raise HTTPException(409, "Choose a reporter from a shared incident")
                result_code = rules.new_code(c)
                reporter = mine[0]
                c.execute("INSERT INTO tickets SELECT ?,building_id,unit,unit_verified,category,urgency,urgency_reason,summary,?,?,access_ok,?,?,NULL,?,?,NULL,NULL,'[]',NULL,NULL,source FROM tickets WHERE code=?", (
                    result_code, reporter["quote"], reporter["language"], json.dumps(mine), "new", reporter["ts"], now, code,
                ))
                c.execute("UPDATE tickets SET reporters=? WHERE code=?", (json.dumps([r for r in reporters if r not in mine]), code))
                c.execute("UPDATE care_requests SET facility_code=? WHERE id=? AND facility_code=?", (result_code, data.reporter_id.removeprefix("care:"), code))
                rules.tlog(c, result_code, "created", f"Split out of {code}: {data.note}", actor["name"], now)
                message, extra = "Reporter separated into " + result_code, [result_code]
            else:
                message = "Facilities handoff note"
            rules.touch(c, ticket, now, actor["name"], data.action, message + (": " + data.note if data.note else ""))
            for changed in {code, *extra}:
                bump(c, changed)
            return {"ok": True, "code": result_code}

    @app.post("/api/care/facility/rooms")
    def edit_room(data: RoomEdit):
        with connect() as c:
            c.execute("BEGIN IMMEDIATE")
            actor = staff(c, data.staff_id)
            if actor["role"] not in {"care_lead", "facilities", "manager"}:
                raise HTTPException(403, "Facilities staff or the care lead must edit room records")
            row = c.execute("SELECT version FROM care_room_versions WHERE room=?", (data.room,)).fetchone()
            if row is None or row[0] != data.version:
                raise HTTPException(409, "This room record changed; refresh before editing")
            new = rules.norm_unit(data.rename_to or data.room)
            if not new:
                raise HTTPException(422, "Use a room number or letter code")
            if new != data.room and c.execute("SELECT 1 FROM units WHERE building_id=? AND unit=?", (BUILDING_ID, new)).fetchone():
                raise HTTPException(409, "That room number is already in use")
            c.execute("UPDATE units SET unit=?,floor=?,stack=?,hvac_zone=? WHERE building_id=? AND unit=?", (new, data.floor, data.stack, data.hvac_zone, BUILDING_ID, data.room))
            c.execute("UPDATE care_room_versions SET room=?,version=version+1 WHERE room=?", (new, data.room))
            if new != data.room:
                c.execute("UPDATE residents SET room=? WHERE room=?", (new, data.room))
                for ticket in c.execute("SELECT * FROM tickets WHERE unit=? AND building_id=?", (data.room, BUILDING_ID)).fetchall():
                    c.execute("UPDATE tickets SET unit=? WHERE code=?", (new, ticket["code"]))
                    rules.tlog(c, ticket["code"], "unit", f"Room renamed {data.room} to {new}", actor["name"])
                    bump(c, ticket["code"])
            # Recalculate relationships after changing a room's riser, floor, or HVAC zone.
            c.execute("UPDATE tickets SET related='[]' WHERE building_id=?", (BUILDING_ID,))
            for ticket in c.execute("SELECT * FROM tickets WHERE building_id=? AND status!='closed' ORDER BY created", (BUILDING_ID,)).fetchall():
                room = c.execute("SELECT * FROM units WHERE building_id=? AND unit=?", (BUILDING_ID, ticket["unit"])).fetchone()
                if room:
                    rules.cross_reference(c, BUILDING_ID, ticket["code"], ticket["category"], dict(room), time.time())
                bump(c, ticket["code"])
            return {"ok": True, "room": new}
