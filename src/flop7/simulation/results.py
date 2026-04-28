"""Aggregate statistics for batches of simulated games."""

from __future__ import annotations

from dataclasses import dataclass, field

from flop7.core.engine.engine import GameEngine
from flop7.simulation.trackers.base import SimTracker


@dataclass
class SimulationResults:
    """Accumulates statistics across a batch of simulated games."""

    total_games: int = 0
    wins_by_type: dict[str, int] = field(default_factory=dict)
    bot_entries_by_type: dict[str, int] = field(default_factory=dict)
    total_rounds: int = 0
    total_winning_scores: int = 0
    trackers: list[SimTracker] = field(default_factory=list)

    def record(self, bot_types: dict[str, int], engine: GameEngine) -> None:
        """Record the outcome of one completed game.

        *bot_types* maps bot-type name to the number of seats that bot type
        occupied in this game. The winner's type is derived from their name
        (``"Type i"`` format).
        """
        self.total_games += 1
        self.total_rounds += engine.round_number
        self.total_winning_scores += engine.winner.score

        for bot_type, count in bot_types.items():
            if count > 0:
                self.bot_entries_by_type[bot_type] = (
                    self.bot_entries_by_type.get(bot_type, 0) + count
                )

        winner_type = engine.winner.name.rsplit(" ", 1)[0]
        self.wins_by_type[winner_type] = self.wins_by_type.get(winner_type, 0) + 1

    @property
    def avg_game_length(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.total_rounds / self.total_games

    @property
    def avg_winning_score(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.total_winning_scores / self.total_games

    def win_rate(self, bot_type: str) -> float:
        entries = self.bot_entries_by_type.get(bot_type, 0)
        if entries == 0:
            return 0.0
        return self.wins_by_type.get(bot_type, 0) / entries * 100
