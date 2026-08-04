import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_casino.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef")
os.environ.setdefault("BONUS_CHIPS", "100")

DB_FILE = Path(__file__).resolve().parent.parent / "test_casino.db"
if DB_FILE.exists():
    DB_FILE.unlink()


import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from app.routers import auth as auth_router
    from app.routers import games as games_router

    auth_router.register_limit.reset()
    games_router.play_limit.reset()
    yield
    auth_router.register_limit.reset()
    games_router.play_limit.reset()