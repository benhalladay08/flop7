from typing import Protocol

from flop7.core.classes.cards import Card

class DrawProtocol(Protocol):
    def __call__(self, cards: list[Card]) -> Card:
        """
        Draw a card from a given list of cards.
        """