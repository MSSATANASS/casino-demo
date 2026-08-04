import random

# Verified mock slot configuration from DeepSeek:
# - 3 reels, 1 line
# - x = total return (not net profit)
# - wild substitutes everything except scatter
# - scatter pays separately and can stack with line wins
# - strips are identical, length 50 each

STRIP = [
    "🍒", "🍒", "🍒", "🍒", "🍒", "🍒", "🍒", "🍒", "🍒", "🍒", "🍒",
    "🍋", "🍋", "🍋", "🍋", "🍋", "🍋", "🍋", "🍋", "🍋", "🍋", "🍋", "🍋",
    "⭐", "⭐", "⭐", "⭐", "⭐", "⭐", "⭐", "⭐", "⭐",
    "BAR", "BAR", "BAR", "BAR", "BAR", "BAR",
    "7", "7", "7", "7",
    "💎", "💎",
    "☀", "☀", "☀", "☀", "☀", "☀",
]

SYMBOLS = sorted(set(STRIP + ["🃏"]))

PAYTABLE = {
    ("🍒",): {1: 1, 2: 2, 3: 5},
    ("🍋",): {3: 8},
    ("⭐",): {3: 12},
    ("BAR",): {3: 20},
    ("7",): {3: 40},
    ("💎",): {3: 100},
    ("☀",): {3: 50},
}
SCATTER = "🃏"
SCATTER_PAYS = {2: 1, 3: 50}
WILD = "💎"


def _visible_from_pos(pos: int) -> list[str]:
    n = len(STRIP)
    return [STRIP[(pos + i) % n] for i in range(3)]


def _count_scatter(grid: list[list[str]]) -> int:
    return sum(1 for col in grid for sym in col if sym == SCATTER)


def _line_payout(line: list[str]) -> float:
    # Wilds behave as substitutes, but W-W-W is its own jackpot bucket.
    if line == [WILD, WILD, WILD]:
        return 100.0

    if SCATTER in line:
        return 0.0

    # Count consecutive matches from left to right, with wild substitution.
    base = None
    run = 0
    for sym in line:
        if sym == WILD:
            run += 1
            continue
        if base is None:
            base = sym
            run += 1
            continue
        if sym == base:
            run += 1
        else:
            break
    if base is None:
        return 0.0

    # For cherries we pay partials on 1 and 2 from left to right.
    if base == "🍒":
        return float(PAYTABLE[("🍒",)].get(run, 0))
    if run == 3 and (base,) in PAYTABLE and 3 in PAYTABLE[(base,)]:
        return float(PAYTABLE[(base,)][3])
    return 0.0


def spin(bet: float, rng: random.Random) -> dict:
    # Build a 3x3 window from three independently stopped reels.
    reels = []
    stops = []
    for _ in range(3):
        stop = rng.randrange(len(STRIP))
        stops.append(stop)
        reels.append(_visible_from_pos(stop))

    payout = 0.0
    lines = [
        [reels[0][0], reels[1][0], reels[2][0]],
    ]

    for line in lines:
        payout += bet * _line_payout(line)

    scatters = _count_scatter(reels)
    payout += bet * float(SCATTER_PAYS.get(scatters, 0))

    return {
        "reels": reels,
        "stops": stops,
        "payout": round(payout, 2),
        "lines": lines,
        "scatter_count": scatters,
        "paytable": {
            "line": PAYTABLE,
            "scatter": SCATTER_PAYS,
            "wild": WILD,
            "scatter_symbol": SCATTER,
            "return_is_total": True,
        },
    }
