import random

from flop7.core.classes.cards import Card, ALL_CARDS
from flop7.core.protocols.draw import DrawProtocol


class Deck:
    """
    Base deck class. Holds the discard pile and knows how to build
    the full card list from ALL_CARDS. Subclasses handle the draw pile
    differently depending on whether the game is virtual or real.
    """

    def __init__(self, draw: DrawProtocol):
        self.draw = draw
        self.draw_pile: list[Card] = []
        self.discard_pile: list[Card] = []

        # Build the initial draw pile from ALL_CARDS
        self.draw_pile = self._build_card_list()
        self.shuffle()

    def _build_card_list(self) -> list[Card]:
        """Expand ALL_CARDS into a flat list, respecting each card's num_in_deck."""
        cards = []
        for card in ALL_CARDS:
            cards.extend([card] * card.num_in_deck)
        return cards
    
    def deal(self) -> Card:
        """Draw a card from the draw pile. Subclasses implement differently."""
        card = self.draw(self.draw_pile)
        self.draw_pile.remove(card)
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

