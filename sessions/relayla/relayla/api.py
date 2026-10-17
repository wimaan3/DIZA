"""Standalone FastAPI application, also mountable in DIZA's future backend."""

from hmac import compare_digest
from contextlib import asynccontextmanager
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from retell import AsyncRetell, APIError
from retell.lib.webhook_auth import verify

from .engine import DomainError, Store
from .retell_adapter import CallBindings, RetellAdapter
from .settings import Settings


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=180)
    payload: dict = Field(default_factory=dict)


class WebCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1, max_length=180)
    language: str = Field(pattern="^(en|es)$")


class RateGate:
    """Bound operator-triggered provider sessions, without a background dialer."""
    def __init__(self):
        self.lock = threading.Lock()
        self.starts: list[float] = []

    def acquire(self):
        now = time.monotonic()
        with self.lock:
            self.starts = [v for v in self.starts if v > now - 60]
            if len(self.starts) >= 6:
                raise HTTPException(429, "Live demo limit: at most six web-call starts per minute.")
            self.starts.append(now)


def create_app(settings: Settings | None = None, *, retell_client=None) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.retell_enabled and not settings.operator_token:
        raise ValueError("An operator token is required before enabling Retell.")
    store = Store(settings.db_path)
    bindings = CallBindings(settings.db_path)
    adapter = RetellAdapter(store, bindings)
    gate = RateGate()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            store.close()

    app = FastAPI(title="DIZA / RelayLA", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.store, app.state.adapter, app.state.settings = store, adapter, settings

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        # Without a configured token this is a loopback-only demo, including
        # protection against malicious Host headers / DNS rebinding.
        if not settings.operator_token:
            if request.url.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}:
                return JSONResponse(status_code=403, content={"detail": "Local demo only. Configure an operator token before exposing this service."})
            client_host = request.client.host if request.client else ""
            if client_host not in {"localhost", "127.0.0.1", "::1", "testclient"}:
                return JSONResponse(status_code=403, content={"detail": "Remote access requires an operator token."})
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin:
                parsed = urlsplit(origin)
                if parsed.netloc != request.headers.get("host") or parsed.scheme not in {"http", "https"}:
                    return JSONResponse(status_code=403, content={"detail": "Cross-origin mutation rejected."})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        route_path = request.url.path.removeprefix(request.scope.get("root_path", ""))
        if route_path.startswith(("/api/", "/retell/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    def operator(request: Request):
        if settings.operator_token and not compare_digest(request.headers.get("x-operator-token", ""), settings.operator_token):
            raise HTTPException(401, "Enter the configured operator token in Connection settings.")

    def state():
        result = store.state()
        result["integration"] = settings.public()
        return result

    @app.get("/health")
    def health():
        return {"ok": True, "service": "diza-relayla", "integration": settings.public()}

    @app.get("/api/state", dependencies=[Depends(operator)])
    def get_state():
        return state()

    @app.get("/api/cases/{case_id}", dependencies=[Depends(operator)])
    def get_case(case_id: str):
        return store.get_case(case_id)

    @app.post("/api/actions/{action}", dependencies=[Depends(operator)])
    def mutate(action: str, body: ActionRequest):
        result = store.apply(action, body.payload, body.event_id, actor="operator")
        return {"result": result, "state": state()}

    @app.post("/api/retell/web-call", dependencies=[Depends(operator)])
    async def create_web_call(body: WebCallRequest):
        if not settings.retell_ready:
            raise HTTPException(503, "Retell is not configured. The local workflow works without live voice.")
        case = store.get_case(body.case_id)
        gate.acquire()
        guidance = adapter.guidance(body.case_id, body.language)
        variables = {
            "case_id": case["id"], "resident_name": case["resident_name"], "language": body.language,
            "severity": case["severity"], "summary": case["summary"],
            "saved_case": json.dumps({k: case[k] for k in ("id", "communication_status", "assistance_status", "assistance_details", "acknowledged_version")}, ensure_ascii=False),
            "current_guidance": json.dumps(guidance, ensure_ascii=False),
        }
        client = retell_client or AsyncRetell(api_key=settings.retell_api_key, max_retries=0, timeout=15)
        try:
            response = await client.call.create_web_call(
                agent_id=settings.agent_id_es if body.language == "es" else settings.agent_id_en,
                agent_version="latest_published",
                metadata={"relayla_case_id": case["id"], "source": "diza-relayla", "demo": True},
                retell_llm_dynamic_variables=variables,
            )
            data = response.model_dump() if hasattr(response, "model_dump") else dict(response)
            bindings.bind(data["call_id"], case["id"])
            # Only short-lived browser connection fields; never the provider API key.
            return {key: data[key] for key in ("call_id", "access_token", "transport", "ice_servers", "expires_at") if key in data}
        except APIError as exc:
            raise HTTPException(502, "Retell could not start this web call. Check agent publication, account access, credits and connectivity.") from exc
        finally:
            if retell_client is None:
                await client.close()

    async def signed_envelope(request: Request) -> dict:
        if not settings.retell_enabled or not settings.retell_api_key:
            raise HTTPException(503, "Provider callbacks are disabled in local demo mode.")
        chunks, length = [], 0
        async for chunk in request.stream():
            length += len(chunk)
            if length > 524288:
                raise HTTPException(413, "Provider payload exceeds 512 KiB.")
            chunks.append(chunk)
        try:
            raw = b"".join(chunks).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(400, "Expected UTF-8 JSON.") from exc
        signature = request.headers.get("x-retell-signature", "")
        try:
            verified = verify(raw, settings.retell_api_key, signature)
        except (ValueError, TypeError):
            verified = False
        if not verified:
            raise HTTPException(401, "Invalid or expired Retell signature.")
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "Expected a JSON object.") from exc
        if not isinstance(envelope, dict) or not isinstance(envelope.get("call"), dict):
            raise HTTPException(422, "Expected a Retell call envelope.")
        if envelope["call"].get("agent_id") not in settings.allowed_agent_ids:
            raise HTTPException(403, "This Retell agent is not configured for RelayLA.")
        return envelope

    @app.post("/retell/functions/{name}")
    async def retell_function(name: str, request: Request):
        envelope = await signed_envelope(request)
        return adapter.dispatch(name, envelope)

    @app.post("/retell/webhook")
    async def webhook(request: Request):
        return adapter.webhook(await signed_envelope(request))

    static_dir = Path(__file__).with_name("static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def index():
        return FileResponse(static_dir / "index.html")

    return app
