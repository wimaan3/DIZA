"""Coordinator, resident, and verified Retell interfaces share one domain store."""

import hmac
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from .models import (
    ContactAttempt,
    Publish,
    Resident,
    Response,
    TaskDecision,
    VoiceResponse,
    VoiceStart,
)
from .store import RelayError, RelayStore
from .voice import RelayVoice

ASSETS = Path(__file__).resolve().parents[1] / "relay_web"


def install(app, backend):
    store, voice = RelayStore(backend.connect), None
    voice = RelayVoice(store)
    app.state.relay_store, app.state.relay_voice = store, voice

    @app.exception_handler(RelayError)
    async def relay_error(request, exc):
        return JSONResponse(
            {"detail": exc.message}, status_code=exc.status, headers={"Cache-Control": "no-store"}
        )

    def operator(request: Request):
        token = os.environ.get("OPS_API_TOKEN", "")
        if not token:
            raise RelayError(503, "Operator access has not been configured.")
        if not hmac.compare_digest(
            request.headers.get("authorization", "").encode(), ("Bearer " + token).encode()
        ):
            raise RelayError(401, "Operator token required.")

    def resident(record_id: str, request: Request):
        store.authenticate(record_id, request.headers.get("x-relay-token", ""))

    coordinator = APIRouter(prefix="/api/relay", dependencies=[Depends(operator)])
    public = APIRouter(prefix="/api/relay/resident")

    @coordinator.get("/dashboard")
    def dashboard():
        return {**store.dashboard(), "voice_available": voice.configured}

    @coordinator.post("/demo")
    def seed_demo():
        return store.seed_demo()

    @coordinator.post("/notices")
    def create_notice(payload: Publish):
        # A stable notice ID for a create retry, derived from the request key.
        import hashlib

        notice_id = hashlib.sha256(
            ("relay-notice:" + payload.idempotency_key).encode()
        ).hexdigest()[:32]
        return store.publish(notice_id, payload.model_dump())

    @coordinator.post("/notices/{notice_id}/publish")
    def publish(notice_id: str, payload: Publish):
        return store.publish(notice_id, payload.model_dump())

    @coordinator.post("/residents")
    def add_resident(payload: Resident):
        return store.add_resident(payload.model_dump())

    @coordinator.get("/records/{record_id}")
    def record_detail(record_id: str):
        return store.context(record_id, history=True)

    @coordinator.post("/records/{record_id}/attempts")
    def attempt(record_id: str, payload: ContactAttempt):
        return store.contact_attempt(record_id, payload.model_dump())

    @coordinator.post("/assistance/{task_id}/decision")
    def decide(task_id: str, payload: TaskDecision):
        return store.decide(task_id, payload.model_dump())

    @public.get("/{record_id}/context", dependencies=[Depends(resident)])
    def context(record_id: str):
        return {**store.context(record_id), "voice_available": voice.configured}

    @public.post("/{record_id}/response", dependencies=[Depends(resident)])
    def respond(record_id: str, payload: Response):
        return store.respond(record_id, payload.model_dump())

    @public.post("/{record_id}/voice", dependencies=[Depends(resident)])
    def start_voice(record_id: str, payload: VoiceStart):
        return voice.start(record_id, payload.model_dump())

    @public.post("/{record_id}/voice/{attempt_id}/end", dependencies=[Depends(resident)])
    def stop_voice(record_id: str, attempt_id: str):
        with store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM relay_attempts WHERE id=? AND record_id=?", (attempt_id, record_id)
            ).fetchone()
            if not row:
                raise RelayError(404, "Conversation not found.")
            if row["call_id"]:
                voice.end(row["call_id"])
        return {"saved": True, "context": store.context(record_id)}

    @app.post("/retell/relay/fn/{action}")
    async def function(action: str, request: Request):
        payload = await backend.verified_body(request)
        call_id = (payload.get("call") or {}).get("call_id", "")
        if action == "context":
            return voice.context(call_id)
        if action not in {
            "save_progress",
            "confirm_instruction",
            "confirm_assistance",
            "needs_clarification",
        }:
            raise RelayError(404, "RelayLA function not found.")
        try:
            args = VoiceResponse.model_validate(payload.get("args") or {}).model_dump()
        except ValidationError as exc:
            raise RelayError(
                422,
                "Function arguments must include a notice version "
                "and explicit confirmation fields.",
            ) from exc
        return voice.respond(call_id, args, action)

    @app.post("/retell/relay/webhook", status_code=204)
    async def webhook(request: Request):
        payload = await backend.verified_body(request)
        call_id = (payload.get("call") or {}).get("call_id", "")
        session = voice.session(call_id)
        if payload.get("event") == "call_started":
            with store.connect() as connection:
                connection.execute(
                    """UPDATE relay_attempts SET status='live'
                       WHERE id=? AND status IN ('ready','connecting')""",
                    (session["id"],),
                )
        elif payload.get("event") in {"call_ended", "call_analyzed"}:
            voice.end(call_id, "ended")

    for path in ("/", "/ops", "/relay"):
        app.add_api_route(
            path,
            lambda: FileResponse(ASSETS / "coordinator.html"),
            methods=["GET"],
            include_in_schema=False,
        )
    for path in ("/respond", "/respond/{record_id}"):
        app.add_api_route(
            path,
            lambda: FileResponse(ASSETS / "resident.html"),
            methods=["GET"],
            include_in_schema=False,
        )

    @app.get("/relay-sw.js", include_in_schema=False)
    def service_worker():
        return FileResponse(
            ASSETS / "sw.js",
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
        )

    @app.get("/health/relay")
    def health():
        return {"status": "ok", "product": "RelayLA", "voice_available": voice.configured}

    app.include_router(coordinator)
    app.include_router(public)
    from fastapi.staticfiles import StaticFiles

    app.mount("/relay/assets", StaticFiles(directory=ASSETS), name="relay-assets")

    @app.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/api/relay", "/respond")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return store
