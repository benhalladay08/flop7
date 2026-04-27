"""Simulation event trackers.

Each tracker observes the stream of events yielded by ``GameEngine.round()``
(via ``play(listeners=...)``), accumulates statistics across games, and
formats results for display.

To add a new tracker, implement the ``SimTracker`` protocol and add an
instance to the ``DEFAULT_TRACKERS`` list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from flop7.core.engine.requests import (
    Flip7Event,
    FreezeEvent,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
)

if TYPE_CHECKING:
    from flop7.core.engine.engine import GameEngine


@runtime_checkable
class SimTracker(Protocol):
    """Protocol for modular simulation event trackers."""

    label: str

    def on_event(self, event: object) -> None:
        """Called for every request/event yielded by the engine generator."""
        ...

    def on_game_over(self, engine: GameEngine) -> None:
        """Called once after each completed game."""
        ...

    def format_results(self) -> list[str]:
        """Return formatted result lines for the results panel."""
        ...


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


class OpeningFreezeTracker:
    """Counts players frozen during the opening deal (before any hit/stay)."""

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


def default_trackers() -> list[SimTracker]:
    """Create a fresh set of default trackers for a simulation run."""
    return [Flip7Tracker(), OpeningFreezeTracker(), BustTracker()]
