"""Transactional, version-aware RelayLA domain logic over the existing SQLite volume."""

import hashlib
import hmac
import json
import re
import secrets
import time
import unicodedata
import uuid
from pathlib import Path


class RelayError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message
        super().__init__(message)


def identifier() -> str:
    return uuid.uuid4().hex


def normalize(text: str) -> str:
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
    )
    return " ".join(re.findall(r"[a-z0-9]+", text))


def matches_step(step: str, content: dict) -> bool:
    clauses = re.split(r"[.!?;,]|\b(?:but|pero)\b", step.casefold())
    expected = [
        normalize(value)
        for language in ("en", "es")
        for value in content[language]["next_steps"]
        if normalize(value)
    ]
    for clause in clauses:
        normalized = normalize(clause)
        for phrase in expected:
            match = re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalized)
            if match and not re.search(
                r"\b(?:not|no|never|won t|cannot|can t|didn t|don t|isn t|nunca|"
                r"closed|cerrad[oa]|maybe|perhaps|unsure|tal vez)\b",
                normalized,
            ):
                return True
    return False


class RelayStore:
    def __init__(self, connect):
        self.connect = connect
        self.secret = ""

    def initialize(self):
        with self.connect() as connection:
            connection.executescript((Path(__file__).parent / "schema.sql").read_text())
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(relay_notice_versions)")
            }
            if "title" not in columns:
                connection.execute(
                    "ALTER TABLE relay_notice_versions ADD COLUMN title TEXT NOT NULL DEFAULT ''"
                )
            connection.execute(
                "INSERT OR IGNORE INTO relay_settings VALUES('access_secret',?)",
                (secrets.token_urlsafe(32),),
            )
            self.secret = connection.execute(
                "SELECT value FROM relay_settings WHERE key='access_secret'"
            ).fetchone()[0]

    def token(self, record_id: str) -> str:
        return hmac.new(
            self.secret.encode(), f"relay-resident:{record_id}".encode(), hashlib.sha256
        ).hexdigest()

    def authenticate(self, record_id: str, token: str):
        if not self.secret or not hmac.compare_digest(
            self.token(record_id).encode(), token.encode()
        ):
            raise RelayError(401, "Use the private response link supplied by your coordinator.")

    def _write(self, scope: str, key: str, payload: dict, operation):
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT * FROM relay_receipts WHERE scope=? AND key=?", (scope, key)
            ).fetchone()
            if previous:
                if previous["request_hash"] != digest:
                    raise RelayError(
                        409, "This request key was already used for different details."
                    )
                return json.loads(previous["result"])
            result = operation(connection)
            connection.execute(
                "INSERT INTO relay_receipts VALUES(?,?,?,?,?)",
                (scope, key, digest, json.dumps(result), time.time()),
            )
            return result

    def _notice(self, connection, notice_id: str, version: int | None = None) -> dict:
        notice = connection.execute(
            "SELECT * FROM relay_notices WHERE id=?", (notice_id,)
        ).fetchone()
        if not notice:
            raise RelayError(404, "Notice not found.")
        version = version or notice["current_version"]
        row = connection.execute(
            "SELECT * FROM relay_notice_versions WHERE notice_id=? AND version=?",
            (notice_id, version),
        ).fetchone()
        if not row:
            raise RelayError(409, "This notice version has not been published.")
        return {
            **dict(notice),
            **dict(row),
            "title": row["title"] or notice["title"],
            "content": json.loads(row["content"]),
        }

    def _record(self, connection, record_id: str) -> dict:
        row = connection.execute(
            """
            SELECT r.*,p.name,p.language,p.opt_in,p.source,n.current_version,n.title
            FROM relay_records r JOIN relay_residents p ON p.id=r.resident_id
            JOIN relay_notices n ON n.id=r.notice_id WHERE r.id=?
        """,
            (record_id,),
        ).fetchone()
        if not row:
            raise RelayError(404, "Response record not found.")
        if not row["opt_in"]:
            raise RelayError(403, "This resident has not opted in.")
        return dict(row)

    def _event(self, connection, record: dict, version: int, type_: str, detail: dict):
        connection.execute(
            """
            INSERT INTO relay_events(record_id,notice_id,version,type,detail,ts) VALUES(?,?,?,?,?,?)
        """,
            (
                record.get("id"),
                record["notice_id"],
                version,
                type_,
                json.dumps(detail),
                time.time(),
            ),
        )

    def _enroll(self, connection, resident_id: str, notice_id: str, version: int) -> str:
        record_id = identifier()
        now = time.time()
        connection.execute(
            """
            INSERT OR IGNORE INTO relay_records(id,resident_id,notice_id,updated) VALUES(?,?,?,?)
        """,
            (record_id, resident_id, notice_id, now),
        )
        record_id = connection.execute(
            "SELECT id FROM relay_records WHERE resident_id=? AND notice_id=?",
            (resident_id, notice_id),
        ).fetchone()[0]
        connection.execute(
            "INSERT OR IGNORE INTO relay_followups VALUES(?,?,'open',?,?,?)",
            (record_id, version, "notice_not_confirmed", now, now),
        )
        return record_id

    def publish(self, notice_id: str, payload: dict) -> dict:
        def operation(connection):
            now = time.time()
            previous = connection.execute(
                "SELECT * FROM relay_notices WHERE id=?", (notice_id,)
            ).fetchone()
            current = previous["current_version"] if previous else 0
            if current != payload["expected_version"]:
                raise RelayError(
                    409, "Someone published a newer notice. Refresh before publishing."
                )
            for lang in ("en", "es"):
                if not all(normalize(step) for step in payload["content"][lang]["next_steps"]):
                    raise RelayError(422, "Every accepted next step must contain words.")
            version = current + 1
            if not previous:
                connection.execute(
                    "INSERT INTO relay_notices VALUES(?,?,?,'organization',?)",
                    (notice_id, payload["title"], version, now),
                )
            else:
                connection.execute(
                    "UPDATE relay_notices SET title=?,current_version=? WHERE id=?",
                    (payload["title"], version, notice_id),
                )
            connection.execute(
                "INSERT INTO relay_notice_versions VALUES(?,?,?,?,?,?,?)",
                (
                    notice_id,
                    version,
                    json.dumps(payload["content"]),
                    payload["reason"],
                    payload["published_by"],
                    now,
                    payload["title"],
                ),
            )
            for resident in connection.execute(
                "SELECT id FROM relay_residents WHERE opt_in=1"
            ).fetchall():
                record_id = self._enroll(connection, resident["id"], notice_id, version)
                connection.execute(
                    """
                    UPDATE relay_followups SET status='superseded',updated=?
                    WHERE record_id=? AND version<? AND status='open'
                """,
                    (now, record_id, version),
                )
            self._event(
                connection,
                {"notice_id": notice_id},
                version,
                "notice_published",
                {"reason": payload["reason"], "published_by": payload["published_by"]},
            )
            return {"notice_id": notice_id, "published_version": version}

        result = self._write("publish:" + notice_id, payload["idempotency_key"], payload, operation)
        return {**result, "notice": self.notice(notice_id)}

    def notice(self, notice_id: str) -> dict:
        with self.connect() as connection:
            return self._notice(connection, notice_id)

    def add_resident(self, payload: dict) -> dict:
        if payload["opt_in"] is not True:
            raise RelayError(422, "Only an opted-in resident can be enrolled.")

        def operation(connection):
            resident_id = identifier()
            connection.execute(
                "INSERT INTO relay_residents VALUES(?,?,?,1,'organization',?)",
                (resident_id, payload["name"], payload["language"], time.time()),
            )
            notice = connection.execute(
                "SELECT * FROM relay_notices ORDER BY created DESC LIMIT 1"
            ).fetchone()
            record_id = (
                self._enroll(connection, resident_id, notice["id"], notice["current_version"])
                if notice
                else None
            )
            return {"resident_id": resident_id, "record_id": record_id}

        return self._write("resident", payload["idempotency_key"], payload, operation)

    def _context(self, connection, record_id: str, *, history: bool = False) -> dict:
        record = self._record(connection, record_id)
        notice = self._notice(connection, record["notice_id"])
        confirmations = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM relay_confirmations WHERE record_id=? ORDER BY version", (record_id,)
            )
        ]
        latest = next((row for row in confirmations if row["version"] == notice["version"]), None)
        assistance = connection.execute(
            "SELECT * FROM relay_assistance WHERE record_id=?", (record_id,)
        ).fetchone()
        if record["clarification_version"] == notice["version"]:
            status = "needs_clarification"
        elif latest:
            status = "confirmed_current"
        elif confirmations:
            status = "updated_notice_awaiting_confirmation"
        elif record["draft_step"] or record["assistance_needed"] is not None:
            status = "awaiting_confirmation"
        else:
            status = "no_response"
        missing = (
            ([] if latest and status == "confirmed_current" else ["instruction_confirmation"])
            + (["assistance_answer"] if record["assistance_needed"] is None else [])
            + (
                ["assistance_confirmation"]
                if record["assistance_needed"] and not record["assistance_confirmed"]
                else []
            )
        )
        result = {
            "record_id": record_id,
            "resident": {key: record[key] for key in ("name", "language", "source")},
            "notice": notice,
            "communication_status": status,
            "confirmed_version": confirmations[-1]["version"] if confirmations else None,
            "confirmed_next_step": latest["next_step"] if latest else None,
            "draft": {
                "next_step": record["draft_step"] or "",
                "notice_version": record["draft_version"],
                "assistance_needed": None
                if record["assistance_needed"] is None
                else bool(record["assistance_needed"]),
                "assistance_details": record["assistance_details"] or "",
                "assistance_confirmed": bool(record["assistance_confirmed"]),
            },
            "assistance": dict(assistance) if assistance else None,
            "missing": missing,
            "last_attempt_at": record["last_attempt_at"],
            "confirmation_history": confirmations,
        }
        if history:
            result["events"] = [
                {**dict(row), "detail": json.loads(row["detail"])}
                for row in connection.execute(
                    "SELECT * FROM relay_events WHERE record_id=? ORDER BY id DESC LIMIT 50",
                    (record_id,),
                )
            ]
        return result

    def context(self, record_id: str, *, history: bool = False) -> dict:
        with self.connect() as connection:
            return self._context(connection, record_id, history=history)

    def respond(self, record_id: str, payload: dict, *, channel: str = "text") -> dict:
        def operation(connection):
            record = self._record(connection, record_id)
            version = self._notice(connection, record["notice_id"], payload["notice_version"])
            now, step = time.time(), payload.get("next_step", "").strip()
            needed = payload.get("assistance_needed")
            details = payload.get("assistance_details", "").strip()
            confirmed = (
                payload.get("confirm_instruction", False)
                and not payload.get("needs_clarification", False)
                and matches_step(step, version["content"])
            )
            clarification = payload.get("needs_clarification", False) or (
                payload.get("confirm_instruction", False) and not confirmed
            )
            connection.execute(
                """
                UPDATE relay_records SET draft_step=?,draft_version=?,last_attempt_at=?,updated=?,
                    clarification_version=CASE WHEN ? THEN ? ELSE clarification_version END
                WHERE id=?
            """,
                (
                    step or record["draft_step"],
                    version["version"] if step else record["draft_version"],
                    now,
                    now,
                    clarification,
                    version["version"],
                    record_id,
                ),
            )
            if confirmed:
                connection.execute(
                    """INSERT INTO relay_confirmations VALUES(?,?,?,?,?)
                       ON CONFLICT(record_id,version) DO UPDATE SET
                       next_step=excluded.next_step,channel=excluded.channel,
                       confirmed_at=excluded.confirmed_at""",
                    (record_id, version["version"], step, channel, now),
                )
                connection.execute(
                    """UPDATE relay_records SET clarification_version=
                       CASE WHEN clarification_version=? THEN NULL ELSE clarification_version END
                       WHERE id=?""",
                    (version["version"], record_id),
                )
                self._event(
                    connection,
                    record,
                    version["version"],
                    "instruction_confirmed",
                    {"next_step": step, "channel": channel},
                )
            elif clarification:
                self._event(
                    connection,
                    record,
                    version["version"],
                    "clarification_requested",
                    {"response": step, "channel": channel},
                )
            if needed is not None:
                if needed and not details:
                    raise RelayError(422, "Describe the assistance needed before saving it.")
                connection.execute(
                    """
                    UPDATE relay_records SET assistance_needed=?,assistance_details=?,
                        assistance_confirmed=? WHERE id=?
                """,
                    (
                        int(needed),
                        details,
                        int(bool(payload.get("confirm_assistance")) or not needed),
                        record_id,
                    ),
                )
                if needed and payload.get("confirm_assistance"):
                    old = connection.execute(
                        "SELECT * FROM relay_assistance WHERE record_id=?", (record_id,)
                    ).fetchone()
                    if not old:
                        connection.execute(
                            "INSERT INTO relay_assistance "
                            "VALUES(?,?,?,'requested',NULL,1,?,?,?,NULL)",
                            (identifier(), record_id, details, version["version"], now, now),
                        )
                    elif old["status"] == "completed" and details != old["details"]:
                        connection.execute(
                            """
                            UPDATE relay_assistance SET details=?,status='requested',owner=NULL,
                                revision=revision+1,requested_version=?,updated=?,completed_at=NULL
                            WHERE id=?
                        """,
                            (details, version["version"], now, old["id"]),
                        )
                    elif details != old["details"]:
                        connection.execute(
                            """UPDATE relay_assistance SET details=?,
                               revision=revision+1,updated=? WHERE id=?""",
                            (details, now, old["id"]),
                        )
                    self._event(
                        connection,
                        record,
                        version["version"],
                        "assistance_confirmed",
                        {"details": details, "channel": channel},
                    )
                elif needed:
                    self._event(
                        connection,
                        record,
                        version["version"],
                        "assistance_draft_saved",
                        {"details": details, "channel": channel},
                    )
            context = self._context(connection, record_id)
            if context["communication_status"] == "confirmed_current" and not context["missing"]:
                connection.execute(
                    """UPDATE relay_followups SET status='complete',updated=?
                       WHERE record_id=? AND version=?""",
                    (now, record_id, context["notice"]["version"]),
                )
            else:
                connection.execute(
                    """UPDATE relay_followups SET status='open',reason=?,updated=?
                       WHERE record_id=? AND version=?""",
                    (
                        "clarification" if clarification else "response_incomplete",
                        now,
                        record_id,
                        context["notice"]["version"],
                    ),
                )
            return {
                "saved_version": version["version"],
                "instruction_confirmed": bool(confirmed),
                "assistance_saved": bool(needed),
                "channel": channel,
            }

        receipt = self._write(
            "response:" + record_id, payload["idempotency_key"], payload, operation
        )
        context = self.context(record_id)
        return {
            **receipt,
            "stale": receipt["saved_version"] != context["notice"]["version"],
            "context": context,
        }

    def decide(self, task_id: str, payload: dict) -> dict:
        def operation(connection):
            task = connection.execute(
                "SELECT * FROM relay_assistance WHERE id=?", (task_id,)
            ).fetchone()
            if not task:
                raise RelayError(404, "Assistance request not found.")
            if task["revision"] != payload["expected_revision"]:
                raise RelayError(409, "This task changed. Refresh before updating it.")
            if payload["action"] == "accept":
                if task["status"] != "requested":
                    raise RelayError(409, "This task is already owned or completed.")
                status = "accepted"
            else:
                if task["status"] != "accepted" or task["owner"] != payload["owner"]:
                    raise RelayError(409, "The accepting coordinator must record completion.")
                status = "completed"
            now = time.time()
            connection.execute(
                """UPDATE relay_assistance SET status=?,owner=?,revision=revision+1,
                   updated=?,completed_at=? WHERE id=?""",
                (status, payload["owner"], now, now if status == "completed" else None, task_id),
            )
            record = self._record(connection, task["record_id"])
            self._event(
                connection,
                record,
                record["current_version"],
                "assistance_" + status,
                {"owner": payload["owner"], "task_id": task_id},
            )
            return {"record_id": task["record_id"], "task_id": task_id, "status": status}

        return self._write("task:" + task_id, payload["idempotency_key"], payload, operation)

    def contact_attempt(self, record_id: str, payload: dict) -> dict:
        def operation(connection):
            record = self._record(connection, record_id)
            now, attempt_id = time.time(), identifier()
            connection.execute(
                "INSERT INTO relay_attempts VALUES(?,?,?,?,?,NULL,?,?)",
                (
                    attempt_id,
                    record_id,
                    record["current_version"],
                    "coordinator",
                    payload["result"],
                    now,
                    now,
                ),
            )
            connection.execute(
                "UPDATE relay_records SET last_attempt_at=?,updated=? WHERE id=?",
                (now, now, record_id),
            )
            self._event(
                connection, record, record["current_version"], "contact_" + payload["result"], {}
            )
            return {"attempt_id": attempt_id, "result": payload["result"]}

        return self._write("contact:" + record_id, payload["idempotency_key"], payload, operation)

    def dashboard(self) -> dict:
        with self.connect() as connection:
            connection.execute("BEGIN")
            notice = connection.execute(
                "SELECT id FROM relay_notices ORDER BY created DESC LIMIT 1"
            ).fetchone()
            if not notice:
                return {"notice": None, "records": [], "counts": {}, "versions": []}
            rows = connection.execute(
                "SELECT id FROM relay_records WHERE notice_id=? ORDER BY updated DESC",
                (notice["id"],),
            ).fetchall()
            records = [self._context(connection, row["id"]) for row in rows]
            for record in records:
                record["response_url"] = (
                    f"/respond/{record['record_id']}#{self.token(record['record_id'])}"
                )
            counts = {
                "residents": len(records),
                "confirmed_current": sum(
                    r["communication_status"] == "confirmed_current" for r in records
                ),
                "updated_pending": sum(
                    r["communication_status"] == "updated_notice_awaiting_confirmation"
                    for r in records
                ),
                "needs_clarification": sum(
                    r["communication_status"] == "needs_clarification" for r in records
                ),
                "no_response": sum(r["communication_status"] == "no_response" for r in records),
                "assistance_open": sum(
                    bool(r["assistance"] and r["assistance"]["status"] != "completed")
                    for r in records
                ),
            }
            versions = [
                self._notice(connection, notice["id"], row[0])
                for row in connection.execute(
                    """SELECT version FROM relay_notice_versions
                       WHERE notice_id=? ORDER BY version DESC""",
                    (notice["id"],),
                ).fetchall()
            ]
            return {
                "notice": self._notice(connection, notice["id"]),
                "records": records,
                "counts": counts,
                "versions": versions,
            }

    def seed_demo(self) -> dict:
        """Explicit operator action; never runs automatically against production data."""
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT id FROM relay_notices LIMIT 1").fetchone()
            if existing:
                raise RelayError(409, "A notice already exists. Demo data will not replace it.")
            now, notice_id = time.time(), identifier()
            content = {
                "en": {
                    "text": "Today's community shuttle pickup is at the north entrance. "
                    "Please arrive by 3:00 PM.",
                    "question": "Which entrance will you use?",
                    "next_steps": ["north entrance", "north door"],
                },
                "es": {
                    "text": "La recogida de hoy del transporte comunitario es en la entrada norte. "
                    "Por favor, llega a las 3:00 p. m.",
                    "question": "¿Qué entrada usarás?",
                    "next_steps": ["entrada norte", "entrada del norte"],
                },
            }
            connection.execute(
                "INSERT INTO relay_notices VALUES(?,? ,1,'synthetic',?)",
                (notice_id, "Community shuttle pickup", now),
            )
            connection.execute(
                "INSERT INTO relay_notice_versions VALUES(?,1,?,?,?,?,?)",
                (
                    notice_id,
                    json.dumps(content),
                    "Everyday pickup coordination",
                    "Demo coordinator",
                    now,
                    "Community shuttle pickup",
                ),
            )
            for name, language in (
                ("Marisol (demo)", "es"),
                ("Evelyn (demo)", "en"),
                ("Sam (demo)", "en"),
                ("Luis (demo)", "es"),
            ):
                resident_id = identifier()
                connection.execute(
                    "INSERT INTO relay_residents VALUES(?,?,?,1,'synthetic',?)",
                    (resident_id, name, language, now),
                )
                record_id = self._enroll(connection, resident_id, notice_id, 1)
                if name.startswith("Evelyn"):
                    connection.execute(
                        "INSERT INTO relay_confirmations "
                        "VALUES(?,1,'I will use the north entrance','demo',?)",
                        (record_id, now),
                    )
                    connection.execute(
                        """UPDATE relay_records SET assistance_needed=0,
                           assistance_confirmed=1,last_attempt_at=? WHERE id=?""",
                        (now, record_id),
                    )
                    connection.execute(
                        "UPDATE relay_followups SET status='complete' WHERE record_id=?",
                        (record_id,),
                    )
                elif name.startswith("Sam"):
                    connection.execute(
                        """UPDATE relay_records SET clarification_version=1,
                           last_attempt_at=? WHERE id=?""",
                        (now, record_id),
                    )
            return {"notice_id": notice_id, "source": "synthetic"}
