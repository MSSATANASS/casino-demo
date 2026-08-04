import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_db, get_current_user
from ..config import MAX_BET, MIN_BET, PLAY_RATE_LIMIT
from ..db import BlackjackRound, GameHistory, User, load_round
from ..games import blackjack, dice, fair, roulette, slots
from ..ratelimit import RateLimiter, client_ip

router = APIRouter(prefix="/api/games", tags=["games"])

play_limit = RateLimiter(*PLAY_RATE_LIMIT)


class PlayIn(BaseModel):
    bet: float
    client_seed: str | None = None


class BlackjackActionIn(BaseModel):
    round_id: int
    action: str


RATE_LIMITED = HTTPException(status_code=429, detail="Too many plays, slow down", headers={"Retry-After": "60"})


def _default_client_seed(user: User) -> str:
    return fair.hash_hex(f"{user.id}:{user.email}")


def _fair(user: User, client_seed: str | None) -> tuple[object, dict]:
    cs = client_seed or _default_client_seed(user)
    seed_used = user.server_seed
    commit_before = user.server_seed_commit
    round_no = (user.round_no or 0) + 1
    if not seed_used:
        seed_used = fair.gen_seed()
        commit_before = None
    next_seed = fair.gen_seed()
    user.server_seed = next_seed
    user.server_seed_commit = fair.hash_hex(next_seed)
    user.round_no = round_no
    fair_info = {
        "round_no": round_no,
        "client_seed": cs,
        "server_seed_used": seed_used,
        "commit_published_before": commit_before,
        "next_commit": user.server_seed_commit,
    }
    return fair.rng_for(seed_used, cs, round_no), fair_info


def _validate_bet(bet: float, chips: int):
    if not (MIN_BET <= bet <= MAX_BET) or bet > chips:
        raise HTTPException(status_code=400, detail="Invalid bet")


def _record(db: Session, user_id: int, game: str, bet: float, payout: float, result: dict):
    db.add(GameHistory(user_id=user_id, game=game, bet=bet, payout=payout, result=str(result)))
    db.commit()


