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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    legacy = None
    if include_legacy:
        # Import the existing engine without editing another session's files.
        os.environ.setdefault("DIZA_DB", str(ROOT / "legacy.sqlite3"))
        sys.path.insert(0, str(ROOT.parent / "cs2-backend" / "mvp"))
        from backend.app.main import app as legacy

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
            ])

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
                raise HTTPException(409, "This submission key was already used for different details")
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
        c.execute("INSERT INTO care_requests VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            rid, code, data.idempotency_key, fingerprint, data.resident_id,
            data.category, "urgent" if urgent else "routine", reason, data.summary,
            data.quote, data.location or f'Room {person["room"]} · {person["wing"]} wing',
            data.reported_by, data.source, "new", None, now, now, 1,
        ))
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
                person["checkin"] = latest.get(person["id"])
                person["checkin_due"] = person["checkin"] is None and now.hour >= 10
                residents.append(person)
            return {
                "facility": os.getenv("CARE_FACILITY_NAME", "Willow House"),
                "demo": demo, "timezone": str(timezone), "today": now.date().isoformat(),
                "legacy_available": legacy is not None,
                "server_time": time.time(), "categories": CATEGORIES,
                "residents": residents,
                "staff": [dict(row) for row in c.execute("SELECT * FROM care_staff ORDER BY name")],
                "requests": [dict(row) for row in c.execute(
                    "SELECT * FROM care_requests ORDER BY CASE urgency WHEN 'urgent' THEN 0 ELSE 1 END, created"
                )],
                "events": [dict(row) for row in c.execute("SELECT * FROM care_events ORDER BY created DESC LIMIT 200")],
                "checkins": checks,
            }

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
        return {"ok": True, "message": "Five fictional scenarios loaded; repeated loads keep the same requests"}

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
            row = c.execute("SELECT id,name,room,wing,language FROM residents WHERE room=?", (room.strip(),)).fetchone()
        return {"found": bool(row), "resident": dict(row) if row else None,
                "message": "Read back the resident and room for confirmation" if row else "Ask staff to confirm the room; never guess a resident"}

    @app.post("/retell/fn/create_care_request")
    async def voice_request(request: Request):
        call_id, args = await signed_voice_payload(request)
        try:
            args["source"] = "voice"
            args["idempotency_key"] = "voice:" + hashlib.sha256((call_id + json.dumps(args, sort_keys=True)).encode()).hexdigest()
            validated = CareInput(**args)
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, "A call ID and valid care request details are required") from None
        item = save_request(validated)
        return {"code": item["code"], "urgency": item["urgency"], "status": item["status"],
                "message": "Recorded for staff review. No person has accepted yet; no emergency services have been contacted."}

    @app.get("/")
    @app.get("/care")
    def dashboard():
        return FileResponse(ROOT / "web" / "index.html")

    @app.get("/healthz")
    def health():
        with connect() as c:
            c.execute("SELECT 1 FROM residents LIMIT 1")
        return {"status": "ok"}

    app.mount("/care-assets", StaticFiles(directory=ROOT / "web"), name="care-assets")
    if legacy is not None:
        # Existing /ops, /supporter, /text, /api/* and signed voice endpoints survive.
        app.mount("/", legacy)
    return app


app = create_app(include_legacy=os.getenv("CARE_INCLUDE_LEGACY", "true").lower() == "true")
