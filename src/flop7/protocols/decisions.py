from __future__ import annotations

from typing import Protocol

from flop7.classes.player import Player
from flop7.enum.decisions import TargetEvent

class HitStay(Protocol):
    def __call__(self, player: Player) -> bool:
        """
        Return True to hit, False to stay.
        """

class TargetSelector(Protocol):
    def __call__(self, event: TargetEvent, player: Player, players: list[Player]) -> Player:
        """
        Given a list of players, return the player to target.
        """