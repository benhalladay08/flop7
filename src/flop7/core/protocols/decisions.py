from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from flop7.core.classes.player import Player
from flop7.core.enum.decisions import TargetEvent

if TYPE_CHECKING:
    from flop7.core.classes.cards import Card
    from flop7.core.engine.engine import GameEngine


class CardProvider(Protocol):
    def __call__(self, game: GameEngine, player: Player) -> Card:
        """
        Return the next card drawn for a player.
        """


class HitStay(Protocol):
    def __call__(self, game: GameEngine, player: Player) -> bool:
        """
        Return True to hit, False to stay.
        """

class TargetSelector(Protocol):
    def __call__(
        self,
        game: GameEngine,
        event: TargetEvent,
        player: Player,
        eligible: list[Player],
    ) -> Player:
        """
        Return the target player for a given action event.
        """
