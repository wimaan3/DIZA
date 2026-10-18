"""Add /city-3d/ without editing the existing DIZA backend or dashboard."""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'cs2-backend' / 'mvp'))
from backend.app.main import app as existing_app  # noqa: E402


@asynccontextmanager
async def lifespan(app):
    # Mounted ASGI apps do not receive startup/shutdown automatically.
    async with existing_app.router.lifespan_context(existing_app):
        yield


app = FastAPI(title='DIZA with Los Angeles 3D', lifespan=lifespan)


@app.get('/city-3d', include_in_schema=False)
async def city_redirect():
    return RedirectResponse('/city-3d/')


app.mount('/city-3d', StaticFiles(directory=HERE / 'dist', html=True), name='city-3d')
# Original /api/* guard, Retell routes, dashboard and operational behavior stay intact.
app.mount('/', existing_app)
