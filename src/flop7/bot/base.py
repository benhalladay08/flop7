from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from flop7.core.enum.decisions import TargetEvent

if TYPE_CHECKING:
    from flop7.bot.knowledge import GameView, PlayerView


class AbstractBot(ABC):
    """
    Base class for bots. Subclasses must implement the hit_stay method
    and target_selector method, which a bot controller calls with read-only
    game-state views.
    """

    # True for bots that rely on perfect information only available in virtual games.
    virtual_only: bool = False

    @abstractmethod
    def hit_stay(self, view: GameView, player: PlayerView) -> bool:
        """Return True to hit, False to stay."""
        pass

    @abstractmethod
    def target_selector(
        self,
        view: GameView,
        event: TargetEvent,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        """Given the game state and event, select an eligible target."""
        pass
