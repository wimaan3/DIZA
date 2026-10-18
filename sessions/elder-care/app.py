"""Care-home operations alongside the existing DIZA engine.

Run from this folder with uvicorn app:app. No external calls are sent here.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
import facility

ROOT = Path(__file__).resolve().parent
CATEGORIES = {
    "urgent_help": "Urgent help",
    "personal_care": "Personal care",
    "medication": "Medication question",
    "meal": "Meals & water",
    "companionship": "Company & activities",
    "maintenance": "Room & maintenance",
    "wellbeing": "Wellbeing follow-up",
}
NURSE_ROLES = {"nurse", "care_lead"}
# These are escalation cues for human review, not a clinical triage model.
# Negative/quoted cues still escalate: staff must review the original words.
DANGER = re.compile(
    r"\b(fall|fallen|fell|chok\w*|bleed\w*|unconscious|unresponsive|"
    r"chest pain|can[’']?t breathe|cannot breathe|not breathing|"
    r"shortness of breath|difficulty breathing|trapped|fire|smoke|gas leak|"
    r"missing resident|suicid\w*|overdose)\b", re.IGNORECASE
)


class CareInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    idempotency_key: str = Field(min_length=1, max_length=120)
    resident_id: str = Field(min_length=1, max_length=80)
    category: Literal["urgent_help", "personal_care", "medication", "meal", "companionship", "maintenance", "wellbeing"]
    urgency: Literal["routine", "urgent"] = "routine"
    summary: str = Field(min_length=3, max_length=1200)
    quote: str = Field(default="", max_length=2000)
    location: str = Field(default="", max_length=200)
    reported_by: str = Field(min_length=1, max_length=100)
    source: Literal["staff", "voice"] = "staff"
    facility_category: Literal["water_leak", "no_heat", "no_hot_water", "electrical", "gas_smell", "lockout", "pest", "appliance", "noise", "security", "other"] = "other"
    access_ok: bool | None = None
    call_id: str = Field(default="", max_length=120)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    staff_id: str = Field(min_length=1, max_length=80)
    action: Literal["accept", "start", "resolve", "escalate", "note"]
    version: int = Field(ge=1)
    note: str = Field(default="", max_length=1200)

    @model_validator(mode="after")
    def require_note(self):
        if self.action in {"resolve", "escalate", "note"} and not self.note:
            raise ValueError("A note is required for this action")
        return self


class ResidentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=80)
    staff_id: str = Field(min_length=1, max_length=80)
    version: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=100)
    room: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    wing: str = Field(min_length=1, max_length=40)
    language: str = Field(min_length=1, max_length=40)
    preferences: str = Field(default="", max_length=1200)
    checkin_enabled: bool = False


class Checkin(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    staff_id: str = Field(min_length=1, max_length=80)
    outcome: Literal["seen_well", "follow_up", "no_response"]
    note: str = Field(default="", max_length=1200)
    idempotency_key: str = Field(min_length=1, max_length=120)


def create_app(db_path=None, *, include_legacy=True):
    db_path = str(db_path or os.getenv("CARE_DB", ROOT / "care.sqlite3"))
    timezone = ZoneInfo(os.getenv("CARE_TIMEZONE", "America/Los_Angeles"))
    demo = os.getenv("DRILL_MODE", "true").lower() == "true"
    # Reuse the existing building rules even in care-only mode, without starting
    # its workers or changing another session's source files.
    os.environ.setdefault("DIZA_DB", str(ROOT / "legacy.sqlite3"))
    engine_path = str(ROOT.parent / "cs2-backend" / "mvp")
    if engine_path not in sys.path:
        sys.path.insert(0, engine_path)
    from backend.app.main import app as engine, connect as engine_connect
    from backend.app import building as building_rules
    legacy = engine if include_legacy else None

    @contextmanager
    def connect():
        connection = sqlite3.connect(db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def stamp():
        return datetime.now(timezone)

    def audit(c, request_id, actor, message):
        c.execute("INSERT INTO care_events VALUES(?,?,?,?,?)", (
            str(uuid.uuid4()), request_id, actor, message, time.time()
        ))

    def initialize():
        with connect() as c:
            c.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS residents (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, room TEXT NOT NULL,
                    wing TEXT NOT NULL, language TEXT NOT NULL, preferences TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS care_staff (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS resident_profiles (
                    resident_id TEXT PRIMARY KEY REFERENCES residents(id),
                    checkin_enabled INTEGER NOT NULL, version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS resident_profile_events (
                    id TEXT PRIMARY KEY, resident_id TEXT NOT NULL REFERENCES residents(id),
                    actor TEXT NOT NULL, details TEXT NOT NULL, created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS care_requests (
                    id TEXT PRIMARY KEY, code TEXT UNIQUE NOT NULL,
                    idempotency_key TEXT UNIQUE NOT NULL, payload_hash TEXT NOT NULL,
                    resident_id TEXT NOT NULL REFERENCES residents(id),
                    category TEXT NOT NULL, urgency TEXT NOT NULL, reason TEXT NOT NULL,
                    summary TEXT NOT NULL, quote TEXT NOT NULL, location TEXT NOT NULL,
                    reported_by TEXT NOT NULL, source TEXT NOT NULL,
                    status TEXT NOT NULL, assignee TEXT REFERENCES care_staff(id),
                    created REAL NOT NULL, updated REAL NOT NULL, version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS care_events (
                    id TEXT PRIMARY KEY, request_id TEXT REFERENCES care_requests(id),
                    actor TEXT NOT NULL, message TEXT NOT NULL, created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS care_checkins (
                    id TEXT PRIMARY KEY, resident_id TEXT NOT NULL REFERENCES residents(id),
                    day TEXT NOT NULL, outcome TEXT NOT NULL,
                    staff_id TEXT NOT NULL REFERENCES care_staff(id),
                    note TEXT NOT NULL, created REAL NOT NULL,
                    idempotency_key TEXT UNIQUE NOT NULL, payload_hash TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS care_queue ON care_requests(status, urgency, created);
                CREATE INDEX IF NOT EXISTS checkin_day ON care_checkins(day, resident_id, created);
            """)
            # Synthetic demo identities only. Never import real resident records here.
            c.executemany("INSERT OR IGNORE INTO residents VALUES(?,?,?,?,?,?)", [
                ("r1", "Margaret Wilson", "101", "Garden", "English", "Speak slowly; prefers a face-to-face check-in."),
                ("r2", "Arthur Bennett", "102", "Garden", "English", "Uses a walking frame; ask before offering assistance."),
                ("r3", "Elena Garcia", "103", "Garden", "Spanish", "Prefers Spanish; enjoys the afternoon reading group."),
                ("r4", "George Park", "201", "Courtyard", "Korean", "Prefers Korean; allow extra time to respond."),
                ("r5", "Rose Thompson", "202", "Courtyard", "English", "Knock and introduce yourself before entering."),
                ("r6", "Samuel Okafor", "203", "Courtyard", "English", "Prefers check-ins after breakfast."),
            ])
            c.executemany("INSERT OR IGNORE INTO care_staff VALUES(?,?,?)", [
                ("nurse-jordan", "Jordan Lee", "nurse"),
                ("care-amira", "Amira Patel", "caregiver"),
                ("lead-morgan", "Morgan Ellis", "care_lead"),
                ("facilities-alex", "Alex Chen", "facilities"),
                ("manager-taylor", "Taylor Brooks", "manager"),
            ])
            c.execute("INSERT OR IGNORE INTO resident_profiles SELECT id,1,1 FROM residents")
            columns = {row[1] for row in c.execute("PRAGMA table_info(care_requests)")}
            for name, declaration in (("facility_code", "TEXT"), ("call_id", "TEXT NOT NULL DEFAULT ''"), ("access_ok", "INTEGER")):
                if name not in columns:
                    c.execute(f"ALTER TABLE care_requests ADD COLUMN {name} {declaration}")
            facility.initialize(c, building_rules, os.getenv("CARE_FACILITY_NAME", "Willow House"))

    @asynccontextmanager
    async def lifespan(application):
        initialize()
        if legacy is not None:
            async with legacy.router.lifespan_context(legacy):
                yield
        else:
            yield

    app = FastAPI(title="DIZA Care", lifespan=lifespan)

    @app.middleware("http")
    async def guard(request, call_next):
        token = os.getenv("OPS_API_TOKEN", "")
        if request.url.path.startswith("/api/care") and token:
            if not hmac.compare_digest(request.headers.get("authorization", ""), "Bearer " + token):
                return JSONResponse({"detail": "Staff access token required"}, status_code=401)
        return await call_next(request)

    def resident(c, rid):
        row = c.execute("SELECT * FROM residents WHERE id=?", (rid,)).fetchone()
        if row is None:
            raise HTTPException(404, "Resident not found; confirm the resident and room")
        return dict(row)

    def staff(c, sid):
        row = c.execute("SELECT * FROM care_staff WHERE id=?", (sid,)).fetchone()
        if row is None:
            raise HTTPException(404, "Staff member not found")
        return dict(row)

    def insert_request(c, data):
        fingerprint = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
        existing = c.execute("SELECT * FROM care_requests WHERE idempotency_key=?", (data.idempotency_key,)).fetchone()
        if existing:
            if existing["payload_hash"] != fingerprint:
                # Preserve idempotency for submissions made by the original care demo.
                original = data.model_dump(exclude={"facility_category", "access_ok", "call_id"})
                old_hash = hashlib.sha256(json.dumps(original, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
                unchanged = data.facility_category == "other" and data.access_ok is None and not data.call_id
                if not unchanged or existing["payload_hash"] != old_hash:
                    raise HTTPException(409, "This submission key was already used for different details")
                c.execute("UPDATE care_requests SET payload_hash=? WHERE id=?", (fingerprint, existing["id"]))
            return dict(existing)
        person = resident(c, data.resident_id)
        danger = DANGER.search(data.summary + " " + data.quote)
        urgent = data.urgency == "urgent" or data.category == "urgent_help" or danger is not None
        reason = (
            f'Escalation cue "{danger.group()}" in original report; nurse review required'
            if danger else "Urgent help reported; nurse review required" if urgent
            else "Everyday care request; staff follow-up required"
        )
        rid, now = str(uuid.uuid4()), time.time()
        code = "C-" + uuid.uuid4().hex[:8].upper()
        c.execute("INSERT INTO care_requests(id,code,idempotency_key,payload_hash,resident_id,category,urgency,reason,summary,quote,location,reported_by,source,status,assignee,created,updated,version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            rid, code, data.idempotency_key, fingerprint, data.resident_id,
            data.category, "urgent" if urgent else "routine", reason, data.summary,
            data.quote, data.location or f'Room {person["room"]} · {person["wing"]} wing',
            data.reported_by, data.source, "new", None, now, now, 1,
        ))
        c.execute("UPDATE care_requests SET call_id=?,access_ok=? WHERE id=?", (data.call_id, data.access_ok, rid))
        if data.category == "maintenance":
            item = dict(c.execute("SELECT * FROM care_requests WHERE id=?", (rid,)).fetchone())
            facility.link_request(c, building_rules, item, data.facility_category, data.access_ok, data.location)
        audit(c, rid, data.reported_by, "Request recorded; awaiting staff acceptance. " + reason)
        return dict(c.execute("SELECT * FROM care_requests WHERE id=?", (rid,)).fetchone())


    def save_request(data):
        with connect() as c:
            c.execute("BEGIN IMMEDIATE")
            return insert_request(c, data)

    @app.get("/api/care/state")
    def state():
        now = stamp()
        with connect() as c:
            checks = [dict(row) for row in c.execute(
                "SELECT * FROM care_checkins WHERE day=? ORDER BY created DESC, rowid DESC", (now.date().isoformat(),)
            )]
            latest = {}
            for check in checks:
                latest.setdefault(check["resident_id"], check)
            residents = []
            for row in c.execute("SELECT * FROM residents ORDER BY room"):
                person = dict(row)
                profile = c.execute("SELECT * FROM resident_profiles WHERE resident_id=?", (person["id"],)).fetchone()
                person["profile_version"] = profile["version"]
                person["checkin_enabled"] = bool(profile["checkin_enabled"])
                person["checkin"] = latest.get(person["id"])
                person["checkin_due"] = person["checkin_enabled"] and person["checkin"] is None and now.hour >= 10
                residents.append(person)
            requests = [dict(row) for row in c.execute(
                "SELECT * FROM care_requests ORDER BY CASE urgency WHEN 'urgent' THEN 0 ELSE 1 END, created"
            )]
            calls = {row["call_id"]: dict(row) for row in c.execute("SELECT * FROM care_call_context")}
            call_ids = list({item["call_id"] for item in requests if item["call_id"]})
            if legacy is not None and call_ids:
                with engine_connect() as old:
                    for row in old.execute(f"SELECT call_id,summary,transcript,status,duration_s FROM calls WHERE call_id IN ({','.join('?' for _ in call_ids)})", call_ids):
                        calls[row["call_id"]] = {**dict(row), "source": "Retell call"}
            return {
                "facility": os.getenv("CARE_FACILITY_NAME", "Willow House"),
                "demo": demo, "timezone": str(timezone), "today": now.date().isoformat(),
                "legacy_available": legacy is not None,
                "server_time": time.time(), "categories": CATEGORIES,
                "residents": residents,
                "staff": [dict(row) for row in c.execute("SELECT * FROM care_staff ORDER BY name")],
                "requests": requests, "facility_workflow": facility.snapshot(c, building_rules),
                "calls": list(calls.values()),
                "events": [dict(row) for row in c.execute("SELECT * FROM care_events ORDER BY created DESC LIMIT 200")],
                "checkins": checks,
            }

    @app.post("/api/care/residents")
    def save_resident(data: ResidentProfile):
        with connect() as c:
            c.execute("BEGIN IMMEDIATE")
            actor = staff(c, data.staff_id)
            if actor["role"] not in {"nurse", "care_lead", "manager"}:
                raise HTTPException(403, "A nurse, care lead or building manager must manage resident profiles")
            existing = c.execute("SELECT * FROM resident_profiles WHERE resident_id=?", (data.id,)).fetchone()
            if (existing["version"] if existing else 0) != data.version:
                raise HTTPException(409, "This resident profile changed. Refresh before saving.")
            room = data.room.upper()
            c.execute("INSERT INTO residents VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,room=excluded.room,wing=excluded.wing,language=excluded.language,preferences=excluded.preferences",
                      (data.id, data.name, room, data.wing, data.language, data.preferences))
            c.execute("INSERT INTO resident_profiles VALUES(?,?,?) ON CONFLICT(resident_id) DO UPDATE SET checkin_enabled=excluded.checkin_enabled,version=excluded.version",
                      (data.id, data.checkin_enabled, data.version + 1))
            # A move changes the resident's address, never an existing physical repair.
            c.execute("INSERT OR IGNORE INTO units VALUES(?,?,?,?,?,?)", (
                facility.BUILDING_ID, room, int(room[0]) if room[0].isdigit() else 1,
                "R" + room[-1], data.wing, data.language,
            ))
            c.execute("INSERT OR IGNORE INTO care_room_versions VALUES(?,1)", (room,))
            c.execute("INSERT INTO resident_profile_events VALUES(?,?,?,?,?)", (
                str(uuid.uuid4()), data.id, actor["name"],
                data.model_dump_json(exclude={"staff_id"}), time.time(),
            ))
            return {**resident(c, data.id), "profile_version": data.version + 1, "checkin_enabled": data.checkin_enabled}

    @app.post("/api/care/requests", status_code=201)
    def new_request(data: CareInput):
        return save_request(data)

    @app.post("/api/care/requests/{rid}/actions")
    def action(rid: str, data: Action):
        with connect() as c:
            c.execute("BEGIN IMMEDIATE")
            person = staff(c, data.staff_id)
            row = c.execute("SELECT * FROM care_requests WHERE id=?", (rid,)).fetchone()
            if row is None:
                raise HTTPException(404, "Request not found")
            item = dict(row)
            if item["version"] != data.version:
                raise HTTPException(409, "This request changed. Refresh and review it before acting.")
            if item["status"] == "resolved":
                raise HTTPException(409, "This request is already resolved; record a new request for a new concern")
            if data.action == "accept":
                if item["status"] != "new":
                    raise HTTPException(409, "Another staff member already accepted this request")
                clinical = item["urgency"] == "urgent" or item["category"] == "medication"
                if clinical and person["role"] not in NURSE_ROLES:
                    raise HTTPException(403, "A nurse or care lead must accept this request")
                if not clinical and person["role"] == "facilities" and item["category"] != "maintenance":
                    raise HTTPException(403, "Facilities staff can accept room and maintenance requests")
                item.update(status="accepted", assignee=data.staff_id)
                message = "Accepted responsibility"
            elif data.action == "escalate":
                if item["urgency"] == "urgent":
                    raise HTTPException(409, "This request is already urgent")
                item["urgency"] = "urgent"
                item["reason"] = "Staff escalation: " + data.note
                owner = staff(c, item["assignee"]) if item["assignee"] else None
                if owner and owner["role"] not in NURSE_ROLES:
                    item.update(status="new", assignee=None)
                message = "Escalated to urgent; nurse review required"
            elif data.action == "note":
                message = "Handoff note"
            else:
                if item["assignee"] != data.staff_id:
                    raise HTTPException(403, "Only the staff member responsible can update progress")
                if data.action == "start":
                    if item["status"] != "accepted":
                        raise HTTPException(409, "Accept the request before starting care")
                    item["status"] = "in_progress"
                    message = "Care in progress"
                else:
                    if item["status"] != "in_progress":
                        raise HTTPException(409, "Start care before recording the outcome")
                    item["status"] = "resolved"
                    message = "Resolved by staff"
            item["updated"] = time.time()
            item["version"] += 1
            c.execute("UPDATE care_requests SET status=?,assignee=?,urgency=?,reason=?,updated=?,version=? WHERE id=?", (
                item["status"], item["assignee"], item["urgency"], item["reason"], item["updated"], item["version"], rid,
            ))
            audit(c, rid, person["name"], message + (": " + data.note if data.note else ""))
            return item

    @app.post("/api/care/residents/{rid}/checkins", status_code=201)
    def checkin(rid: str, data: Checkin):
        day = stamp().date().isoformat()
        fingerprint = hashlib.sha256(json.dumps({"resident": rid, **data.model_dump()}, sort_keys=True).encode()).hexdigest()
        with connect() as c:
            c.execute("BEGIN IMMEDIATE")
            existing = c.execute("SELECT * FROM care_checkins WHERE idempotency_key=?", (data.idempotency_key,)).fetchone()
            if existing:
                if existing["payload_hash"] != fingerprint:
                    raise HTTPException(409, "This check-in key was already used for different details")
                return dict(existing)
            person = resident(c, rid)
            actor = staff(c, data.staff_id)
            if not c.execute("SELECT checkin_enabled FROM resident_profiles WHERE resident_id=?", (rid,)).fetchone()[0]:
                raise HTTPException(409, "Scheduled check-ins are not enabled for this resident")
            if actor["role"] == "facilities":
                raise HTTPException(403, "A care team member must record wellbeing check-ins")
            if data.outcome != "seen_well" and not data.note:
                raise HTTPException(422, "Add an observation for the care team")
            # Never mark a concern as well based only on the selected outcome.
            if data.outcome == "seen_well" and DANGER.search(data.note):
                raise HTTPException(422, "This observation includes an urgent cue. Record follow-up and an urgent request.")
            cid = str(uuid.uuid4())
            c.execute("INSERT INTO care_checkins VALUES(?,?,?,?,?,?,?,?,?)", (
                cid, rid, day, data.outcome, data.staff_id, data.note, time.time(), data.idempotency_key, fingerprint,
            ))
            # A concern always becomes a tracked queue item, never just a roster badge.
            if data.outcome in {"follow_up", "no_response"}:
                req = CareInput(
                    idempotency_key="checkin:" + cid, resident_id=rid, category="wellbeing",
                    summary=("No response at check-in" if data.outcome == "no_response" else "Check-in needs follow-up"),
                    quote=data.note, reported_by=actor["name"],
                )
                # Reuse intake rules within the same transaction.
                insert_request(c, req)
            audit(c, None, actor["name"], f'Check-in for {person["name"]}: {data.outcome.replace("_", " ")}')
            return dict(c.execute("SELECT * FROM care_checkins WHERE id=?", (cid,)).fetchone())

    @app.post("/api/care/demo")
    def load_demo():
        if not demo:
            raise HTTPException(403, "Demo scenarios are disabled")
        samples = [
            ("r2", "urgent_help", "urgent", "Arthur needs a nurse in his room", "I fell by the armchair and need help."),
            ("r3", "meal", "routine", "Water and help choosing lunch", "Could someone bring me water and today's menu?"),
            ("r1", "companionship", "routine", "Would like company this afternoon", "I'd love someone to sit and chat with."),
            ("r5", "maintenance", "routine", "Bedside reading light is not working", "My lamp won't turn on."),
            ("r4", "medication", "routine", "Has a question for the nurse", "I have a question about my medication schedule."),
        ]
        for resident_id, category, urgency, summary, quote in samples:
            save_request(CareInput(
                idempotency_key="demo-v1-" + resident_id, resident_id=resident_id,
                category=category, urgency=urgency, summary=summary, quote=quote, reported_by="Demo scenario",
            ))
        for key, resident_id, summary, quote in [
            ("101-a", "r1", "Heating is not working in room 101", "My room is cold. The heater isn't working."),
            ("103-a", "r3", "Heating is not working in room 103", "The heater is not warming my room."),
            ("101-b", "r1", "Second report of the heating problem in 101", "The room is still cold. Please check the heater."),
        ]:
            save_request(CareInput(idempotency_key="demo-facility-" + key, resident_id=resident_id,
                category="maintenance", urgency="urgent", facility_category="no_heat", summary=summary, quote=quote,
                access_ok=True, reported_by="Demo scenario", call_id="demo-call-" + key))
            with connect() as c:
                c.execute("INSERT OR IGNORE INTO care_call_context VALUES(?,?,?,?)", (
                    "demo-call-" + key, summary,
                    "Agent: Which room are you reporting?\nResident: Room " + ("101" if resident_id == "r1" else "103") + ".\nResident: " + quote,
                    "Synthetic demo transcript",
                ))
        return {"ok": True, "message": "Eight fictional care reports loaded, including linked heating incidents and a duplicate report"}

    async def signed_voice_payload(request):
        raw = await request.body()
        key = os.getenv("RETELL_API_KEY", "")
        if not key:
            raise HTTPException(503, "Retell care intake is not configured")
        from retell.lib.webhook_auth import verify
        if not verify(raw.decode(), key, request.headers.get("x-retell-signature", "")):
            raise HTTPException(401, "Invalid Retell signature")
        try:
            data = json.loads(raw)
            call_id = data["call"]["call_id"]
            if not isinstance(call_id, str) or not call_id:
                raise ValueError("call_id")
            args = dict(data["args"])
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, "A call ID and valid care request details are required") from None
        return call_id, args

    @app.post("/retell/fn/lookup_care_resident")
    async def voice_lookup(request: Request):
        _, args = await signed_voice_payload(request)
        room = args.get("room")
        if not isinstance(room, str) or not room.strip() or len(room) > 30:
            raise HTTPException(422, "A room number is required")
        with connect() as c:
            row = c.execute("SELECT id,name,room,wing,language FROM residents WHERE room=?", (building_rules.norm_unit(room),)).fetchone()
        return {"found": bool(row), "resident": dict(row) if row else None,
                "message": "Read back the resident and room for confirmation" if row else "Ask staff to confirm the room; never guess a resident"}

    @app.post("/retell/fn/create_care_request")
    async def voice_request(request: Request):
        call_id, args = await signed_voice_payload(request)
        try:
            args["source"] = "voice"
            args["idempotency_key"] = "voice:" + hashlib.sha256((call_id + json.dumps(args, sort_keys=True)).encode()).hexdigest()
            args["call_id"] = call_id
            validated = CareInput(**args)
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, "A call ID and valid care request details are required") from None
        item = save_request(validated)
        return {"code": item["code"], "facility_code": item["facility_code"], "urgency": item["urgency"], "status": item["status"],
                "message": "Recorded for staff review. No person has accepted yet; no emergency services have been contacted."}

    @app.get("/care/workspace")
    def care_workspace():
        return FileResponse(ROOT / "web" / "index.html")

    @app.get("/")
    def home():
        if legacy is not None:
            return RedirectResponse("/ops", status_code=307)
        return care_workspace()

    @app.get("/care")
    def dashboard():
        if legacy is not None:
            return RedirectResponse("/building", status_code=307)
        return care_workspace()

    @app.get("/ops")
    @app.get("/building")
    @app.get("/supporter")
    def operations_workspace():
        if legacy is None:
            raise HTTPException(404, "Operations workspace requires CARE_INCLUDE_LEGACY=true")
        entry = ROOT / "dist" / "index.html"
        if not entry.exists():
            raise HTTPException(503, "Build the integrated workspace with npm run build")
        return FileResponse(entry)

    @app.get("/healthz")
    def health():
        with connect() as c:
            c.execute("SELECT 1 FROM residents LIMIT 1")
        return {"status": "ok"}

    facility.register_routes(app, connect, staff, building_rules)
    app.mount("/care-assets", StaticFiles(directory=ROOT / "web"), name="care-assets")
    if legacy is not None and (ROOT / "dist" / "assets").exists():
        app.mount("/assets", StaticFiles(directory=ROOT / "dist" / "assets"), name="workspace-assets")
    if legacy is not None:
        # Existing /ops, /supporter, /text, /api/* and signed voice endpoints survive.
        app.mount("/", legacy)
    return app


app = create_app(include_legacy=os.getenv("CARE_INCLUDE_LEGACY", "true").lower() == "true")
