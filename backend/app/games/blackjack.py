import secrets

RANK_NAMES = {
    "A": "Ace", "K": "King", "Q": "Queen", "J": "Jack",
    "10": "10", "9": "9", "8": "8", "7": "7",
}


def new_deck() -> list[dict]:
    suits = ["♠", "♥", "♦", "♣"]
    ranks = ["A", "K", "Q", "J", "10", "9", "8", "7"]
    return [{"rank": r, "suit": s, "value": _value(r)} for r in ranks for s in suits]


def _value(rank: str) -> int:
    if rank == "A":
        return 11
    if rank in ("K", "Q", "J"):
        return 10
    return int(rank)


def hand_value(hand: list[dict]) -> int:
    total = sum(c["value"] for c in hand)
    aces = sum(1 for c in hand if c["rank"] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def play(bet: float, player_hand: list[dict], dealer_hand: list[dict], deck: list[dict]) -> dict:
    player_total = hand_value(player_hand)
    dealer_total = hand_value(dealer_hand)
    if player_total > 21:
        return {"outcome": "bust", "payout": 0.0, "player": player_total, "dealer": dealer_total}
    while dealer_total < 17:
        dealer_hand.append(deck.pop(0))
        dealer_total = hand_value(dealer_hand)
    if dealer_total > 21 or player_total > dealer_total:
        return {"outcome": "win", "payout": bet * 2, "player": player_total, "dealer": dealer_total}
    if player_total == dealer_total:
        return {"outcome": "push", "payout": bet, "player": player_total, "dealer": dealer_total}
    return {"outcome": "lose", "payout": 0.0, "player": player_total, "dealer": dealer_total}