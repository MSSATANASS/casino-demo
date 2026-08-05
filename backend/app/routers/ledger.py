from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..auth import get_db, get_current_user
from ..config import DEPOSIT_RATE_LIMIT
from ..db import User, LedgerEntry, record_ledger_event
from ..routers.games import _lock_for
from ..ratelimit import RateLimiter, client_ip

router = APIRouter(prefix="/api/ledger", tags=["ledger"])

deposit_limit = RateLimiter(*DEPOSIT_RATE_LIMIT)
adjust_limit = RateLimiter(60, 60)


class DepositIn(BaseModel):
    amount: int = Field(..., gt=0, le=10000, description="Amount in chips (1-10000)")
    idempotency_key: str = Field(..., min_length=1, max_length=255, description="Idempotency key")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if not (1 <= v <= 10000):
            raise ValueError("Amount must be an integer between 1 and 10000")
        return v

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: str) -> str:
        if not v or len(v) > 256:
            raise ValueError("Idempotency key must be between 1 and 256 characters")
        return v


class AdjustIn(BaseModel):
    kind: str = Field(..., description="bet | win | withdraw")
    amount: int = Field(..., gt=0, le=100000)
    game: str = Field("", max_length=32)
    note: str = Field("", max_length=256)
    idempotency_key: str = Field(..., min_length=1, max_length=255)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v not in ("bet", "win", "withdraw"):
            raise ValueError("kind must be bet, win or withdraw")
        return v

    @field_validator("idempotency_key")
    @classmethod
    def validate_adjust_key(cls, v: str) -> str:
        if not v or len(v) > 256:
            raise ValueError("Idempotency key must be between 1 and 256 characters")
        return v


class LedgerEntryOut(BaseModel):
    id: int
    kind: str
    amount: float  # in chips
    idempotency_key: str
    meta: str
    created_at: str  # ISO string


@router.post("/deposit", status_code=201)
def deposit(
    body: DepositIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not deposit_limit.allowed(client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many deposit requests",
            headers={"Retry-After": "60"},
        )
    # Use per-user lock to avoid race conditions on user.chips
    with _lock_for(user.id):
        db.refresh(user)
        # Check for existing entry with the same key BEFORE recording
        existing = (
            db.query(LedgerEntry)
            .filter(
                LedgerEntry.user_id == user.id,
                LedgerEntry.idempotency_key == body.idempotency_key,
                LedgerEntry.kind == "deposit",
            )
            .first()
        )
        if existing:
            return {"chips": user.chips, "deposited": body.amount}
        # Record ledger entry for deposit (kind="deposit")
        # amount in chips -> convert to cents for storage
        amount_cents = int(round(body.amount * 100))
        record_ledger_event(
            db,
            user_id=user.id,
            kind="deposit",
            amount=amount_cents,
            idempotency_key=body.idempotency_key,
            meta={"source": "deposit_endpoint", "note": "Compra de fichas"},
        )
        # Update user chips
        user.chips = user.chips + body.amount
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"chips": user.chips, "deposited": body.amount}


@router.post("/adjust")
def adjust(
    body: AdjustIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sincroniza el saldo real con rondas de Crash/Mines/Plinko/Towers.

    Estos 4 juegos todavia corren el RNG en el cliente (a diferencia de
    slots/roulette/dice/blackjack, que son server-authoritative), asi que el
    resultado llega reportado desde el navegador. Se valida que el saldo
    nunca quede negativo y se aplica idempotencia igual que en /deposit.
    """
    if not adjust_limit.allowed(client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": "60"},
        )
    with _lock_for(user.id):
        db.refresh(user)
        existing = (
            db.query(LedgerEntry)
            .filter(LedgerEntry.user_id == user.id, LedgerEntry.idempotency_key == body.idempotency_key)
            .first()
        )
        if existing:
            return {"chips": user.chips}
        delta = -body.amount if body.kind in ("bet", "withdraw") else body.amount
        if delta < 0 and user.chips + delta < 0:
            raise HTTPException(status_code=400, detail="Insufficient chips")
        db_kind = "bet" if body.kind == "bet" else ("payout" if body.kind == "win" else "withdraw")
        record_ledger_event(
            db,
            user_id=user.id,
            kind=db_kind,
            amount=int(round(delta * 100)),
            idempotency_key=body.idempotency_key,
            meta={"game": body.game, "note": body.note, "client_reported": True},
        )
        user.chips = max(0, user.chips + delta)
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"chips": user.chips}


@router.get("/entries", response_model=List[LedgerEntryOut])
def list_entries(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of entries to return"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.user_id == user.id)
        .order_by(LedgerEntry.id.desc())
        .limit(limit)
        .all()
    )
    # Convert amount from cents to chips for output
    result = []
    for e in entries:
        result.append(
            LedgerEntryOut(
                id=e.id,
                kind=e.kind,
                amount=e.amount / 100.0,  # cents to chips
                idempotency_key=e.idempotency_key,
                meta=e.meta,
                created_at=e.created_at.isoformat(),
            )
        )
    return result