@router.post("/slots/play")
def play_slots(
    body: PlayIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not play_limit.allowed(str(user.id), client_ip(request)):
        raise RATE_LIMITED
    _validate_bet(body.bet, user.chips)
    rng, fair_info = _fair(user, body.client_seed)
    result = slots.spin(body.bet, rng)
    user.chips = round(user.chips - body.bet + result["payout"], 2)
    _record(db, user.id, "slots", body.bet, result["payout"], result)
    return {"result": result, "chips": user.chips, "fair": fair_info}


@router.post("/roulette/play")
def play_roulette(
    body: PlayIn,
    bet_type: str,
    number: int | None = None,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not play_limit.allowed(str(user.id), client_ip(request)):
        raise RATE_LIMITED
    if bet_type not in roulette.PAYOUTS:
        raise HTTPException(status_code=400, detail="Invalid bet type")
    if bet_type == "straight" and (number is None or number not in roulette.NUMBERS):
        raise HTTPException(status_code=400, detail="Invalid number")
    _validate_bet(body.bet, user.chips)
    rng, fair_info = _fair(user, body.client_seed)
    result = roulette.spin(body.bet, bet_type, number, rng)
    user.chips = round(user.chips - body.bet + result["payout"], 2)
    _record(db, user.id, "roulette", body.bet, result["payout"], result)
    return {"result": result, "chips": user.chips, "fair": fair_info}


@router.post("/dice/play")
def play_dice(
    body: PlayIn,
    bet_type: str,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not play_limit.allowed(str(user.id), client_ip(request)):
        raise RATE_LIMITED
    if bet_type not in dice.PAYOUTS:
        raise HTTPException(status_code=400, detail="Invalid bet type")
    _validate_bet(body.bet, user.chips)
    rng, fair_info = _fair(user, body.client_seed)
    result = dice.spin(body.bet, bet_type, rng)
    user.chips = round(user.chips - body.bet + result["payout"], 2)
    _record(db, user.id, "dice", body.bet, result["payout"], result)
    return {"result": result, "chips": user.chips, "fair": fair_info}


@router.post("/blackjack/start")
def blackjack_start(
    body: PlayIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not play_limit.allowed(str(user.id), client_ip(request)):
        raise RATE_LIMITED
    _validate_bet(body.bet, user.chips)
    rng, fair_info = _fair(user, body.client_seed)
    user.chips = round(user.chips - body.bet, 2)
    deck = blackjack.new_shuffled_deck(rng)
    player = [blackjack.draw(deck), blackjack.draw(deck)]
    dealer = [blackjack.draw(deck), blackjack.draw(deck)]
    if blackjack.is_natural(player) or blackjack.is_natural(dealer):
        result = blackjack.natural_settle(body.bet, player, dealer)
        user.chips = round(user.chips + result["payout"], 2)
        _record(db, user.id, "blackjack", body.bet, result["payout"], result)
        return {
            "round_id": None,
            "player": player,
            "dealer": dealer,
            "dealer_hidden": False,
            "result": result,
            "can_act": False,
            "chips": user.chips,
            "fair": fair_info,
        }
    r = BlackjackRound(
        user_id=user.id,
        bet=body.bet,
        deck=json.dumps(deck),
        player_hand=json.dumps(player),
        dealer_hand=json.dumps(dealer),
        status="open",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {
        "round_id": r.id,
        "player": player,
        "dealer": dealer,
        "dealer_hidden": True,
        "result": None,
        "can_act": True,
        "chips": user.chips,
        "fair": fair_info,
    }


@router.post("/blackjack/action")
def blackjack_action(
    body: BlackjackActionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = db.get(BlackjackRound, body.round_id)
    if not r or r.user_id != user.id or r.status != "open":
        raise HTTPException(status_code=400, detail="Invalid round")
    if body.action not in ("hit", "stand", "double"):
        raise HTTPException(status_code=400, detail="Invalid action")
    deck, player, dealer = load_round(r)
    if body.action == "double":
        if r.doubled or len(player) != 2:
            raise HTTPException(status_code=400, detail="Double only at start")
        extra = r.bet
        if user.chips < extra:
            raise HTTPException(status_code=400, detail="Insufficient chips")
        user.chips = round(user.chips - extra, 2)
        r.bet = float(round(r.bet * 2, 2))
        r.doubled = 1
        player.append(blackjack.draw(deck))
    elif body.action == "hit":
        player.append(blackjack.draw(deck))

    if body.action == "hit" and blackjack.hand_value(player) < 21:
        r.deck = json.dumps(deck)
        r.player_hand = json.dumps(player)
        r.dealer_hand = json.dumps(dealer)
        db.commit()
        return {
            "round_id": r.id,
            "player": player,
            "dealer": dealer,
            "dealer_hidden": True,
            "result": None,
            "can_act": True,
            "chips": user.chips,
        }

    result = blackjack.play_out(r.bet, player, dealer, deck)
    user.chips = round(user.chips + result["payout"], 2)
    r.status = "done"
    r.deck = json.dumps(deck)
    r.player_hand = json.dumps(player)
    r.dealer_hand = json.dumps(dealer)
    _record(db, user.id, "blackjack", r.bet, result["payout"], result)
    return {
        "round_id": r.id,
        "player": player,
        "dealer": dealer,
        "dealer_hidden": False,
        "result": result,
        "can_act": False,
        "chips": user.chips,
    }


@router.get("/fair/state")
def fair_state(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.server_seed:
        user.server_seed = fair.gen_seed()
        user.server_seed_commit = fair.hash_hex(user.server_seed)
        db.commit()
    return {"round_no": user.round_no, "server_seed_commit": user.server_seed_commit}


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.chips.desc()).limit(20).all()
    return [
        {"username": u.username or f"player_{u.id}", "chips": u.chips}
        for u in rows
    ]


@router.get("/history")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(GameHistory)
        .filter(GameHistory.user_id == user.id)
        .order_by(GameHistory.id.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "game": h.game,
            "bet": h.bet,
            "payout": h.payout,
            "net": round(h.payout - h.bet, 2),
            "result": h.result,
            "at": h.created_at.isoformat(),
        }
        for h in rows
    ]