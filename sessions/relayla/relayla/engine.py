"""Durable, provider-independent follow-through for the synthetic RelayLA demo.

The store accepts an upstream severity label. It does not infer medical urgency,
place calls, dispatch resources, or treat delivery as comprehension. Every command
and its audit trail commit in the same SQLite transaction.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PRIORITIES = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
CONTACT_OUTCOMES = {"connected", "dropped", "no_answer", "resumed", "ended"}
ZONE_LEVELS = {"normal", "watch", "ask", "crisis", "stand_down"}
ACTIVE_WORK = {"requested", "assigned", "accepted"}
CALLBACK_RANK = {"none": 0, "retry_pending": 1, "contact_review": 2, "human_review": 3}
OPERATOR_ACTIONS = {"revise_notice", "zone", "accept", "resolve"}


class DomainError(Exception):
    """A safe, user-facing rejection of a domain command."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.detail = message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _text(payload: dict, key: str, *, empty: bool = False, limit: int = 4000) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        qualifier = "a string" if empty else "a non-empty string"
        raise DomainError(422, f"{key} must be {qualifier} of at most {limit} characters.")
    return value.strip()


def _integer(payload: dict, key: str, low: int, high: int = 2_147_483_647) -> int:
    value = payload.get(key)
    if type(value) is not int or not low <= value <= high:
        raise DomainError(422, f"{key} must be an integer between {low} and {high}.")
    return value


def _boolean(payload: dict, key: str) -> bool:
    value = payload.get(key)
    if type(value) is not bool:
        raise DomainError(422, f"{key} must be true or false.")
    return value


