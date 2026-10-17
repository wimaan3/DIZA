"""A bounded Retell adapter for DIZA's proposed tool names.

This module never dials a telephone, sends an SMS, publishes a notice or accepts
a handoff. Authentication of public callbacks belongs to the HTTP boundary.
"""

from hashlib import sha256
from contextlib import contextmanager
import json
import sqlite3
from pathlib import Path
from threading import RLock

from .engine import DomainError, Store


FUNCTIONS = frozenset({"submit_report", "lookup_guidance", "save_checkin", "check_status", "route_to_human", "schedule_callback"})


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class CallBindings:
    """Keep calls and normalized commands durable across restarts and retries."""

    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS relayla_call_bindings (call_id TEXT PRIMARY KEY, case_id TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS relayla_provider_plans (event_id TEXT PRIMARY KEY, source_hash TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS relayla_call_lifecycle (call_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, phase TEXT NOT NULL, start_timestamp INTEGER)")
            db.execute("CREATE TABLE IF NOT EXISTS relayla_latest_call (case_id TEXT PRIMARY KEY, call_id TEXT NOT NULL)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def bind(self, call_id: str, case_id: str) -> None:
        with self.connect() as db:
            existing = db.execute("SELECT case_id FROM relayla_call_bindings WHERE call_id=?", (call_id,)).fetchone()
            if existing and existing[0] != case_id:
                raise DomainError(409, "This call is already bound to another case.")
            db.execute("INSERT OR IGNORE INTO relayla_call_bindings VALUES (?, ?)", (call_id, case_id))

    def lookup(self, call_id: str) -> str | None:
        with self.connect() as db:
            row = db.execute("SELECT case_id FROM relayla_call_bindings WHERE call_id=?", (call_id,)).fetchone()
            return row[0] if row else None

    def plan(self, event_id: str, source: dict, action: str, payload: dict) -> tuple[str, dict]:
        digest = sha256(canonical(source).encode()).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT source_hash, action, payload FROM relayla_provider_plans WHERE event_id=?", (event_id,)).fetchone()
            if row:
                if row[0] != digest:
                    raise DomainError(409, "The provider reused an event ID with different content.")
                return row[1], json.loads(row[2])
            db.execute("INSERT INTO relayla_provider_plans VALUES (?, ?, ?, ?)", (event_id, digest, action, canonical(payload)))
            return action, payload

    def lifecycle(self, call_id: str, case_id: str) -> tuple[tuple | None, tuple | None]:
        with self.connect() as db:
            current = db.execute("SELECT phase, start_timestamp FROM relayla_call_lifecycle WHERE call_id=?", (call_id,)).fetchone()
            latest = db.execute("SELECT life.call_id, life.start_timestamp FROM relayla_latest_call AS latest JOIN relayla_call_lifecycle AS life ON life.call_id=latest.call_id WHERE latest.case_id=?", (case_id,)).fetchone()
            return current, latest

    def record_lifecycle(self, call_id: str, case_id: str, phase: str, start_timestamp: int | None, *, latest: bool) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO relayla_call_lifecycle VALUES (?, ?, ?, ?) ON CONFLICT(call_id) DO UPDATE SET phase=excluded.phase, start_timestamp=COALESCE(excluded.start_timestamp, relayla_call_lifecycle.start_timestamp)", (call_id, case_id, phase, start_timestamp))
            if latest:
                db.execute("INSERT INTO relayla_latest_call VALUES (?, ?) ON CONFLICT(case_id) DO UPDATE SET call_id=excluded.call_id", (case_id, call_id))


class RetellAdapter:
    def __init__(self, store: Store, bindings: CallBindings):
        self.store = store
        self.bindings = bindings
        # The standalone app deliberately runs one worker. Serialize lifecycle
        # checks and domain writes so simultaneous callbacks cannot reorder them.
        self.webhook_lock = RLock()

    def _case_id(self, call: dict, args: dict, *, required: bool = True) -> str | None:
        call_id = str(call.get("call_id", ""))
        if not call_id or len(call_id) > 200:
            raise DomainError(422, "A valid provider call_id is required.")
        bound = self.bindings.lookup(call_id)
        metadata = call.get("metadata") if isinstance(call.get("metadata"), dict) else {}
        supplied = metadata.get("relayla_case_id")
        if bound and supplied and bound != supplied:
            raise DomainError(403, "Call metadata does not match its existing case binding.")
        if not bound and supplied:
            self.store.get_case(str(supplied))
            self.bindings.bind(call_id, str(supplied))
            bound = str(supplied)
        if args.get("case_id") and args["case_id"] != bound:
            raise DomainError(403, "A voice tool can only access the case bound to this call.")
        if not bound and required:
            raise DomainError(409, "Save an intake report before requesting case-specific actions.")
        return bound

    def _apply(self, function: str, call: dict, args: dict, action: str, payload: dict) -> dict:
        # Ignore changing transcript/timing fields when recognizing retries.
        source = {"call_id": call["call_id"], "function": function, "args": args}
        suffix = str(args.get("event_id") or sha256(canonical(args).encode()).hexdigest())
        event_id = "retell:" + sha256(f"{call['call_id']}:{function}:{suffix}".encode()).hexdigest()
        normalized_action, normalized_payload = self.bindings.plan(event_id, source, action, payload)
        return self.store.apply(normalized_action, normalized_payload, event_id, actor="retell")

    def guidance(self, case_id: str, language: str = "en") -> dict:
        case = self.store.get_case(case_id)
        notice = next((n for n in self.store.state()["notices"] if n["id"] == case.get("notice_id")), None)
        if not notice:
            return {"available": False, "message": "No approved instruction is attached to this case; request operator review."}
        lang = "es" if language.startswith("es") else "en"
        return {
            "available": True, "notice_id": notice["id"], "version": notice["version"],
            "text": notice[f"body_{lang}"], "action_key": notice["action_key"],
            "action_label": notice[f"action_label_{lang}"], "source_label": notice["source_label"],
            "approved_by": notice["approved_by"], "updated_at": notice["updated_at"],
            "instruction": "Read this approved version; preserve its version when saving the caller's response.",
        }

    def dispatch(self, name: str, envelope: dict) -> dict:
        if name not in FUNCTIONS:
            raise DomainError(404, "This function is not exposed to the voice agent.")
        call, args = envelope.get("call"), envelope.get("args", {})
        if not isinstance(call, dict) or not isinstance(args, dict):
            raise DomainError(422, "Expected a Retell call envelope with an args object.")
        if envelope.get("name") and envelope["name"] != name:
            raise DomainError(422, "Function name and route must agree.")
        case_id = self._case_id(call, args, required=name != "submit_report")

        if name == "submit_report":
            # DIZA owns classification. Missing severity means human review, P2.
            allowed = ("resident_name", "language", "zone", "category", "severity", "skills_needed", "summary", "notice_id", "needs_assistance", "assistance_details", "vulnerability", "people_at_risk", "confidence", "hazard_here_now", "keyword_hits", "location", "triage_source")
            payload = {key: args[key] for key in allowed if key in args}
            if case_id:
                current = self.store.get_case(case_id)
                if "notice_id" in payload and payload["notice_id"] != current.get("notice_id"):
                    raise DomainError(403, "Changing this case's approved notice requires an operator.")
                payload["case_id"] = case_id
            else:
                metadata = call.get("metadata") if isinstance(call.get("metadata"), dict) else {}
                payload["resident_id"] = str(metadata.get("resident_id") or "call-" + sha256(call["call_id"].encode()).hexdigest()[:16])
                payload.setdefault("resident_name", "Voice intake")
                payload.setdefault("language", "en")
                payload.setdefault("zone", "Unconfirmed")
                payload.setdefault("category", "other")
                payload.setdefault("severity", "P2")
                payload.setdefault("skills_needed", [])
                payload.setdefault("summary", "Voice intake awaiting operator review")
                payload.setdefault("needs_assistance", True)
                payload.setdefault("assistance_details", "Operator review requested")
            result = self._apply(name, call, args, "submit_report", payload)
            new_id = result.get("case_id") or result.get("id")
            if not new_id and isinstance(result.get("case"), dict):
                new_id = result["case"]["id"]
            if not new_id:
                raise DomainError(500, "The intake store did not return a case identifier.")
            self.bindings.bind(call["call_id"], new_id)
            return {"saved": True, "case_id": new_id, "cluster_match": None, "message": "Request recorded; no responder has been dispatched.", "case": self.store.get_case(new_id)}

        if name == "lookup_guidance":
            return self.guidance(case_id, str(args.get("language", "en")))
        if name == "check_status":
            case = self.store.get_case(case_id)
            return {"case_id": case_id, "communication_status": case["communication_status"], "acknowledged_version": case["acknowledged_version"], "assistance_status": case["assistance_status"], "callback_stage": case["callback_stage"], "message": "A request or callback plan is not proof that help is on the way."}
        if name == "save_checkin":
            payload = {"case_id": case_id, **{key: args[key] for key in ("notice_version", "action_key", "readback_text", "needs_assistance", "assistance_details") if key in args}}
            result = self._apply(name, call, args, "acknowledge", payload)
            current = self.store.get_case(case_id)
            return {"saved": True, "result": result, "communication_status": current["communication_status"], "guidance": self.guidance(case_id, current["language"])}
        if name == "route_to_human":
            case = self.store.get_case(case_id)
            reason = str(args.get("reason") or "Human follow-up requested")
            existing = case.get("assistance_details", "")
            details = existing if reason in existing else "\n".join(filter(None, (existing, "Handoff request: " + reason)))
            payload = {"case_id": case_id, "needs_assistance": True, "assistance_details": details}
            self._apply(name, call, args, "submit_report", payload)
            case = self.store.get_case(case_id)
            return {"case_id": case_id, "handoff_status": case["assistance_status"], "recommended_responder_id": case.get("recommended_responder_id"), "brief": case["summary"], "requires_professional": case["severity"] == "P0", "oncall_number": None, "message": "The request and its current handoff status are recorded. This integration does not place a transfer or promise an answer."}
        result = self._apply(name, call, args, "callback", {"case_id": case_id, "minutes": args.get("minutes", 5), "reason": str(args.get("reason") or "Caller requested follow-up")})
        case = self.store.get_case(case_id)
        return {"planned": True, "result": result, "callback_stage": case["callback_stage"], "callback_due_at": case.get("callback_due_at"), "message": "Follow-up is pending human action; no callback time is guaranteed and no call was placed."}

    def webhook(self, envelope: dict) -> dict:
        with self.webhook_lock:
            return self._webhook(envelope)

    def _webhook(self, envelope: dict) -> dict:
        event, call = envelope.get("event"), envelope.get("call")
        if not isinstance(call, dict):
            raise DomainError(422, "Webhook requires a call object.")
        case_id = self._case_id(call, {}, required=False)
        if not case_id:
            return {"received": True, "applied": False, "reason": "Call has no RelayLA intake binding yet."}
        if event == "call_started":
            outcome = "connected"
        elif event == "call_ended":
            reason = str(call.get("disconnection_reason", ""))
            if reason in {"dial_no_answer", "dial_busy", "voicemail_reached", "dial_failed", "user_declined"}:
                outcome = "no_answer"
            elif reason.startswith("error_") or reason in {"telephony_provider_unavailable", "sip_routing_error"}:
                outcome = "dropped"
            else:
                outcome = "ended"
        else:
            return {"received": True, "applied": False, "reason": "Event does not change confirmation or handoff state."}
        call_id = str(call["call_id"])
        current, latest = self.bindings.lifecycle(call_id, case_id)
        supplied_timestamp = call.get("start_timestamp")
        start_timestamp = supplied_timestamp if type(supplied_timestamp) is int and supplied_timestamp >= 0 else (current[1] if current else None)
        if current and current[0] in {"ended", "superseded"}:
            return {"received": True, "applied": False, "reason": "This call is already terminal or superseded; its contact state is not replayed."}
        if latest and latest[0] != call_id:
            known_older = current is not None
            timestamp_older = start_timestamp is not None and latest[1] is not None and start_timestamp <= latest[1]
            ambiguous_end = event == "call_ended" and (start_timestamp is None or latest[1] is None)
            if known_older or timestamp_older or ambiguous_end:
                self.bindings.record_lifecycle(call_id, case_id, "superseded", start_timestamp, latest=False)
                return {"received": True, "applied": False, "reason": "A newer call owns this case's contact state; late or unorderable prior events are ignored."}
        result = self._apply("webhook-" + str(event), call, {"outcome": outcome}, "contact", {"case_id": case_id, "outcome": outcome})
        # Persist after the domain write. A crash between these writes can retry
        # the same idempotent command; it cannot lose the contact operation.
        self.bindings.record_lifecycle(call_id, case_id, "ended" if event == "call_ended" else "started", start_timestamp, latest=True)
        return {"received": True, "applied": True, "result": result}
