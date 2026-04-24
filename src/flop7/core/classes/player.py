from flop7.core.classes.cards import Card


class Player:
    """
    Holds all state for a single player across the game.
    Pure state object — no I/O, no strategy logic.
    """

    def __init__(self, name: str):
        self.name = name
        self.hand: list[Card] = []
        self.score: int = 0
        self.is_active: bool = True  # False if player has stayed or frozen
        self.busted: bool = False  # True if player busted this round

    @property
    def active_score(self) -> int:
        """Calculate the player's current score based on their hand."""
        sorted_cards = sorted(self.hand, key=lambda c: c.score_priority)
        score = 0
        for card in sorted_cards:
            if card.score_modifier:
                score = card.score_modifier(score)
            else:
                score += card.points
        return score

    def has_card(self, card: Card) -> bool:
        """Check if the player already has a card with the same name."""
        return any(c.name == card.name for c in self.hand)
    