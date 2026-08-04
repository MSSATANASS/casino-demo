import random

# Sprint 1 baseline verified with DeepSeek:
# - 6 decks
# - dealer stands on soft 17 (S17)
# - double after split allowed
# - no surrender, no resplit aces, max 3 resplits
# - natural blackjack pays 3:2
# - bets should be in even-unit increments if you want clean 3:2 resolution;
#   this MVP truncates the half-unit in favor of the player when needed.

RANKS = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]
SUITS = ["♠", "♥", "♦", "♣"]
DECK_COUNT = 6


def _value(rank: str) -> int:
    if rank == "A":
        return 11
    if rank in ("K", "Q", "J", "10"):
        return 10
    return int(rank)


def new_shuffled_deck(rng: random.Random) -> list[dict]:
    deck = [
        {"rank": r, "suit": s, "value": _value(r)}
        for _ in range(DECK_COUNT)
        for r in RANKS
        for s in SUITS
    ]
    rng.shuffle(deck)
    return deck


def draw(deck: list[dict]) -> dict:
    return deck.pop()


def hand_value(hand: list[dict]) -> int:
    total = sum(c["value"] for c in hand)
    aces = sum(1 for c in hand if c["rank"] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def is_soft(hand: list[dict]) -> bool:
    total = sum(c["value"] for c in hand)
    aces = sum(1 for c in hand if c["rank"] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return any(c["rank"] == "A" for c in hand) and total <= 17


def is_natural(hand: list[dict]) -> bool:
    return len(hand) == 2 and hand_value(hand) == 21


def dealer_should_hit(hand: list[dict]) -> bool:
    total = hand_value(hand)
    if total < 17:
        return True
    if total == 17 and is_soft(hand):
        return False  # S17
    return False


def _truncate_half_to_player(amount: float) -> float:
    whole = int(amount)
    frac = amount - whole
    if abs(frac - 0.5) < 1e-9:
        return float(whole + 1)
    return round(amount, 2)


def play_out(bet: float, player: list[dict], dealer: list[dict], deck: list[dict]) -> dict:
    while len(deck) and dealer_should_hit(dealer):
        dealer.append(draw(deck))
    player_total = hand_value(player)
    dealer_total = hand_value(dealer)
    if player_total > 21:
        outcome = "bust"
        payout = 0.0
    elif is_natural(player) and not is_natural(dealer):
        outcome = "blackjack"
        payout = _truncate_half_to_player(bet * 2.5)
    elif dealer_total > 21 or player_total > dealer_total:
        outcome = "win"
        payout = bet * 2
    elif player_total == dealer_total:
        outcome = "push"
        payout = bet
    else:
        outcome = "lose"
        payout = 0.0
    return {
        "outcome": outcome,
        "payout": round(payout, 2),
        "player": player_total,
        "dealer": dealer_total,
    }


def natural_settle(bet: float, player: list[dict], dealer: list[dict]) -> dict:
    p_nat = is_natural(player)
    d_nat = is_natural(dealer)
    if p_nat and d_nat:
        return {"outcome": "push", "payout": round(bet, 2), "player": 21, "dealer": 21}
    if p_nat:
        return {"outcome": "blackjack", "payout": round(_truncate_half_to_player(bet * 2.5), 2), "player": 21, "dealer": hand_value(dealer)}
    return {"outcome": "lose", "payout": 0.0, "player": hand_value(player), "dealer": 21}
