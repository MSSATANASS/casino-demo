import random

SYMBOLS = ["7", "BAR", "🍒", "🍋", "⭐", "💎"]
MULTIPLIERS = {"7": 10, "💎": 5, "BAR": 3, "⭐": 2, "🍒": 1.5, "🍋": 0}


def spin(bet: float, rng: random.Random) -> dict:
    reels = [[rng.choice(SYMBOLS) for _ in range(3)] for _ in range(3)]
    payout = 0.0
    for row in range(3):
        line = [reels[col][row] for col in range(3)]
        if len(set(line)) == 1:
            payout += bet * MULTIPLIERS[line[0]]
    return {"reels": reels, "payout": round(payout, 2)}