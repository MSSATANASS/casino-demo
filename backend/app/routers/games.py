from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_db, get_current_user
from ..db import User, GameHistory
from ..games import slots, blackjack, roulette

router = APIRouter(prefix="/api/games", tags=["games"])


class PlayIn(BaseModel):
    bet: float


class BlackjackIn(BaseModel):
    bet: float
    player: list[dict]
    dealer: list[dict]


@router.post("/slots/play")
def play_slots(body: PlayIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.bet <= 0 or body.bet > user.chips:
        raise HTTPException(status_code=400, detail="Invalid bet")
    result = slots.spin(body.bet)
    user.chips = round(user.chips - body.bet + result["payout"], 2)
    _record(db, user.id, "slots", body.bet, result["payout"], result)
    return {"result": result, "chips": user.chips}


@router.post("/roulette/play")
def play_roulette(
    body: PlayIn,
    bet_type: str,
    number: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if bet_type not in roulette.PAYOUTS:
        raise HTTPException(status_code=400, detail="Invalid bet type")
    if bet_type == "straight" and (number is None or number not in roulette.NUMBERS):
        raise HTTPException(status_code=400, detail="Invalid number")
    if body.bet <= 0 or body.bet > user.chips:
        raise HTTPException(status_code=400, detail="Invalid bet")
    result = roulette.spin(body.bet, bet_type, number)
    user.chips = round(user.chips - body.bet + result["payout"], 2)
    _record(db, user.id, "roulette", body.bet, result["payout"], result)
    return {"result": result, "chips": user.chips}


@router.post("/blackjack/play")
def play_blackjack(body: BlackjackIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.bet <= 0 or body.bet > user.chips:
        raise HTTPException(status_code=400, detail="Invalid bet")
    deck = blackjack.new_deck()
    result = blackjack.play(body.bet, body.player, body.dealer, deck)
    user.chips = round(user.chips - body.bet + result["payout"], 2)
    _record(db, user.id, "blackjack", body.bet, result["payout"], result)
    return {"result": result, "chips": user.chips}


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.chips.desc()).limit(20).all()
    return [{"email": u.email, "chips": u.chips} for u in rows]


def _record(db: Session, user_id: int, game: str, bet: float, payout: float, result: dict):
    db.add(GameHistory(user_id=user_id, game=game, bet=bet, payout=payout, result=str(result)))
    db.commit()