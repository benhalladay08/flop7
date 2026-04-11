from abc import ABC, abstractmethod

from flop7.core.classes.player import Player
from flop7.core.enum.decisions import TargetEvent

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flop7.core.engine.engine import GameEngine

class AbstractBot(ABC):
    """
    Base class for bots. Subclasses must implement the hit_stay method
    and target_selector method, which the game engine will call during play.
    """

    virtual_only: bool = False  # Whether this bot can only be used in a virtual game (e.g. relies on perfect information)

    @abstractmethod
    def hit_stay(self, game: GameEngine, player: Player) -> bool:
        """Return True to hit, False to stay."""
        pass

    @abstractmethod
    def target_selector(
        self,
        game: GameEngine,
        event: TargetEvent,
        player: Player,
    ) -> Player:
        """Given the game state and event, select a target."""
        pass