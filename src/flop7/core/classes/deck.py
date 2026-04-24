import random

from flop7.core.classes.cards import Card, ALL_CARDS


class Deck:
    """
    Holds the draw pile and discard pile. In virtual mode, ``draw_pile[0]``
    is the next card to be drawn.
    """

    def __init__(self, cards: list[Card] | None = None):
        self.draw_pile: list[Card] = []
        self.discard_pile: list[Card] = []

        if cards is None:
            self.draw_pile = self._build_card_list()
            self.shuffle()
        else:
            self.draw_pile = list(cards)

    def _build_card_list(self) -> list[Card]:
        """Expand ALL_CARDS into a flat list, respecting each card's num_in_deck."""
        cards = []
        for card in ALL_CARDS:
            cards.extend([card] * card.num_in_deck)
        return cards

    def deal(self) -> Card:
        """Draw a card and reshuffle discards if this was the last draw card."""
        if not self.draw_pile:
            raise IndexError("Cannot deal from an empty draw pile.")

        card = self.draw_pile.pop(0)
        if not self.draw_pile:
            self.reshuffle()
        return card

    def discard(self, cards: list[Card]) -> None:
        """Add cards to the discard pile."""
        self.discard_pile.extend(cards)

    def shuffle(self) -> None:
        """Shuffle the draw pile."""
        random.shuffle(self.draw_pile)

    def reshuffle(self) -> None:
        """Shuffle the discard pile back into the draw pile."""
        self.draw_pile.extend(self.discard_pile)
        self.discard_pile.clear()
        self.shuffle()
