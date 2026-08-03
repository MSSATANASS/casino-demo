from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

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


def init_db():
    Base.metadata.create_all(bind=engine)