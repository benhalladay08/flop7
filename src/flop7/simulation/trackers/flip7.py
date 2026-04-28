"""Tracker for Flip 7 achievements."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flop7.core.engine.requests import Flip7Event

if TYPE_CHECKING:
    from flop7.core.engine.engine import GameEngine


class Flip7Tracker:
    """Counts how many Flip 7 achievements occur across all games."""

    label = "Flip 7s"

    def __init__(self) -> None:
        self._count: int = 0
        self._games: int = 0

    def on_event(self, event: object) -> None:
        if isinstance(event, Flip7Event):
            self._count += 1

    def on_game_over(self, engine: GameEngine) -> None:
        self._games += 1

    def format_results(self) -> list[str]:
        rate = self._count / self._games * 100 if self._games else 0
        return [
            f"Total: {self._count:,}",
            f"Rate: {rate:.1f} per 100 games",
        ]
