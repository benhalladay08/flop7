"""Tracker for Freeze actions during the opening deal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flop7.core.engine.requests import FreezeEvent, HitStayRequest, RoundOverEvent

if TYPE_CHECKING:
    from flop7.core.engine.engine import GameEngine


class OpeningFreezeTracker:
    """Counts players frozen during the opening deal before any hit/stay."""

    label = "Opening Deal Freezes"

    def __init__(self) -> None:
        self._count: int = 0
        self._games: int = 0
        self._in_opening: bool = True

    def on_event(self, event: object) -> None:
        if isinstance(event, HitStayRequest):
            self._in_opening = False
        elif isinstance(event, RoundOverEvent):
            self._in_opening = True
        elif isinstance(event, FreezeEvent) and self._in_opening:
            self._count += 1

    def on_game_over(self, engine: GameEngine) -> None:
        self._games += 1
        self._in_opening = True

    def format_results(self) -> list[str]:
        rate = self._count / self._games * 100 if self._games else 0
        return [
            f"Total: {self._count:,}",
            f"Rate: {rate:.1f} per 100 games",
        ]
