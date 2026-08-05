import logging
import os
import secrets

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./casino.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    if os.getenv("RENDER"):
        logging.warning("SECRET_KEY no configurado en producción: se genera clave efímera (los tokens expiran al reiniciar). Setea SECRET_KEY en Render para tokens estables.")
    else:
        logging.warning("SECRET_KEY no configurado: se usa clave efímera local.")

BONUS_CHIPS = int(os.getenv("BONUS_CHIPS", "100"))
JWT_EXPIRE_HOURS = 72

MIN_BET = 1
MAX_BET = int(os.getenv("MAX_BET", "1000"))

REGISTER_RATE_LIMIT = (5, 3600)
PLAY_RATE_LIMIT = (30, 60)
DEPOSIT_RATE_LIMIT = (10, 60)
