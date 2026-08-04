import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./casino.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")


def _ensure_secret_key():
    sk = os.getenv("SECRET_KEY", "dev-secret-key")
    if os.getenv("RENDER") and sk in ("", "dev-secret-key"):
        raise RuntimeError("SECRET_KEY must be set in production (Render)")


_ensure_secret_key()

BONUS_CHIPS = int(os.getenv("BONUS_CHIPS", "100"))
JWT_EXPIRE_HOURS = 72

MIN_BET = 1
MAX_BET = int(os.getenv("MAX_BET", "1000"))

REGISTER_RATE_LIMIT = (5, 3600)
PLAY_RATE_LIMIT = (30, 60)