"""Base protocol for simulation event trackers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

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