def _strings(payload: dict, key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or len(value) > 30 or any(
        not isinstance(item, str) or not item.strip() or len(item) > 100 for item in value
    ):
        raise DomainError(422, f"{key} must be an array of at most 30 short, non-empty strings.")
    return list(dict.fromkeys(item.strip() for item in value))


class Store:
    """One SQLite database, safe for threaded HTTP handlers and multiple stores.

    ``BEGIN IMMEDIATE`` serializes writers, including different Store instances.
    Event IDs provide command idempotency, while notice expected_version provides
    optimistic concurrency. Reads use a transaction to return one consistent
    dashboard snapshot. A memory database is also supported for small experiments.
    """

    ACTIONS = {
        "submit_report", "acknowledge", "contact", "assign", "accept", "resolve",
        "callback", "revise_notice", "zone", "handoff_failed",
    }

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.path, timeout=10, isolation_level=None, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA busy_timeout = 10000")
        self._db.execute("PRAGMA journal_mode = WAL")
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, version INTEGER NOT NULL CHECK(version > 0));
            CREATE TABLE IF NOT EXISTS notice_versions (
                notice_id TEXT NOT NULL REFERENCES notices(id), version INTEGER NOT NULL,
                data TEXT NOT NULL, PRIMARY KEY(notice_id, version)
            );
            CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS responders (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS zones (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS operations (
                event_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                action TEXT NOT NULL, actor TEXT NOT NULL, payload TEXT NOT NULL,
                result TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY, event_id TEXT NOT NULL, case_id TEXT,
                kind TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL,
                actor TEXT NOT NULL, data TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_by_case ON events(case_id, created_at);
            CREATE TABLE IF NOT EXISTS acknowledgments (
                event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id),
                notice_id TEXT NOT NULL, notice_version INTEGER NOT NULL,
                data TEXT NOT NULL,
                FOREIGN KEY(notice_id, notice_version) REFERENCES notice_versions(notice_id, version)
            );
        """)
        with self._transaction(write=True):
            if not self._db.execute("SELECT 1 FROM metadata WHERE key = 'seeded'").fetchone():
                if not self._db.execute("SELECT 1 FROM cases LIMIT 1").fetchone():
                    self._seed()
                self._db.execute("INSERT INTO metadata(key, value) VALUES ('seeded', ?)", (_now(),))

    def close(self) -> None:
        with self._lock:
            self._db.close()

    @contextmanager
    def _transaction(self, *, write: bool = False):
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            try:
                yield
            except BaseException:
                self._db.rollback()
                raise
            else:
                self._db.commit()

    def _record(self, table: str, identifier: str, label: str) -> dict:
        row = self._db.execute(f"SELECT data FROM {table} WHERE id = ?", (identifier,)).fetchone()
        if not row:
            raise DomainError(404, f"{label} {identifier!r} was not found.")
        return json.loads(row["data"])

    def _save(self, table: str, record: dict) -> None:
        self._db.execute(
            f"INSERT INTO {table}(id, data) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (record["id"], _json(record)),
        )

    def _all(self, table: str) -> list[dict]:
        return [json.loads(row["data"]) for row in self._db.execute(f"SELECT data FROM {table}")]

    def _notice(self, identifier: str, version: int | None = None) -> dict:
        current = self._db.execute("SELECT version FROM notices WHERE id = ?", (identifier,)).fetchone()
        if not current:
            raise DomainError(404, f"Notice {identifier!r} was not found.")
        version = current["version"] if version is None else version
        row = self._db.execute(
            "SELECT data FROM notice_versions WHERE notice_id = ? AND version = ?", (identifier, version)
        ).fetchone()
        if not row:
            raise DomainError(409, "That notice version does not exist; refresh the current notice.")
        return json.loads(row["data"])

    def _case(self, payload: dict) -> dict:
        return self._record("cases", _text(payload, "case_id", limit=100), "Case")

    def _audit(self, event_id: str, actor: str, kind: str, detail: str,
               case_id: str | None = None, data: dict | None = None) -> None:
        self._db.execute(
            "INSERT INTO events(id,event_id,case_id,kind,detail,created_at,actor,data) VALUES (?,?,?,?,?,?,?,?)",
            ("evt-" + uuid.uuid4().hex, event_id, case_id, kind, detail, _now(), actor, _json(data or {})),
        )

    def _events(self, case_id: str | None = None) -> list[dict]:
        if case_id is None:
            rows = self._db.execute("SELECT * FROM events ORDER BY created_at DESC, rowid DESC LIMIT 100")
        else:
            rows = self._db.execute(
                "SELECT * FROM events WHERE case_id = ? ORDER BY created_at DESC, rowid DESC", (case_id,)
            )
        result = []
        for row in rows:
            item = dict(row)
            item["data"] = json.loads(item["data"])
            result.append(item)
        return result

    @staticmethod
    def _public(case: dict) -> dict:
        return {key: value for key, value in case.items() if not key.startswith("_")}

    def _responders(self, cases: list[dict]) -> list[dict]:
        responders = self._all("responders")
        for responder in responders:
            responder["active_count"] = sum(
                case["owner_id"] == responder["id"] and case["assistance_status"] in {"assigned", "accepted"}
                for case in cases
            )
        return sorted(responders, key=lambda value: value["id"])

    @staticmethod
    def _recommend(case: dict, responders: list[dict]) -> str | None:
        if case["assistance_status"] in {"assigned", "accepted"}:
            return case["owner_id"]
        if case["assistance_status"] == "completed":
            return None
        if not (case["needs_assistance"] or case["severity"] in {"P0", "P1"}
                or case["communication_status"] == "needs_clarification"
                or case["callback_stage"] in {"contact_review", "human_review"}):
            return None
        candidates = [r for r in responders if r["available"] and r["active_count"] < r["capacity"]
                      and r["id"] not in case.get("failed_responder_ids", [])
                      and (case["severity"] != "P0" or r["role"] == "professional")]
        if not candidates:
            return None
        needed = set(case["skills_needed"])

        def score(responder: dict) -> tuple:
            return (
                -len(needed.intersection(responder["skills"])),
                -(case["language"] in responder["languages"]),
                -(case["severity"] in {"P0", "P1"} and responder["role"] == "professional"),
                responder["active_count"] / responder["capacity"],
                responder["id"],
            )

        return min(candidates, key=score)["id"]

    def _state(self) -> dict:
        cases = self._all("cases")
        notices = [self._notice(row["id"]) for row in self._db.execute("SELECT id FROM notices ORDER BY id")]
        responders = self._responders(cases)
        for case in cases:
            case["recommended_responder_id"] = self._recommend(case, responders)
        cases.sort(key=lambda case: (PRIORITIES[case["severity"]], case["created_at"], case["id"]))
        current = {notice["id"]: notice for notice in notices}
        metrics = {
            "total_cases": len(cases),
            "current_confirmations": sum(
                case["communication_status"] == "confirmed"
                and case["notice_id"] in current
                and case["acknowledged_version"] == current[case["notice_id"]]["version"]
                and case.get("acknowledged_action_key") == current[case["notice_id"]]["action_key"]
                for case in cases
            ),
            "needs_human": sum(
                (case["severity"] in {"P0", "P1"} and case["assistance_status"] != "completed")
                or case["assistance_status"] in {"requested", "assigned"}
                or case["communication_status"] == "needs_clarification"
                or case["callback_stage"] in {"contact_review", "human_review"}
                for case in cases
            ),
            "unreached": sum(case["communication_status"] == "unreached" for case in cases),
            "pending_updates": sum(case["communication_status"] == "update_pending" for case in cases),
            "open_assistance": sum(case["assistance_status"] in ACTIVE_WORK for case in cases),
        }
        return {"notices": notices, "cases": [self._public(case) for case in cases],
                "responders": responders, "zones": sorted(self._all("zones"), key=lambda zone: zone["id"]),
                "events": self._events(), "metrics": metrics, "demo": True, "server_time": _now()}

    def state(self) -> dict:
        with self._transaction():
            return self._state()

    def get_case(self, case_id: str) -> dict:
        if not isinstance(case_id, str) or not case_id:
            raise DomainError(422, "case_id must be a non-empty string.")
        with self._transaction():
            case = self._record("cases", case_id, "Case")
            case["recommended_responder_id"] = self._recommend(case, self._responders(self._all("cases")))
            public = self._public(case)
            public["events"] = self._events(case_id)
            public["acknowledgment_history"] = [json.loads(row["data"]) for row in self._db.execute(
                "SELECT data FROM acknowledgments WHERE case_id = ? ORDER BY rowid", (case_id,)
            )]
            return public

    def apply(self, action: str, payload: dict, event_id: str, actor: str = "operator") -> dict:
        if not isinstance(action, str) or action not in self.ACTIONS:
            raise DomainError(404, "Unknown action.")
        if not isinstance(payload, dict):
            raise DomainError(422, "payload must be an object.")
        event_id = _text({"event_id": event_id}, "event_id", limit=200)
        actor = _text({"actor": actor}, "actor", limit=100)
        try:
            encoded = _json({"action": action, "payload": payload, "actor": actor})
        except (ValueError, TypeError):
            raise DomainError(422, "payload must contain valid JSON values.") from None
        fingerprint = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        with self._transaction(write=True):
            existing = self._db.execute("SELECT fingerprint,result FROM operations WHERE event_id = ?", (event_id,)).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise DomainError(409, "This event_id was already used for different content.")
                return json.loads(existing["result"])
            if action in OPERATOR_ACTIONS and actor != "operator":
                raise DomainError(403, "This action requires an operator.")
            result = getattr(self, "_do_" + action)(payload, event_id, actor)
            self._db.execute(
                "INSERT INTO operations(event_id,fingerprint,action,actor,payload,result,created_at) VALUES (?,?,?,?,?,?,?)",
                (event_id, fingerprint, action, actor, _json(payload), _json(result), _now()),
            )
            return result

    def _communication(self, case: dict) -> None:
        if case["notice_id"] is None:
            if case["contact_status"] in {"connected", "resumed"}:
                case["communication_status"] = "awaiting_confirmation"
            return
        notice = self._notice(case["notice_id"])
        if case.get("_last_ack_version") == notice["version"] and case.get("_last_ack_matches") is False:
            case["communication_status"] = "needs_clarification"
        elif (case["acknowledged_version"] == notice["version"]
              and case.get("acknowledged_action_key") == notice["action_key"]):
            case["communication_status"] = "confirmed"
            case["_pending_notice_update"] = False
        elif case.get("_pending_notice_update") or (
            case["acknowledged_version"] is not None and case["acknowledged_version"] < notice["version"]
        ):
            case["communication_status"] = "update_pending"
        elif case["contact_status"] in {"connected", "resumed"}:
            case["communication_status"] = "awaiting_confirmation"
        elif case["communication_status"] not in {"awaiting_confirmation", "needs_clarification"}:
            case["communication_status"] = "unreached"

    @staticmethod
    def _request_help(case: dict, details: str | None = None) -> None:
        case["needs_assistance"] = True
        if details is not None:
            case["assistance_details"] = details
        if case["assistance_status"] in {"none", "completed"}:
            case["assistance_status"] = "requested"
            case["owner_id"] = None
            case["resolved_at"] = None
            case["resolution_note"] = None
            case["failed_responder_ids"] = []

    def _guard_priority(self, case: dict, old_severity: str | None = None) -> None:
        if case["severity"] in {"P0", "P1"}:
            if case["assistance_status"] == "none" or (
                case["assistance_status"] == "completed" and old_severity != case["severity"]
            ):
                case["assistance_status"] = "requested"
                case["owner_id"] = None
                case["resolved_at"] = None
                case["resolution_note"] = None
        if case["severity"] == "P0":
            case["callback_due_at"] = None
            if case["assistance_status"] == "completed":
                case["callback_stage"] = "none"
            elif case["assistance_status"] != "accepted" or case["callback_stage"] != "none":
                case["callback_stage"] = "human_review"
            if case["owner_id"]:
                owner = self._record("responders", case["owner_id"], "Responder")
                if owner["role"] != "professional":
                    case["owner_id"] = None
                    case["assistance_status"] = "requested"
                    case["callback_stage"] = "human_review"

    def _do_submit_report(self, payload: dict, event_id: str, actor: str) -> dict:
        supplied_id = payload.get("case_id")
        existing = supplied_id is not None
        if existing:
            case = self._case(payload)
            old_severity = case["severity"]
            if "resident_id" in payload and payload["resident_id"] != case["resident_id"]:
                raise DomainError(409, "An existing case cannot be moved to a different resident.")
        else:
            case = self._new_case("case-" + uuid.uuid4().hex[:12], _now())
            old_severity = None
        required = {"resident_id", "resident_name", "language", "zone", "category", "severity", "summary"}
        if not existing:
            missing = sorted(required.difference(payload))
            if missing:
                raise DomainError(422, "Missing report fields: " + ", ".join(missing) + ".")
        for key in ("resident_id", "resident_name", "zone", "category", "summary"):
            if key in payload:
                case[key] = _text(payload, key, limit=4000 if key == "summary" else 200)
        if "language" in payload:
            language = _text(payload, "language", limit=10)
            if language not in {"en", "es"}:
                raise DomainError(422, "The demo supports language en or es.")
            case["language"] = language
        if "severity" in payload:
            severity = _text(payload, "severity", limit=2)
            if severity not in PRIORITIES:
                raise DomainError(422, "severity must be P0, P1, P2, or P3.")
            case["severity"] = severity if old_severity is None else min((old_severity, severity), key=PRIORITIES.get)
        if "skills_needed" in payload:
            case["skills_needed"] = _strings(payload, "skills_needed")
        if "notice_id" in payload:
            notice_id = payload["notice_id"]
            if notice_id is not None:
                notice_id = _text(payload, "notice_id", limit=100)
                self._notice(notice_id)
            if notice_id != case["notice_id"]:
                case["notice_id"] = notice_id
                case["acknowledged_version"] = None
                case["acknowledged_action_key"] = None
                case["readback_text"] = None
                case["_last_ack_version"] = None
                case["_last_ack_matches"] = None
                case["_pending_notice_update"] = bool(existing and notice_id)
                case["communication_status"] = "update_pending" if case["_pending_notice_update"] else "unreached"
        if "assistance_details" in payload:
            case["assistance_details"] = _text(payload, "assistance_details", empty=True)
        if "needs_assistance" in payload and _boolean(payload, "needs_assistance"):
            self._request_help(case, case["assistance_details"])
        # Preserve upstream data without interpreting it or running a classifier.
        for key in ("location", "hazard_here_now", "people_at_risk", "vulnerability", "keyword_hits", "confidence", "triage_source"):
            if key not in payload:
                continue
            if key in {"vulnerability", "keyword_hits"}:
                case[key] = _strings(payload, key)
            elif key == "hazard_here_now":
                case[key] = _boolean(payload, key)
            elif key == "people_at_risk":
                case[key] = _integer(payload, key, 0, 100000)
            elif key == "confidence":
                value = payload[key]
                if type(value) not in {int, float} or not 0 <= value <= 1:
                    raise DomainError(422, "confidence must be a number from 0 to 1.")
                case[key] = value
            else:
                case[key] = _text(payload, key, empty=True, limit=500)
        # A new imported zone begins at normal; only an operator changes its level.
        if not self._db.execute("SELECT 1 FROM zones WHERE id = ?", (case["zone"],)).fetchone():
            self._save("zones", {"id": case["zone"], "level": "normal", "changed_by": "Report import",
                                 "updated_at": _now(), "reason": "New zone registered; no incident declaration."})
            self._audit(event_id, actor, "zone_registered", "Registered a report zone at the normal baseline.",
                        data={"zone_id": case["zone"], "level": "normal"})
        self._guard_priority(case, old_severity)
        self._communication(case)
        case["updated_at"] = _now()
        self._save("cases", case)
        detail = "Continued a saved report." if existing else "Saved a new upstream-classified report."
        if old_severity and old_severity != case["severity"]:
            detail += f" Priority escalated from {old_severity} to {case['severity']}."
        elif old_severity and "severity" in payload and payload["severity"] != case["severity"]:
            detail += f" Preserved the existing {case['severity']} priority."
        self._audit(event_id, actor, "submit_report", detail, case["id"],
                    {"severity": case["severity"], "assistance_status": case["assistance_status"]})
        return {"case_id": case["id"], "created": not existing, "severity": case["severity"],
                "communication_status": case["communication_status"], "assistance_status": case["assistance_status"]}

    def _do_acknowledge(self, payload: dict, event_id: str, actor: str) -> dict:
        case = self._case(payload)
        if case["notice_id"] is None:
            raise DomainError(409, "This case has no notice to acknowledge.")
        version = _integer(payload, "notice_version", 1)
        key = _text(payload, "action_key", limit=200)
        readback = _text(payload, "readback_text")
        historical = self._notice(case["notice_id"], version)
        current = self._notice(case["notice_id"])
        matched = key == historical["action_key"]
        ignored = version < (case.get("_last_ack_version") or 0)
        if not ignored:
            case["_last_ack_version"] = version
            case["_last_ack_matches"] = matched
            case["readback_text"] = readback
            if matched and version >= (case["acknowledged_version"] or 0):
                case["acknowledged_version"] = version
                case["acknowledged_action_key"] = key
            if version < current["version"]:
                case["_pending_notice_update"] = True
        if "needs_assistance" in payload:
            wants_help = _boolean(payload, "needs_assistance")
            details = _text(payload, "assistance_details", empty=True) if "assistance_details" in payload else None
            if wants_help:
                self._request_help(case, details)
        elif "assistance_details" in payload:
            _text(payload, "assistance_details", empty=True)
        self._communication(case)
        self._guard_priority(case, case["severity"])
        case["updated_at"] = _now()
        self._save("cases", case)
        record = {"event_id": event_id, "case_id": case["id"], "notice_id": case["notice_id"],
                  "notice_version": version, "action_key": key, "readback_text": readback,
                  "matched": matched, "stale": version != current["version"], "ignored": ignored,
                  "created_at": _now(), "actor": actor}
        self._db.execute(
            "INSERT INTO acknowledgments(event_id,case_id,notice_id,notice_version,data) VALUES (?,?,?,?,?)",
            (event_id, case["id"], case["notice_id"], version, _json(record)),
        )
        detail = f"Recorded read-back for notice v{version}: "
        detail += "older event retained in history." if ignored else (
            "clarification required." if not matched else (
                "an updated notice still needs confirmation." if record["stale"] else "current action confirmed."
            )
        )
        self._audit(event_id, actor, "acknowledge", detail, case["id"], record)
        return {"case_id": case["id"], "acknowledged_version": case["acknowledged_version"],
                "current_version": current["version"], "matched": matched, "stale": record["stale"],
                "ignored": ignored, "communication_status": case["communication_status"],
                "assistance_status": case["assistance_status"]}

    @staticmethod
    def _failure_stage(failures: int) -> str:
        return "retry_pending" if failures <= 1 else "contact_review" if failures == 2 else "human_review"

    def _do_contact(self, payload: dict, event_id: str, actor: str) -> dict:
        case = self._case(payload)
        outcome = _text(payload, "outcome", limit=30)
        if outcome not in CONTACT_OUTCOMES:
            raise DomainError(422, "outcome must be connected, dropped, no_answer, resumed, or ended.")
        case["contact_status"] = outcome
        if outcome in {"dropped", "no_answer"}:
            case["contact_failures"] += 1
            proposed = self._failure_stage(case["contact_failures"])
            case["callback_stage"] = max((case["callback_stage"], proposed), key=CALLBACK_RANK.get)
        elif outcome in {"connected", "resumed"}:
            case["callback_stage"] = "none"
            case["callback_due_at"] = None
        self._communication(case)
        self._guard_priority(case, case["severity"])
        case["updated_at"] = _now()
        self._save("cases", case)
        self._audit(event_id, actor, "contact", f"Contact {outcome.replace('_', ' ')}; no acknowledgment or completion inferred.",
                    case["id"], {"outcome": outcome, "contact_failures": case["contact_failures"],
                                 "callback_stage": case["callback_stage"]})
        return {"case_id": case["id"], "contact_status": outcome, "contact_failures": case["contact_failures"],
                "callback_stage": case["callback_stage"], "communication_status": case["communication_status"]}

    def _do_assign(self, payload: dict, event_id: str, actor: str) -> dict:
        case = self._case(payload)
        responder_id = _text(payload, "responder_id", limit=100)
        responders = self._responders(self._all("cases"))
        responder = next((item for item in responders if item["id"] == responder_id), None)
        if responder is None:
            raise DomainError(404, "Responder was not found.")
        if case["assistance_status"] == "completed":
            raise DomainError(409, "Completed work must be reopened by a new assistance report before assignment.")
        if case["severity"] == "P0" and responder["role"] != "professional":
            raise DomainError(409, "P0 cases require a professional; volunteer assignment is not allowed.")
        already_owned = case["owner_id"] == responder_id and case["assistance_status"] in {"assigned", "accepted"}
        if not responder["available"] or (responder["active_count"] >= responder["capacity"] and not already_owned):
            raise DomainError(409, "This responder is unavailable or at capacity.")
        if not already_owned:
            case["owner_id"] = responder_id
            case["assistance_status"] = "assigned"
        case["updated_at"] = _now()
        self._save("cases", case)
        self._audit(event_id, actor, "assign", f"Proposed a handoff to {responder['name']}; acceptance is a separate action.",
                    case["id"], {"responder_id": responder_id, "assistance_status": case["assistance_status"]})
        return {"case_id": case["id"], "owner_id": responder_id, "assistance_status": case["assistance_status"]}

    def _do_accept(self, payload: dict, event_id: str, actor: str) -> dict:
        case = self._case(payload)
        responder_id = _text(payload, "responder_id", limit=100)
        if case["owner_id"] != responder_id or case["assistance_status"] not in {"assigned", "accepted"}:
            raise DomainError(409, "Only the currently assigned responder can have this handoff accepted.")
        responder = self._record("responders", responder_id, "Responder")
        if case["severity"] == "P0" and responder["role"] != "professional":
            raise DomainError(409, "A P0 handoff must be accepted by a professional.")
        case["assistance_status"] = "accepted"
        case["callback_stage"] = "none"
        case["callback_due_at"] = None
        case["updated_at"] = _now()
        self._save("cases", case)
        self._audit(event_id, actor, "accept", f"Operator recorded {responder['name']}'s acceptance; work remains incomplete.",
                    case["id"], {"responder_id": responder_id})
        return {"case_id": case["id"], "owner_id": responder_id, "assistance_status": "accepted"}

    def _do_handoff_failed(self, payload: dict, event_id: str, actor: str) -> dict:
        case = self._case(payload)
        responder_id = _text(payload, "responder_id", limit=100)
        reason = _text(payload, "reason", limit=1000)
        if case["owner_id"] != responder_id or case["assistance_status"] != "assigned":
            raise DomainError(409, "Only an unaccepted handoff to the currently assigned responder can fail.")
        case["owner_id"] = None
        case["assistance_status"] = "requested"
        case["handoff_failures"] = case.get("handoff_failures", 0) + 1
        case["failed_responder_ids"] = list(dict.fromkeys(case.get("failed_responder_ids", []) + [responder_id]))
        case["updated_at"] = _now()
        self._guard_priority(case, case["severity"])
        self._save("cases", case)
        recommended = self._recommend(case, self._responders(self._all("cases")))
        self._audit(event_id, actor, "handoff_failed", "Human handoff not accepted: " + reason,
                    case["id"], {"responder_id": responder_id, "recommended_responder_id": recommended,
                                 "handoff_failures": case["handoff_failures"]})
        return {"case_id": case["id"], "owner_id": None, "assistance_status": "requested",
                "handoff_failures": case["handoff_failures"], "recommended_responder_id": recommended}

    def _do_resolve(self, payload: dict, event_id: str, actor: str) -> dict:
        case = self._case(payload)
        note = _text(payload, "note", limit=4000)
        needs_review = case["needs_assistance"] or case["severity"] in {"P0", "P1"} or case["assistance_status"] in ACTIVE_WORK
        if case["assistance_status"] == "completed":
            raise DomainError(409, "This assistance work has already been completed.")
        if needs_review and (case["assistance_status"] != "accepted" or not case["owner_id"]):
            raise DomainError(409, "An accepted human handoff is required before completing this work.")
        if case["severity"] == "P0" and self._record("responders", case["owner_id"], "Responder")["role"] != "professional":
            raise DomainError(409, "P0 completion requires an accepted professional handoff.")
        if needs_review:
            case["assistance_status"] = "completed"
        case["resolved_at"] = _now()
        case["resolution_note"] = note
        case["callback_stage"] = "none"
        case["callback_due_at"] = None
        case["updated_at"] = _now()
        self._save("cases", case)
        self._audit(event_id, actor, "resolve", "Operator completion note: " + note, case["id"],
                    {"assistance_status": case["assistance_status"], "owner_id": case["owner_id"]})
        return {"case_id": case["id"], "assistance_status": case["assistance_status"], "resolved_at": case["resolved_at"]}

    def _do_callback(self, payload: dict, event_id: str, actor: str) -> dict:
        case = self._case(payload)
        minutes = _integer(payload, "minutes", 1, 60)
        reason = _text(payload, "reason", limit=1000)
        if case["severity"] == "P0":
            raise DomainError(409, "P0 cannot be deferred into a timed callback; professional review is required now.")
        proposed = self._failure_stage(case["contact_failures"])
        case["callback_stage"] = max((case["callback_stage"], proposed), key=CALLBACK_RANK.get)
        case["callback_due_at"] = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        case["callback_reason"] = reason
        case["updated_at"] = _now()
        self._save("cases", case)
        self._audit(event_id, actor, "callback", f"Recorded a follow-up task due in {minutes} minutes; no call or message sent.",
                    case["id"], {"reason": reason, "callback_stage": case["callback_stage"], "callback_due_at": case["callback_due_at"]})
        return {"case_id": case["id"], "callback_stage": case["callback_stage"], "callback_due_at": case["callback_due_at"], "sent": False}

    def _do_revise_notice(self, payload: dict, event_id: str, actor: str) -> dict:
        notice_id = _text(payload, "notice_id", limit=100)
        expected = _integer(payload, "expected_version", 1)
        previous = self._notice(notice_id)
        if expected != previous["version"]:
            raise DomainError(409, "The notice changed since it was loaded; refresh before publishing a revision.")
        updated = dict(previous)
        for key in ("body_en", "body_es", "action_key", "action_label_en", "action_label_es", "source_label", "approved_by"):
            updated[key] = _text(payload, key, limit=4000 if key.startswith("body_") else 200)
        updated["version"] += 1
        updated["updated_at"] = _now()
        self._db.execute("UPDATE notices SET version = ? WHERE id = ?", (updated["version"], notice_id))
        self._db.execute("INSERT INTO notice_versions(notice_id,version,data) VALUES (?,?,?)",
                         (notice_id, updated["version"], _json(updated)))
        affected = []
        for case in self._all("cases"):
            if case["notice_id"] != notice_id:
                continue
            case["_pending_notice_update"] = True
            case["communication_status"] = "update_pending"
            case["updated_at"] = _now()
            self._save("cases", case)
            affected.append(case["id"])
            self._audit(event_id, actor, "notice_update_pending", f"Notice v{updated['version']} needs a new read-back; prior confirmation retained in history.",
                        case["id"], {"notice_id": notice_id, "notice_version": updated["version"]})
        self._audit(event_id, actor, "revise_notice", f"Published operator-approved notice v{updated['version']}; {len(affected)} cases need the update.",
                    data={"notice_id": notice_id, "notice_version": updated["version"], "affected_case_ids": affected})
        return {"notice_id": notice_id, "version": updated["version"], "affected_case_ids": affected, "messages_sent": 0}

    def _do_zone(self, payload: dict, event_id: str, actor: str) -> dict:
        zone_id = _text(payload, "zone_id", limit=200)
        zone = self._record("zones", zone_id, "Zone")
        level = _text(payload, "level", limit=30)
        if level not in ZONE_LEVELS:
            raise DomainError(422, "level must be normal, watch, ask, crisis, or stand_down.")
        reason = _text(payload, "reason", limit=1000)
        previous = zone["level"]
        zone.update(level=level, changed_by=actor, updated_at=_now(), reason=reason)
        self._save("zones", zone)
        self._audit(event_id, actor, "zone", f"Operator changed {zone_id} from {previous} to {level}: {reason}",
                    data={"zone_id": zone_id, "previous_level": previous, "level": level})
        return {"zone_id": zone_id, "level": level}

    @staticmethod
    def _new_case(identifier: str, created_at: str) -> dict:
        return {"id": identifier, "resident_id": "", "resident_name": "", "language": "en", "zone": "",
                "category": "other", "severity": "P3", "skills_needed": [], "summary": "", "notice_id": None,
                "acknowledged_version": None, "acknowledged_action_key": None, "readback_text": None,
                "communication_status": "unreached", "contact_status": "not_contacted", "needs_assistance": False,
                "assistance_details": "", "assistance_status": "none", "owner_id": None,
                "recommended_responder_id": None, "callback_stage": "none", "callback_due_at": None,
                "callback_reason": None, "contact_failures": 0, "handoff_failures": 0, "failed_responder_ids": [],
                "resolved_at": None, "resolution_note": None, "created_at": created_at, "updated_at": created_at,
                "_last_ack_version": None, "_last_ack_matches": None, "_pending_notice_update": False}

    def _seed(self) -> None:
        now = datetime.now(timezone.utc)
        stamp = (now - timedelta(minutes=45)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        notice = {"id": "notice-pickup", "title": "Community pickup", "version": 1,
                  "body_en": "Demo pickup is at the north entrance of the community hub. Ask the coordinator if you need help reaching it.",
                  "body_es": "La recogida de demostración está en la entrada norte del centro comunitario. Pida ayuda al coordinador si la necesita para llegar.",
                  "action_key": "north_entrance", "action_label_en": "North entrance", "action_label_es": "Entrada norte",
                  "zone": "Campus West", "source_label": "Demo coordinator", "approved_by": "Demo supervisor", "updated_at": stamp}
        self._db.execute("INSERT INTO notices(id,version) VALUES (?,?)", (notice["id"], 1))
        self._db.execute("INSERT INTO notice_versions(notice_id,version,data) VALUES (?,?,?)", (notice["id"], 1, _json(notice)))
        for identifier, level in (("Campus West", "watch"), ("Campus East", "normal"), ("University Village", "normal")):
            self._save("zones", {"id": identifier, "level": level, "changed_by": "Demo supervisor",
                                 "updated_at": stamp, "reason": "Synthetic exercise baseline; not a live incident declaration."})
        for responder in (
            {"id": "responder-01", "name": "Demo mobility coordinator", "languages": ["en", "es"],
             "skills": ["mobility", "logistics", "evac_logistics", "safety"], "role": "professional", "available": True, "capacity": 3},
            {"id": "responder-02", "name": "Demo response lead", "languages": ["en"],
             "skills": ["medical", "medical_review", "safety", "power"], "role": "professional", "available": True, "capacity": 2},
            {"id": "responder-03", "name": "Demo community volunteer", "languages": ["en", "es"],
             "skills": ["logistics", "escort"], "role": "volunteer", "available": True, "capacity": 2},
        ):
            self._save("responders", responder)
        scenarios = [
            dict(language="es", severity="P2", category="logistics", skills_needed=["mobility"],
                 summary="Needs help reaching the community pickup with a mobility aid.", needs_assistance=True,
                 assistance_details="Requested an accessible escort to pickup.", assistance_status="requested"),
            dict(language="en", severity="P0", category="medical", skills_needed=["medical"], zone="Campus East", notice_id=None,
                 summary="Upstream DIZA intake marked this synthetic report P0; immediate professional review is pending.",
                 needs_assistance=True, assistance_details="Urgent professional review; no automated diagnosis or dispatch.",
                 assistance_status="requested", contact_status="connected", communication_status="awaiting_confirmation", callback_stage="human_review"),
            dict(language="en", severity="P1", category="power", skills_needed=["safety", "power"], zone="Campus East", notice_id=None,
                 summary="Upstream P1 report about a building power hazard; follow-up has not reached the resident.",
                 needs_assistance=True, assistance_details="Professional review requested for the upstream hazard report.",
                 assistance_status="requested", contact_status="no_answer", contact_failures=3, callback_stage="human_review"),
            dict(language="es", severity="P2", category="logistics", skills_needed=["logistics"],
                 summary="Understood the pickup location; volunteer handoff still needs acceptance.", needs_assistance=True,
                 assistance_details="Requested help carrying supplies.", assistance_status="assigned", owner_id="responder-03",
                 contact_status="connected", communication_status="confirmed", acknowledged_version=1, acknowledged_action_key="north_entrance",
                 readback_text="Iré a la entrada norte."),
            dict(language="en", severity="P3", category="info", summary="Confirmed the north entrance and can reach pickup independently.",
                 contact_status="connected", communication_status="confirmed", acknowledged_version=1, acknowledged_action_key="north_entrance",
                 readback_text="I will use the north entrance."),
            dict(language="es", severity="P3", category="logistics", summary="Connection ended before the location read-back; saved report is ready to resume.",
                 contact_status="dropped", communication_status="awaiting_confirmation", contact_failures=1, callback_stage="retry_pending",
                 callback_due_at=(now + timedelta(minutes=5)).isoformat(timespec="milliseconds").replace("+00:00", "Z")),
            dict(language="en", severity="P2", category="logistics", skills_needed=["mobility"],
                 summary="Pickup instructions confirmed; coordinator accepted the escort request, which is still incomplete.",
                 needs_assistance=True, assistance_details="Accessible escort accepted; awaiting operator confirmation of completion.",
                 assistance_status="accepted", owner_id="responder-01", contact_status="connected", communication_status="confirmed",
                 acknowledged_version=1, acknowledged_action_key="north_entrance", readback_text="The north entrance is my pickup point."),
            dict(language="en", severity="P3", category="info", summary="Two contact attempts received no answer; an operator should review the next attempt.",
                 zone="University Village", contact_status="no_answer", contact_failures=2, callback_stage="contact_review"),
        ]
        for index, scenario in enumerate(scenarios, 1):
            created = (now - timedelta(minutes=40 - index * 3)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            case = self._new_case(f"case-{index:03d}", created)
            case.update(resident_id=f"demo-{index:03d}", resident_name=f"Demo resident {index:02d}", zone="Campus West", notice_id="notice-pickup")
            case.update(scenario)
            if case["acknowledged_version"]:
                case["_last_ack_version"] = 1
                case["_last_ack_matches"] = True
            self._save("cases", case)
            self._audit(f"seed-{index}", "demo_seed", "demo_seed", "Synthetic starting scenario: " + case["summary"], case["id"])
            if case["acknowledged_version"]:
                ack = {"event_id": f"seed-ack-{index}", "case_id": case["id"], "notice_id": "notice-pickup", "notice_version": 1,
                       "action_key": "north_entrance", "readback_text": case["readback_text"], "matched": True, "stale": False,
                       "ignored": False, "created_at": created, "actor": "demo_seed"}
                self._db.execute("INSERT INTO acknowledgments(event_id,case_id,notice_id,notice_version,data) VALUES (?,?,?,?,?)",
                                 (ack["event_id"], case["id"], "notice-pickup", 1, _json(ack)))
