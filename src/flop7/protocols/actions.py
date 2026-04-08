from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from flop7.classes.cards import Card
    from flop7.classes.player import Player
    from flop7.engine.base import GameEngine

class CardAction(Protocol):
    def __call__(self, game: GameEngine, player: Player, card: Card) -> bool:
        """
        Perform the action of a card on a player. This is where the logic
        for each card's effect will be implemented.
        """