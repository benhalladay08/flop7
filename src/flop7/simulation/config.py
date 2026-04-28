"""Configuration validation and sampling for simulation batches."""

from __future__ import annotations

import random


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
    """Sample a valid game configuration from the given ranges."""
    min_players, max_players = player_range
    sum_mins = sum(lo for lo, _ in bot_ranges.values())
    sum_maxes = sum(hi for _, hi in bot_ranges.values())

    effective_min = max(min_players, sum_mins)
    effective_max = min(max_players, sum_maxes)
    player_count = random.randint(effective_min, effective_max)

    counts = {name: lo for name, (lo, _) in bot_ranges.items()}
    remaining = player_count - sum_mins

    expandable = [name for name, (lo, hi) in bot_ranges.items() if hi > lo]
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
