import random

NUMBERS = list(range(37))
PAYOUTS = {
    "straight": 35,
    "red": 1,
    "black": 1,
    "even": 1,
    "odd": 1,
    "low": 1,
    "high": 1,
}
REDS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


def spin(bet: float, bet_type: str, number: int | None, rng: random.Random) -> dict:
    result = rng.choice(NUMBERS)
    won = False
    if bet_type == "straight":
        won = result == number
    elif bet_type == "red":
        won = result in REDS
    elif bet_type == "black":
        won = result not in REDS and result != 0
    elif bet_type == "even":
        won = result != 0 and result % 2 == 0
    elif bet_type == "odd":
        won = result % 2 == 1
    elif bet_type == "low":
        won = 1 <= result <= 18
    elif bet_type == "high":
        won = 19 <= result <= 36
    payout = bet * (1 + PAYOUTS[bet_type]) if won else 0.0
    return {"number": result, "bet_type": bet_type, "won": won, "payout": round(payout, 2)}