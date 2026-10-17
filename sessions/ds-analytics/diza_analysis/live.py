"""ASGI entry point that composes analytics with the existing DIZA application."""

import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask, BackgroundTasks
from starlette.concurrency import run_in_threadpool

from .live_store import LiveStore

LOG = logging.getLogger(__name__)
ASSETS = Path(__file__).parent / "web"


def create_app():
    """Run from the existing backend work directory, preserving its routes and lifecycle."""
    backend = import_module("backend.app.main")
    store = LiveStore(backend.connect, salt=os.environ.get("DIZA_ANALYTICS_SALT", ""))

    @asynccontextmanager
    async def lifespan(app):
        async with backend.app.router.lifespan_context(backend.app):
            await run_in_threadpool(store.initialize)
            yield

    app = FastAPI(title="DIZA with analytics", lifespan=lifespan)

    def operator(request: Request):
        token = os.environ.get("OPS_API_TOKEN", "")
        if not token:
            raise HTTPException(503, "Operator authentication is not configured")
        if not hmac.compare_digest(
            request.headers.get("authorization", "").encode(), ("Bearer " + token).encode()
        ):
            raise HTTPException(401, "Operator token required")

    @app.get("/health/analysis")
    def health():
        return {
            "status": "ok",
            "analysis": "enabled",
            "configured": len(store.salt.encode()) >= 16,
            "revision": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "local"),
        }

    @app.get("/analytics")
    def analytics_page():
        return FileResponse(ASSETS / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/api/analytics", dependencies=[Depends(operator)])
    def analytics():
        return JSONResponse(store.dashboard(now=time.time()), headers={"Cache-Control": "no-store"})

    def observe_safely(payload):
        try:
            store.observe(payload)
        except Exception:
            # No caller input, transcripts, phone numbers, or provider errors in logs.
            LOG.error("Analytics observation failed; operational request completed")

    @app.middleware("http")
    async def observe_signed_requests(request, call_next):
        path = request.url.path
        payload = None
        if request.method == "POST" and (
            path == "/retell/webhook" or path.startswith("/retell/fn/")
        ):
            raw = await request.body()
            if len(raw) <= 2_000_000:
                try:
                    parsed = json.loads(raw)
                    payload = parsed if isinstance(parsed, dict) else None
                except (ValueError, UnicodeDecodeError):
                    pass
        response = await call_next(request)
        # The child verifies the original raw body and signature. Rejected requests
        # never contribute, and storage executes after the response has been sent.
        if payload is not None and 200 <= response.status_code < 300:
            tasks = BackgroundTasks()
            if response.background:
                tasks.add_task(response.background)
            tasks.tasks.append(BackgroundTask(observe_safely, payload))
            response.background = tasks
        return response

    app.mount("/analytics/assets", StaticFiles(directory=ASSETS), name="analysis-assets")
    # The existing app's SPA catch-all stays after the specific analytics routes.
    app.mount("/", backend.app)
    app.state.analysis_store = store
    return app
