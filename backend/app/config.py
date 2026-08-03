import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./casino.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
BONUS_CHIPS = int(os.getenv("BONUS_CHIPS", "100"))
JWT_EXPIRE_HOURS = 72

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)