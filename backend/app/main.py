from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .db import init_db
from .routers import auth as auth_router
from .routers import games as games_router

app = FastAPI(title="Casino Demo", description="Demo con fichas virtuales - sin dinero real")

init_db()

app.include_router(auth_router.router)
app.include_router(games_router.router)

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")