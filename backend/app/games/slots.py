import random

# Verified mock slot configuration from DeepSeek:
# - 3 reels, 1 line
# - x = total return (not net profit)
# - wild resolves to the best valid symbol on the line
# - one payout per line; scatter pays separately
# - strips are identical, length 50 each

CHERRY = "🍒"
LEMON = "🍋"
BELL = "⭐"
BAR = "BAR"
SEVEN = "7"
WILD = "💎"
SCATTER = "🃏"

STRIP = [
    CHERRY, CHERRY, CHERRY, CHERRY, CHERRY, CHERRY, CHERRY, CHERRY, CHERRY, CHERRY, CHERRY,
    LEMON, LEMON, LEMON, LEMON, LEMON, LEMON, LEMON, LEMON, LEMON, LEMON, LEMON, LEMON,
    BELL, BELL, BELL, BELL, BELL, BELL, BELL, BELL, BELL,
    BAR, BAR, BAR, BAR, BAR, BAR,
    SEVEN, SEVEN, SEVEN, SEVEN,
    WILD, WILD,
    SCATTER, SCATTER, SCATTER, SCATTER, SCATTER, SCATTER,
]

SYMBOLS = sorted(set(STRIP))

PAYTABLE = {
    CHERRY: {1: 1, 2: 2, 3: 5},
    LEMON: {3: 8},
    BELL: {3: 13},
    BAR: {3: 20},
    SEVEN: {3: 38},
    WILD: {3: 100},
}
SCATTER_PAYS = {2: 1, 3: 50}


def _visible_from_pos(pos: int) -> list[str]:
    n = len(STRIP)
    return [STRIP[(pos + i) % n] for i in range(3)]


def _count_scatter(grid: list[list[str]]) -> int:
    return sum(1 for col in grid for sym in col if sym == SCATTER)


def _line_payout(line: list[str]) -> float:
    # One classification per line. Wild resolves to the best valid base symbol.
    if line == [WILD, WILD, WILD]:
        return float(PAYTABLE[WILD][3])
    if SCATTER in line:
        return 0.0

    best = 0.0
    candidates = {sym for sym in line if sym not in {WILD, SCATTER}}
    for base in candidates:
        run = 0
        for sym in line:
            if sym == base or sym == WILD:
                run += 1
            else:
                break
        if base == CHERRY:
            pay = PAYTABLE[CHERRY].get(run, 0)
        else:
            pay = PAYTABLE.get(base, {}).get(3, 0) if run == 3 else 0
        if pay > best:
            best = float(pay)
    return best


def spin(bet: float, rng: random.Random) -> dict:
    # Build a 3x3 visible window from three independently stopped reels.
    reels = []
    stops = []
    for _ in range(3):
        stop = rng.randrange(len(STRIP))
        stops.append(stop)
        reels.append(_visible_from_pos(stop))

    payout = 0.0
    line = [reels[0][0], reels[1][0], reels[2][0]]
    payout += bet * _line_payout(line)

    scatters = _count_scatter(reels)
    payout += bet * float(SCATTER_PAYS.get(scatters, 0))

    return {
        "reels": reels,
        "stops": stops,
        "payout": round(payout, 2),
        "lines": [line],
        "scatter_count": scatters,
        "paytable": {
            "line": PAYTABLE,
            "scatter": SCATTER_PAYS,
            "wild": WILD,
            "scatter_symbol": SCATTER,
            "return_is_total": True,
        },
    }
