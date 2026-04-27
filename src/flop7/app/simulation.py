"""Simulation engine: run batches of all-bot games and aggregate results."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from flop7.bot.base import AbstractBot
from flop7.bot.controller import BotController
from flop7.bot.registry import Bot
from flop7.core.classes.deck import Deck
from flop7.core.classes.player import Player
from flop7.core.engine.engine import GameEngine


@dataclass
class SimulationResults:
    """Accumulates statistics across a batch of simulated games."""

    total_games: int = 0
    wins_by_type: dict[str, int] = field(default_factory=dict)
    games_by_type: dict[str, int] = field(default_factory=dict)
    total_rounds: int = 0
    total_winning_scores: int = 0
    trackers: list = field(default_factory=list)

    def record(self, bot_types: dict[str, int], engine: GameEngine) -> None:
        """Record the outcome of one completed game.

        *bot_types* maps bot-type name -> count used in this game.
        The winner's type is derived from their name (``"Type i"`` format).
        """
        self.total_games += 1
        self.total_rounds += engine.round_number
        self.total_winning_scores += engine.winner.score

        for bot_type, count in bot_types.items():
            if count > 0:
                self.games_by_type[bot_type] = (
                    self.games_by_type.get(bot_type, 0) + count
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

    def win_pct(self, bot_type: str) -> float:
        total_wins = sum(self.wins_by_type.values())
        if total_wins == 0:
            return 0.0
        return self.wins_by_type.get(bot_type, 0) / total_wins * 100


def validate_sim_config(
    player_range: tuple[int, int],
    bot_ranges: dict[str, tuple[int, int]],
) -> str | None:
    """Return an error message if the configuration is infeasible, else None."""
    min_players, max_players = player_range
    sum_mins = sum(lo for lo, _ in bot_ranges.values())
    sum_maxes = sum(hi for _, hi in bot_ranges.values())

    if sum_maxes < min_players:
        return (
            f"Bot maximums sum to {sum_maxes}, which is less than the "
            f"minimum player count ({min_players}). Increase bot ranges "
            f"or lower the minimum player count."
        )
    if sum_mins > max_players:
        return (
            f"Bot minimums sum to {sum_mins}, which exceeds the maximum "
            f"player count ({max_players}). Decrease bot minimums or "
            f"raise the maximum player count."
        )
    return None


def sample_game_config(
    player_range: tuple[int, int],
    bot_ranges: dict[str, tuple[int, int]],
) -> dict[str, int]:
    """Sample a valid game configuration from the given ranges.

    Returns a dict mapping bot-type name -> count, summing to a value
    within *player_range*.
    """
    min_players, max_players = player_range
    sum_mins = sum(lo for lo, _ in bot_ranges.values())
    sum_maxes = sum(hi for _, hi in bot_ranges.values())

    effective_min = max(min_players, sum_mins)
    effective_max = min(max_players, sum_maxes)
    player_count = random.randint(effective_min, effective_max)

    counts = {name: lo for name, (lo, _) in bot_ranges.items()}
    remaining = player_count - sum_mins

    expandable = [
        name for name, (lo, hi) in bot_ranges.items() if hi > lo
    ]
    random.shuffle(expandable)

    while remaining > 0 and expandable:
        next_round = []
        for name in expandable:
            if remaining <= 0:
                break
            _, hi = bot_ranges[name]
            room = hi - counts[name]
            if room > 0:
                add = random.randint(1, min(room, remaining))
                counts[name] += add
                remaining -= add
                if counts[name] < hi:
                    next_round.append(name)
        expandable = next_round
        random.shuffle(expandable)

    return counts


def run_game(
    bot_types: dict[str, int],
    trackers: list | None = None,
) -> GameEngine:
    """Create and play a single all-bot game, returning the finished engine."""
    players: list[Player] = []
    bots_by_index: dict[int, AbstractBot] = {}

    for bot_type, count in bot_types.items():
        for i in range(count):
            idx = len(players)
            players.append(Player(f"{bot_type} {i + 1}"))
            bots_by_index[idx] = Bot.create(bot_type, virtual=True)

    controller = BotController(bots_by_index)
    deck = Deck()

    engine = GameEngine(
        deck=deck,
        players=players,
        card_provider=lambda game, _player: game.deck.deal(),
        hit_stay_decider=controller.hit_stay,
        target_selector=controller.target_selector,
    )

    _trackers = trackers or ()
    listeners = [t.on_event for t in _trackers]
    engine.play(listeners=listeners)
    for t in _trackers:
        t.on_game_over(engine)

    return engine
