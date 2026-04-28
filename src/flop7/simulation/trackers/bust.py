"""Tracker for bust events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flop7.core.engine.requests import PlayerBustedEvent

if TYPE_CHECKING:
    from flop7.core.engine.engine import GameEngine


class BustTracker:
    """Counts total busts across all games."""

    label = "Busts"

    def __init__(self) -> None:
        self._count: int = 0
        self._games: int = 0

    def on_event(self, event: object) -> None:
        if isinstance(event, PlayerBustedEvent):
            self._count += 1

    def on_game_over(self, engine: GameEngine) -> None:
        self._games += 1

    def format_results(self) -> list[str]:
        per_game = self._count / self._games if self._games else 0
        return [
            f"Total: {self._count:,}",
            f"Avg per game: {per_game:.1f}",
        ]
