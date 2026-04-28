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

We'll build `BiggestRoundTracker`: records the largest single-round score across all simulated games and which bot earned it.

### 1. Create the tracker module

Create `src/flop7/simulation/trackers/biggest_round.py`:

```python
"""Tracker for the largest single-round score in a simulation batch."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flop7.core.engine.requests import RoundOverEvent

if TYPE_CHECKING:
    from flop7.core.engine.engine import GameEngine


class BiggestRoundTracker:
    """Tracks the highest single-round score across all games."""

    label = "Biggest Round"

    def __init__(self) -> None:
        self._best_score: int = 0
        self._best_player: str = ""
        self._games: int = 0

    def on_event(self, event: object) -> None:
        if not isinstance(event, RoundOverEvent):
            return
        for player in event.players:
            if player.active_score > self._best_score:
                self._best_score = player.active_score
                self._best_player = player.name

    def on_game_over(self, engine: GameEngine) -> None:
        self._games += 1

    def format_results(self) -> list[str]:
        if self._best_score == 0:
            return ["No rounds recorded"]
        return [
            f"Score: {self._best_score}",
            f"By: {self._best_player}",
        ]
```

> Verify the exact field name on `RoundOverEvent` in `flop7/core/engine/requests.py` before relying on it — the example uses `event.players`, but match whatever the engine actually exposes.

### 2. (Optional) Add it to the default set

If your tracker should run on every default simulation, add it to [`simulation/trackers/__init__.py`](../../src/flop7/simulation/trackers/__init__.py):

```python
from flop7.simulation.trackers.biggest_round import BiggestRoundTracker

__all__ = [
    "BiggestRoundTracker",
    "BustTracker",
    "Flip7Tracker",
    "OpeningFreezeTracker",
    "SimTracker",
    "default_trackers",
]


def default_trackers() -> list[SimTracker]:
    return [Flip7Tracker(), BustTracker(), BiggestRoundTracker()]
```

If it's a one-off you'd rather opt into per simulation, skip this step and pass it explicitly to `run_game`.

### 3. Use it in a simulation

```python
from flop7.simulation.runner import run_game
from flop7.simulation.trackers.biggest_round import BiggestRoundTracker

tracker = BiggestRoundTracker()
for _ in range(500):
    run_game({"Basic": 3}, trackers=[tracker])

print(tracker.label)
for line in tracker.format_results():
    print("  " + line)
```

A tracker instance accumulates across every `run_game` call you pass it to — that's how `tests/simulation/test_runner.py::test_flip7_tracker_accumulates_across_games` works.

## Testing your tracker

Mirror [`tests/simulation/`](../../tests/simulation/). Two patterns work well:

**Direct event injection** — fastest, no engine needed:

```python
from flop7.core.engine.requests import RoundOverEvent
from flop7.simulation.trackers.biggest_round import BiggestRoundTracker


def test_records_highest_score():
    tracker = BiggestRoundTracker()
    tracker.on_event(RoundOverEvent(players=[
        FakePlayer(name="Basic 1", active_score=42),
        FakePlayer(name="Basic 2", active_score=18),
    ]))
    assert tracker.format_results() == ["Score: 42", "By: Basic 1"]
```

**End-to-end through `run_game`** — verifies the tracker really receives the events the engine emits:

```python
from flop7.simulation.runner import run_game
from flop7.simulation.trackers.biggest_round import BiggestRoundTracker


def test_accumulates_across_games():
    tracker = BiggestRoundTracker()
    for _ in range(5):
        run_game({"Basic": 3}, trackers=[tracker])
    assert tracker._games == 5
```

Add at least one of each. The first nails the logic, the second catches contract drift if `RoundOverEvent`'s shape ever changes.

## Project rule: don't recompute engine state

Trackers consume the event stream — they don't peek at engine internals or recompute scores. If the data you need isn't on an event yet, **add it to the event** rather than reaching into the engine from your tracker. That keeps the engine the single source of truth and makes trackers cheap and predictable.
