"""Persistent demo conversations and staff tasks with transactional request receipts."""

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from . import assistant


class HotelError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


class HotelStore:
    def __init__(self, database):
        self.database = Path(database)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self, seed=False):
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript((Path(__file__).parent / "schema.sql").read_text())
            connection.executemany(
                "INSERT OR IGNORE INTO hotel_rooms VALUES(?,?)",
                [(str(floor * 100 + room), floor) for floor in (3, 4) for room in range(1, 13)],
            )
            connection.executemany(
                "INSERT OR IGNORE INTO hotel_staff VALUES(?,?,?)",
                [
                    ("noa", "Noa Chen", "front_desk"),
                    ("eli", "Eli Rivera", "maintenance"),
                    ("ana", "Ana Morales", "housekeeping"),
                ],
            )
            if seed and not connection.execute("SELECT id FROM hotel_tickets LIMIT 1").fetchone():
                for room, category, quote, minutes, status, owner in [
                    (
                        "412",
                        "air_conditioning",
                        "The air conditioning is blowing warm air.",
                        18,
                        "new",
                        None,
                    ),
                    (
                        "408",
                        "housekeeping",
                        "Could we have two extra towels, please?",
                        9,
                        "new",
                        None,
                    ),
                    (
                        "307",
                        "water_leak",
                        "There is a steady drip under the bathroom sink.",
                        26,
                        "assigned",
                        "eli",
                    ),
                    (
                        "409",
                        "air_conditioning",
                        "The room is warm even with the AC on.",
                        35,
                        "in_progress",
                        "eli",
                    ),
                    (
                        "405",
                        "lighting",
                        "The bedside reading light was not working.",
                        70,
                        "completed",
                        "eli",
                    ),
                ]:
                    session = self._new_session(connection, room, "en")
                    self._ticket(
                        connection,
                        session,
                        category,
                        quote,
                        False,
                        "priority" if category == "water_leak" else "routine",
                        minutes,
                        status,
                        owner,
                    )

    def _new_session(self, connection, room, language):
        if not connection.execute(
            "SELECT number FROM hotel_rooms WHERE number=?", (room,)
        ).fetchone():
            raise HotelError(422, "Choose a room from this demo hotel's room list.")
        now, identity, token = time.time(), uuid.uuid4().hex, secrets.token_urlsafe(32)
        connection.execute(
            "INSERT INTO hotel_sessions VALUES(?,?,?,?,1,NULL,?,?)",
            (identity, token, room, language, now, now),
        )
        self._message(connection, identity, "assistant", assistant.greeting(room, language))
        return dict(
            connection.execute("SELECT * FROM hotel_sessions WHERE id=?", (identity,)).fetchone()
        )

    def _write(self, scope, payload, operation):
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            old = connection.execute(
                "SELECT * FROM hotel_receipts WHERE scope=? AND key=?",
                (scope, payload["idempotency_key"]),
            ).fetchone()
            if old:
                if old["digest"] != digest:
                    raise HotelError(
                        409, "This request key was already used for different details."
                    )
                return json.loads(old["result"])
            result = operation(connection)
            connection.execute(
                "INSERT INTO hotel_receipts VALUES(?,?,?,?)",
                (scope, payload["idempotency_key"], digest, json.dumps(result)),
            )
            return result

    def start(self, payload):
        def operation(connection):
            session = self._new_session(connection, payload["room"], payload["language"])
            return {"session_id": session["id"], "token": session["token"]}

        return self._write("start", payload, operation)

    def authenticate(self, identity, token):
        with self.connect() as connection:
            session = self._session(connection, identity)
        if not hmac.compare_digest(session["token"].encode(), token.encode()):
            raise HotelError(
                401, "This guest session is private. Start your own demo conversation."
            )

    def _session(self, connection, identity):
        row = connection.execute("SELECT * FROM hotel_sessions WHERE id=?", (identity,)).fetchone()
        if not row:
            raise HotelError(404, "Guest conversation not found.")
        return dict(row)

    def _message(self, connection, identity, role, text):
        connection.execute(
            "INSERT INTO hotel_messages(session_id,role,text,created) VALUES(?,?,?,?)",
            (identity, role, text, time.time()),
        )

    def _event(self, connection, ticket, identity, kind, detail):
        connection.execute(
            "INSERT INTO hotel_events(ticket_id,session_id,type,detail,created) VALUES(?,?,?,?,?)",
            (ticket, identity, kind, detail, time.time()),
        )

    def _ticket(
        self,
        connection,
        session,
        category,
        quote,
        access,
        urgency,
        minutes=0,
        status="new",
        owner=None,
    ):
        label, department = assistant.CATEGORIES[category]
        now = time.time() - minutes * 60
        cursor = connection.execute(
            """INSERT INTO hotel_tickets(session_id,room,category,department,urgency,summary,
               quote,language,access_ok,status,assignee,created,updated,completed)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                session["id"],
                session["room"],
                category,
                department,
                urgency,
                label,
                quote,
                session["language"],
                int(access),
                status,
                owner,
                now,
                now,
                now if status == "completed" else None,
            ),
        )
        self._event(
            connection, cursor.lastrowid, session["id"], "created", "Guest request recorded"
        )
        return cursor.lastrowid

    def message(self, identity, payload):
        def operation(connection):
            session = self._session(connection, identity)
            reply = assistant.respond(payload["text"], session["room"], session["language"])
            self._message(connection, identity, "guest", payload["text"])
            self._message(connection, identity, "assistant", reply["text"])
            pending = session["pending"]
            if reply["kind"] == "request":
                pending = json.dumps(reply)
            elif reply["kind"] == "safety":
                self._ticket(connection, session, "safety", payload["text"], False, "emergency")
                pending = None
            elif reply["kind"] == "answer":
                self._event(
                    connection, None, identity, "answered", "Approved hotel answer provided"
                )
            connection.execute(
                "UPDATE hotel_sessions SET pending=?,revision=revision+1,updated=? WHERE id=?",
                (pending, time.time(), identity),
            )
            return {"kind": reply["kind"]}

        self._write("message:" + identity, payload, operation)
        return self.session(identity)

    def confirm(self, identity, payload):
        def operation(connection):
            session = self._session(connection, identity)
            if session["revision"] != payload["expected_revision"] or not session["pending"]:
                raise HotelError(409, "The request changed. Review the latest details first.")
            spanish = session["language"] == "es"
            ticket_id = None
            if payload["confirmed"]:
                pending = json.loads(session["pending"])
                ticket_id = self._ticket(
                    connection,
                    session,
                    pending["category"],
                    pending["quote"],
                    payload["access_ok"],
                    pending["urgency"],
                )
                code = f"H-{1000 + ticket_id}"
                text = (
                    f"Solicitud {code} registrada. Está esperando que el personal la acepte. "
                    "Aún no hay una hora de finalización confirmada."
                    if spanish
                    else f"Request {code} is recorded and awaiting staff acceptance. "
                    "There is no confirmed completion time yet."
                )
            else:
                text = (
                    "He descartado el borrador. ¿En qué más puedo ayudarte?"
                    if spanish
                    else ("I’ve discarded that draft. What else can I help with?")
                )
            self._message(connection, identity, "assistant", text)
            connection.execute(
                "UPDATE hotel_sessions SET pending=NULL,revision=revision+1,updated=? WHERE id=?",
                (time.time(), identity),
            )
            return {"ticket_id": ticket_id}

        self._write("confirm:" + identity, payload, operation)
        return self.session(identity)

    def _tickets(self, connection):
        tickets = [
            dict(row)
            for row in connection.execute(
                """SELECT t.*,s.name AS owner FROM hotel_tickets t
               LEFT JOIN hotel_staff s ON s.id=t.assignee
               ORDER BY CASE t.urgency WHEN 'emergency' THEN 0 WHEN 'priority' THEN 1 ELSE 2 END,
               t.created ASC"""
            )
        ]
        for ticket in tickets:
            ticket["code"] = f"H-{1000 + ticket['id']}"
            ticket["access_ok"] = bool(ticket["access_ok"])
            ticket["related"] = [
                {
                    "code": f"H-{1000 + other['id']}",
                    "room": other["room"],
                    "reason": "Same category and floor",
                }
                for other in tickets
                if other["id"] != ticket["id"]
                and other["category"] == ticket["category"]
                and other["room"][0] == ticket["room"][0]
                and abs(other["created"] - ticket["created"]) <= 7 * 86400
            ]
        return tickets

    def session(self, identity):
        with self.connect() as connection:
            session = self._session(connection, identity)
            return {
                "id": identity,
                "room": session["room"],
                "language": session["language"],
                "revision": session["revision"],
                "pending": json.loads(session["pending"]) if session["pending"] else None,
                "messages": [
                    dict(row)
                    for row in connection.execute(
                        "SELECT role,text,created,id FROM hotel_messages "
                        "WHERE session_id=? ORDER BY id",
                        (identity,),
                    )
                ],
                "tickets": [
                    self._public_ticket(t)
                    for t in self._tickets(connection)
                    if t["session_id"] == identity
                ],
            }

    def _public_ticket(self, ticket):
        return {
            key: ticket[key] for key in ("code", "room", "summary", "status", "owner", "updated")
        }

    def dashboard(self):
        with self.connect() as connection:
            connection.execute("BEGIN")
            tickets = self._tickets(connection)
            answered = connection.execute(
                "SELECT COUNT(*) FROM hotel_events WHERE type='answered'"
            ).fetchone()[0]
            return {
                "hotel": "Harbor House",
                "scenario": "Synthetic hotel demo",
                "rooms": [
                    dict(row)
                    for row in connection.execute("SELECT * FROM hotel_rooms ORDER BY number")
                ],
                "staff": [
                    dict(row)
                    for row in connection.execute("SELECT * FROM hotel_staff ORDER BY name")
                ],
                "tickets": tickets,
                "counts": {
                    "open": sum(t["status"] != "completed" for t in tickets),
                    "priority": sum(
                        t["urgency"] != "routine" and t["status"] != "completed" for t in tickets
                    ),
                    "in_progress": sum(t["status"] == "in_progress" for t in tickets),
                    "answered": answered,
                },
            }

    def update(self, ticket_id, payload):
        def operation(connection):
            row = connection.execute(
                "SELECT * FROM hotel_tickets WHERE id=?", (ticket_id,)
            ).fetchone()
            if not row:
                raise HotelError(404, "Request not found.")
            ticket = dict(row)
            if ticket["revision"] != payload["expected_revision"]:
                raise HotelError(409, "Someone updated this request. Refresh before continuing.")
            action = payload["action"]
            now, owner, status = time.time(), ticket["assignee"], ticket["status"]
            if action == "assign":
                if status != "new":
                    raise HotelError(409, "This request already has an owner or is completed.")
                staff = connection.execute(
                    "SELECT * FROM hotel_staff WHERE id=?", (payload["staff_id"],)
                ).fetchone()
                if not staff or staff["department"] not in {ticket["department"], "front_desk"}:
                    raise HotelError(422, "Choose a staff member from the responsible team.")
                owner, status = staff["id"], "assigned"
                detail = f"Accepted by {staff['name']}"
            elif action in {"start", "complete"}:
                required = "assigned" if action == "start" else "in_progress"
                if status != required or not owner:
                    raise HotelError(
                        409, "Accept the request, then start work before completing it."
                    )
                status = "in_progress" if action == "start" else "completed"
                detail = "Work started" if action == "start" else "Completion recorded by staff"
            else:
                detail = payload["note"].strip()
                if not detail:
                    raise HotelError(422, "Write a note before saving it.")
            connection.execute(
                """UPDATE hotel_tickets SET assignee=?,status=?,revision=revision+1,
                   updated=?,completed=? WHERE id=?""",
                (
                    owner,
                    status,
                    now,
                    now if action == "complete" else ticket["completed"],
                    ticket_id,
                ),
            )
            self._event(connection, ticket_id, ticket["session_id"], action, detail)
            return {"ticket_id": ticket_id, "status": status}

        return self._write("task:" + str(ticket_id), payload, operation)

    def detail(self, ticket_id):
        with self.connect() as connection:
            ticket = next((t for t in self._tickets(connection) if t["id"] == ticket_id), None)
            if not ticket:
                raise HotelError(404, "Request not found.")
            ticket["events"] = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM hotel_events WHERE ticket_id=? ORDER BY id DESC", (ticket_id,)
                )
            ]
            return ticket
