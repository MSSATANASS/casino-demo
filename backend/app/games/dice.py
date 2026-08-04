PAYOUTS = {"under7": 1, "over7": 1, "7": 4}


def spin(bet: float, bet_type: str, rng) -> dict:
    d1 = rng.randint(1, 6)
    d2 = rng.randint(1, 6)
    total = d1 + d2
    won = (
        (bet_type == "under7" and total < 7)
        or (bet_type == "over7" and total > 7)
        or (bet_type == "7" and total == 7)
    )
    payout = bet * (1 + PAYOUTS[bet_type]) if won else 0.0
    return {
        "dice": [d1, d2],
        "total": total,
        "bet_type": bet_type,
        "won": won,
        "payout": round(payout, 2),
    }