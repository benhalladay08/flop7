# Building simulation trackers

Trackers are how you collect statistics during all-bot batched games. Each tracker observes the engine's event stream, accumulates whatever it cares about, and reports the results when the simulation finishes. Examples: how often players bust, how often Flip 7 happens, win rate when a Second Chance was held into the final hit.

## The contract

A tracker is anything that satisfies the [`SimTracker`](../../src/flop7/simulation/trackers/base.py) `Protocol`:

```python
@runtime_checkable
class SimTracker(Protocol):
    label: str

    def on_event(self, event: object) -> None: ...
    def on_game_over(self, engine: GameEngine) -> None: ...
    def format_results(self) -> list[str]: ...
```

| Hook              | When it fires                                                            |
| ----------------- | ------------------------------------------------------------------------ |
| `on_event`        | Every request and event yielded by the engine generator                  |
| `on_game_over`    | Once after each completed game                                           |
| `format_results`  | Called by the simulation results panel; returns one line per item        |

`label` is the heading the TUI shows above your formatted lines.

You don't need to subclass anything — a plain class with these three methods and one attribute satisfies the protocol.

## What you can listen to

The engine yields a stream of typed requests and events from `flop7.core.engine.requests`. Common ones:

| Event / request          | Fires when…                                              |
| ------------------------ | -------------------------------------------------------- |
| `CardDrawRequest`        | Engine needs the next card                                |
| `CardDrawnEvent`         | A card was drawn for a player                             |
| `HitStayRequest`         | A player must choose to hit or stay                       |
| `TargetRequest`          | An action card needs a target                             |
| `Flip7Event`             | A player hit Flip 7                                       |
| `PlayerBustedEvent`      | A player busted                                           |
| `FreezeEvent`            | A Freeze was resolved                                     |
| `RoundOverEvent`         | A round ended                                             |

Use `isinstance(event, EventType)` inside `on_event` to filter. See the existing trackers for the canonical pattern.

## Walkthrough — building a new tracker

We'll build `HighScoreTracker`: records the highest final cumulative score earned by any winning bot across the simulation batch, and which bot type earned it.

This uses `on_game_over` (called once per game with the finished engine) rather than `on_event` — it's the natural choice when the data you want is already on the engine at game-end. Trackers that need to observe in-game state (busts, freezes, draws) use `on_event` instead.

### 1. Create the tracker module

Create `src/flop7/simulation/trackers/high_score.py`:

```python
"""Tracker for the highest winning score across a simulation batch."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flop7.core.engine.engine import GameEngine


class HighScoreTracker:
    """Tracks the highest winning final score across all games."""

    label = "High Score"

    def __init__(self) -> None:
        self._best_score: int = 0
        self._best_winner: str = ""
        self._games: int = 0

    def on_event(self, event: object) -> None:
        # No per-event data needed — see Flip7Tracker / BustTracker for that pattern.
        pass

    def on_game_over(self, engine: GameEngine) -> None:
        self._games += 1
        winner = engine.winner
        if winner is not None and winner.score > self._best_score:
            self._best_score = winner.score
            self._best_winner = winner.name

    def format_results(self) -> list[str]:
        if self._games == 0:
            return ["No games recorded"]
        return [
            f"Score: {self._best_score}",
            f"By: {self._best_winner}",
        ]
```

`engine.winner` is set when the engine flips `game_over = True` at the end of a winning round (see [`core/engine/engine.py`](../../src/flop7/core/engine/engine.py)). It's always populated by the time `on_game_over` fires, since `run_game` only returns after `engine.play()` finishes.

> If you instead want a tracker that listens to the event stream — e.g. counting busts or freezes — `BustTracker` and `Flip7Tracker` are the canonical templates. Filter inside `on_event` with `isinstance(event, PlayerBustedEvent)` or whichever event type you care about.

### 2. (Optional) Add it to the default set

If your tracker should run on every default simulation, add it to [`simulation/trackers/__init__.py`](../../src/flop7/simulation/trackers/__init__.py):

```python
from flop7.simulation.trackers.high_score import HighScoreTracker

__all__ = [
    "BustTracker",
    "Flip7Tracker",
    "HighScoreTracker",
    "OpeningFreezeTracker",
    "SimTracker",
    "default_trackers",
]


def default_trackers() -> list[SimTracker]:
    return [Flip7Tracker(), BustTracker(), HighScoreTracker()]
```

If it's a one-off you'd rather opt into per simulation, skip this step and pass it explicitly to `run_game`.

### 3. Use it in a simulation

```python
from flop7.simulation.runner import run_game
from flop7.simulation.trackers.high_score import HighScoreTracker

tracker = HighScoreTracker()
for _ in range(500):
    run_game({"Basic": 3}, trackers=[tracker])

print(tracker.label)
for line in tracker.format_results():
    print("  " + line)
```

A tracker instance accumulates across every `run_game` call you pass it to — that's how `tests/simulation/test_runner.py::test_flip7_tracker_accumulates_across_games` works.

## Testing your tracker

Mirror [`tests/simulation/`](../../tests/simulation/). Two patterns work well:

**Direct invocation with a stub engine** — fastest, no full game needed. Build a minimal engine-shaped object and call the tracker hook directly:

```python
from types import SimpleNamespace

from flop7.simulation.trackers.high_score import HighScoreTracker


def test_records_highest_winning_score():
    tracker = HighScoreTracker()

    tracker.on_game_over(SimpleNamespace(
        winner=SimpleNamespace(name="Basic 1", score=210),
    ))
    tracker.on_game_over(SimpleNamespace(
        winner=SimpleNamespace(name="Basic 2", score=242),
    ))
    tracker.on_game_over(SimpleNamespace(
        winner=SimpleNamespace(name="Basic 3", score=205),
    ))

    assert tracker.format_results() == ["Score: 242", "By: Basic 2"]
```

For event-based trackers, build the relevant event with `Player` instances directly (see `tests/bot/models/test_basic.py` for the pattern).

**End-to-end through `run_game`** — verifies the tracker really receives the engine output:

```python
from flop7.simulation.runner import run_game
from flop7.simulation.trackers.high_score import HighScoreTracker


def test_accumulates_across_games():
    tracker = HighScoreTracker()
    for _ in range(5):
        run_game({"Basic": 3}, trackers=[tracker])
    assert tracker._games == 5
    assert tracker._best_score >= 200
```

Add at least one of each. The first nails the logic; the second catches contract drift if engine fields you depend on ever change.

## Project rule: don't recompute engine state

Trackers consume the event stream — they don't peek at engine internals or recompute scores. If the data you need isn't on an event yet, **add it to the event** rather than reaching into the engine from your tracker. That keeps the engine the single source of truth and makes trackers cheap and predictable.
