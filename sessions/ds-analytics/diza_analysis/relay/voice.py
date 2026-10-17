"""Retell browser voice adapter. Server-owned call bindings protect resident records."""

import json
import os
import time

import httpx

from .store import RelayError, identifier


class RelayVoice:
    def __init__(self, store):
        self.store = store

    @property
    def configured(self):
        return bool(os.getenv("RETELL_API_KEY") and os.getenv("RELAY_RETELL_AGENT_ID"))

    def create_call(self, body):
        try:
            response = httpx.post(
                "https://api.retellai.com/v3/create-web-call",
                json=body,
                headers={"Authorization": "Bearer " + os.environ["RETELL_API_KEY"]},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("access_token") or not data.get("call_id"):
                raise ValueError("Missing voice session fields")
            return data
        except (httpx.HTTPError, ValueError) as exc:
            raise RelayError(
                502,
                "Voice could not connect. Your saved record is safe; "
                "use the text form or try again.",
            ) from exc

    def start(self, record_id: str, payload: dict) -> dict:
        if payload["consent_to_voice"] is not True:
            raise RelayError(422, "Please agree to start a voice conversation first.")
        if not self.configured:
            raise RelayError(
                503,
                "Voice is not available right now. You can send your response using the text form.",
            )

        def reserve(connection):
            record = self.store._record(connection, record_id)
            active = connection.execute(
                """
                SELECT id FROM relay_attempts WHERE record_id=? AND channel='voice'
                AND status IN ('creating','connecting','ready','live') AND created>?
            """,
                (record_id, time.time() - 600),
            ).fetchone()
            if active:
                raise RelayError(
                    409,
                    "A voice session is already starting or active. End it before reconnecting.",
                )
            attempt_id = identifier()
            now = time.time()
            connection.execute(
                "INSERT INTO relay_attempts VALUES(?,?,?,'voice','creating',NULL,?,NULL)",
                (attempt_id, record_id, record["current_version"], now),
            )
            connection.execute(
                "UPDATE relay_records SET last_attempt_at=?,updated=? WHERE id=?",
                (now, now, record_id),
            )
            return {"attempt_id": attempt_id, "version": record["current_version"]}

        receipt = self.store._write(
            "voice:" + record_id, payload["idempotency_key"], payload, reserve
        )
        # Never create a second provider call for an HTTP retry of this attempt.
        with self.store.connect() as connection:
            attempt = dict(
                connection.execute(
                    "SELECT * FROM relay_attempts WHERE id=?", (receipt["attempt_id"],)
                ).fetchone()
            )
            if attempt["status"] != "creating":
                raise RelayError(
                    409, "This start request was already used. Reconnect with a new request."
                )
            claimed = connection.execute(
                "UPDATE relay_attempts SET status='connecting' WHERE id=? AND status='creating'",
                (attempt["id"],),
            ).rowcount
        if not claimed:
            raise RelayError(409, "This voice session is already connecting.")
        context = self.store.context(record_id)
        notice = context["notice"]
        body = {
            "agent_id": os.environ["RELAY_RETELL_AGENT_ID"],
            "retell_llm_dynamic_variables": {
                "resident_name": context["resident"]["name"],
                "language": payload["language"],
                "notice_version": str(notice["version"]),
                "notice_en": notice["content"]["en"]["text"],
                "notice_es": notice["content"]["es"]["text"],
                "saved_progress": json.dumps(context["draft"], ensure_ascii=False),
            },
            "metadata": {"relay_attempt_id": attempt["id"]},
            "agent_override": {
                "agent": {"language": "en-US" if payload["language"] == "en" else "es-ES"}
            },
        }
        try:
            result = self.create_call(body)
        except RelayError:
            with self.store.connect() as connection:
                connection.execute(
                    "UPDATE relay_attempts SET status='failed',ended=? WHERE id=?",
                    (time.time(), attempt["id"]),
                )
            raise
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE relay_attempts SET status='ready',call_id=?,version=? WHERE id=?",
                (result["call_id"], notice["version"], attempt["id"]),
            )
        return {
            "call_id": result["call_id"],
            "access_token": result["access_token"],
            "attempt_id": attempt["id"],
            "notice_version": notice["version"],
            **{
                key: result[key]
                for key in ("transport", "url", "ice_servers", "expires_at")
                if key in result
            },
        }

    def session(self, call_id: str) -> dict:
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM relay_attempts WHERE call_id=?", (call_id,)
            ).fetchone()
        if not row:
            raise RelayError(403, "This call is not linked to a RelayLA resident record.")
        return dict(row)

    def context(self, call_id: str) -> dict:
        session = self.session(call_id)
        context = self.store.context(session["record_id"])
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE relay_attempts SET version=? WHERE id=?",
                (context["notice"]["version"], session["id"]),
            )
        return context

    def respond(self, call_id: str, args: dict, action: str) -> dict:
        session = self.session(call_id)
        if args["notice_version"] != session["version"]:
            raise RelayError(
                409, "Call relay_context before confirming a notice version you have not delivered."
            )
        import hashlib

        key = hashlib.sha256(
            json.dumps([call_id, action, args], sort_keys=True).encode()
        ).hexdigest()
        payload = {
            "idempotency_key": key,
            "notice_version": args["notice_version"],
            "next_step": args.get("next_step", ""),
            "confirm_instruction": action == "confirm_instruction"
            and args.get("confirmed") is True,
            "needs_clarification": action == "needs_clarification",
            "assistance_needed": args.get("assistance_needed"),
            "assistance_details": args.get("assistance_details", ""),
            "confirm_assistance": action == "confirm_assistance" and args.get("confirmed") is True,
        }
        return self.store.respond(session["record_id"], payload, channel="voice")

    def end(self, call_id: str, status: str = "disconnected"):
        session = self.session(call_id)
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE relay_attempts SET status=?,ended=? WHERE id=?",
                (status, time.time(), session["id"]),
            )
