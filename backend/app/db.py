import json
import re
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragma(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True, index=True)
    password_hash = Column(String, nullable=False)
    chips = Column(Integer, nullable=False, default=0)
    server_seed = Column(String, nullable=True)
    server_seed_commit = Column(String, nullable=True)
    round_no = Column(Integer, nullable=False, default=0)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GameHistory(Base):
    __tablename__ = "game_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    game = Column(String, nullable=False)
    bet = Column(Float, nullable=False)
    payout = Column(Float, nullable=False)
    result = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class BlackjackRound(Base):
    __tablename__ = "blackjack_rounds"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    bet = Column(Float, nullable=False)
    deck = Column(Text, nullable=False)
    player_hand = Column(Text, nullable=False)
    dealer_hand = Column(Text, nullable=False)
    doubled = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    kind = Column(String, nullable=False)  # deposit | bet | payout | bonus | adjustment
    amount = Column(Integer, nullable=False)
    idempotency_key = Column(String, nullable=False, index=True)
    meta = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


def normalize_handle(raw: str) -> str:
    name = re.sub(r"[^a-z0-9_.-]", "", (raw or "").lower())
    return (name[:16] or "player").rstrip("._-") or "player"


def record_ledger_event(db, *, user_id: int, kind: str, amount: int, idempotency_key: str, meta: dict | None = None):
    """Idempotent ledger insert for mock balances and future payment stubs."""
    existing = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.user_id == user_id, LedgerEntry.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        return existing
    row = LedgerEntry(
        user_id=user_id,
        kind=kind,
        amount=int(amount),
        idempotency_key=idempotency_key,
        meta=json.dumps(meta or {}, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _migrate():
    insp = inspect(engine)
    if "users" in insp.get_table_names():
        existing = {c["name"] for c in insp.get_columns("users")}
        with engine.begin() as conn:
            for col, ddl in (
                ("server_seed", "VARCHAR"),
                ("server_seed_commit", "VARCHAR"),
                ("round_no", "INTEGER DEFAULT 0"),
                ("username", "VARCHAR"),
                ("source", "VARCHAR"),
            ):
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {ddl}"))
            null_users = conn.execute(
                text("SELECT id, email FROM users WHERE username IS NULL OR username = '' ORDER BY id")
            ).all()
            if null_users:
                used: set[str] = set()
                for uid, email in null_users:
                    base = normalize_handle(email.split("@")[0]) if email else "player"
                    name, n = base, 1
                    while name in used:
                        name, n = f"{base}{n}", n + 1
                    used.add(name)
                    conn.execute(
                        text("UPDATE users SET username = :u WHERE id = :i"),
                        {"u": name, "i": uid},
                    )


def init_db():
    _migrate()
    Base.metadata.create_all(bind=engine)


def dump_round(deck, player, dealer) -> tuple[str, str, str]:
    return json.dumps(deck), json.dumps(player), json.dumps(dealer)


def load_round(r: BlackjackRound) -> tuple[list[dict], list[dict], list[dict]]:
    return json.loads(r.deck), json.loads(r.player_hand), json.loads(r.dealer_hand)
