from __future__ import annotations

from typing import TYPE_CHECKING, Generator, Protocol

if TYPE_CHECKING:
    from flop7.core.classes.cards import Card
    from flop7.core.classes.player import Player
    from flop7.core.engine.engine import GameEngine


class CardAction(Protocol):
    def __call__(
        self, game: GameEngine, player: Player, card: Card
    ) -> Generator:
        """Generator that performs a card's special action.

        Yields decision requests and notification events (same protocol
        as the engine's ``round()`` generator).  The engine delegates to
        this via ``yield from card.special_action(game, player, card)``.
        """