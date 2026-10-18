"""Isolated, localhost-oriented hotel demonstration API."""

import hmac
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .store import HotelError, HotelStore

ASSETS = Path(__file__).resolve().parents[1] / "hotel_web"


class Keyed(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    idempotency_key: str = Field(min_length=8, max_length=160)


class Start(Keyed):
    room: str = Field(pattern=r"^[34](?:0[1-9]|1[0-2])$")
    language: Literal["en", "es"] = "en"


class Message(Keyed):
    text: str = Field(min_length=1, max_length=1000)


class Confirmation(Keyed):
    expected_revision: int = Field(ge=1)
    confirmed: StrictBool
    access_ok: StrictBool = False


class Decision(Keyed):
    expected_revision: int = Field(ge=1)
    action: Literal["assign", "start", "complete", "note"]
    staff_id: str = Field(default="", max_length=40)
    note: str = Field(default="", max_length=1000)


def create_app(database, operator_token, *, seed=False):
    store = HotelStore(database)
    store.initialize(seed=seed)
    app = FastAPI(title="DIZA Hotel Service Demo")
    app.state.hotel_store = store

    @app.exception_handler(HotelError)
    async def hotel_error(request, exc):
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    def staff(request: Request):
        if not operator_token or not hmac.compare_digest(
            request.headers.get("authorization", "").encode(),
            ("Bearer " + operator_token).encode(),
        ):
            raise HotelError(401, "Enter the demo staff token to open the front desk.")

    def guest(session_id: str, request: Request):
        store.authenticate(session_id, request.headers.get("x-guest-token", ""))

    @app.get("/health/hotel")
    def health():
        return {"status": "ok", "mode": "hotel", "synthetic": True, "voice_available": False}

    @app.get("/api/hotel/options")
    def options():
        return {"rooms": [str(floor * 100 + room) for floor in (3, 4) for room in range(1, 13)]}

    @app.get("/api/hotel/state", dependencies=[Depends(staff)])
    def state():
        return store.dashboard()

    @app.get("/api/hotel/tickets/{ticket_id}", dependencies=[Depends(staff)])
    def detail(ticket_id: int):
        return store.detail(ticket_id)

    @app.post("/api/hotel/tickets/{ticket_id}", dependencies=[Depends(staff)])
    def decide(ticket_id: int, payload: Decision):
        return store.update(ticket_id, payload.model_dump())

    @app.post("/api/hotel/guest/start")
    def start(payload: Start):
        return store.start(payload.model_dump())

    @app.get("/api/hotel/guest/{session_id}", dependencies=[Depends(guest)])
    def session(session_id: str):
        return store.session(session_id)

    @app.post("/api/hotel/guest/{session_id}/message", dependencies=[Depends(guest)])
    def message(session_id: str, payload: Message):
        return store.message(session_id, payload.model_dump())

    @app.post("/api/hotel/guest/{session_id}/confirm", dependencies=[Depends(guest)])
    def confirm(session_id: str, payload: Confirmation):
        return store.confirm(session_id, payload.model_dump())

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/hotel")

    for path in ("/hotel", "/building", "/ops"):
        app.add_api_route(
            path,
            lambda: FileResponse(ASSETS / "index.html"),
            methods=["GET"],
            include_in_schema=False,
        )
    app.mount("/hotel/assets", StaticFiles(directory=ASSETS), name="hotel-assets")

    @app.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return app
