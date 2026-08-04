import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    chips = Column(Integer, nullable=False, default=0)
    server_seed = Column(String, nullable=True)
    server_seed_commit = Column(String, nullable=True)
    round_no = Column(Integer, nullable=False, default=0)
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


def _migrate():
    insp = inspect(engine)
    if "users" in insp.get_table_names():
        existing = {c["name"] for c in insp.get_columns("users")}
        with engine.begin() as conn:
            for col, ddl in (("server_seed", "VARCHAR"), ("server_seed_commit", "VARCHAR"), ("round_no", "INTEGER DEFAULT 0")):
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {ddl}"))


def init_db():
    _migrate()
    Base.metadata.create_all(bind=engine)


def dump_round(deck, player, dealer) -> tuple[str, str, str]:
    return json.dumps(deck), json.dumps(player), json.dumps(dealer)


def load_round(r: BlackjackRound) -> tuple[list[dict], list[dict], list[dict]]:
    return json.loads(r.deck), json.loads(r.player_hand), json.loads(r.dealer_hand)