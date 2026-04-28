# Building and testing bots

Flop 7 is built around the idea that **anyone can plug in a new Flip 7 bot** and benchmark it against existing models. This guide walks through the full path: how bots see the game, how to write one, how to register it, and how to test and benchmark it.

> **Project rule:** never reimplement engine logic inside a bot. Bots receive read-only views and return decisions — the engine handles all state mutation. If you find yourself simulating a draw or scoring a hand, reach for `bot/utils.py` or extend the engine instead.

## Concepts

### The bot contract

Every bot subclasses [`AbstractBot`](../../src/flop7/bot/base.py) and implements two methods:

```python
class AbstractBot(ABC):
    virtual_only: bool = False

    @abstractmethod
    def hit_stay(self, view: GameView, player: PlayerView) -> bool:
        """Return True to hit, False to stay."""

    @abstractmethod
    def target_selector(
        self,
        view: GameView,
        event: TargetEvent,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        """Pick one eligible target for an action card."""
```

The engine yields a `HitStayRequest` whenever a player must decide to draw or bank, and a `TargetRequest` (with a `TargetEvent` of `FLIP_THREE`, `FREEZE`, or `SECOND_CHANCE`) when an action card needs a target. Your bot is the function that answers those requests.

### Read-only views

Bots never see the live `GameEngine`. They receive frozen snapshots from [`bot/knowledge.py`](../../src/flop7/bot/knowledge.py):

| View          | What you get                                                              |
| ------------- | ------------------------------------------------------------------------- |
| `GameView`    | All players, active indexes, round number, dealer, deck, win conditions  |
| `PlayerView`  | A player's hand, banked score, active score, busted/active flags          |
| `DeckView`    | Discard pile, remaining count, and the **draw order** in virtual mode     |

In **virtual** games, `DeckView.draw_order` reveals the full upcoming card sequence — that's how `OmniscientBot` peeks ahead. In **real** games (live scorekeeping), `draw_order` is an empty tuple and `remaining_count` is `None`. Bots that depend on hidden information must set `virtual_only = True` so the registry refuses to load them in real games.

### The registry

[`bot/registry.py`](../../src/flop7/bot/registry.py) is the central lookup the app and simulator use to instantiate bots by name:

```python
class Bot:
    available_bots: dict[str, type[AbstractBot]] = {
        "Basic": BasicBot,
        "Omniscient": OmniscientBot,
    }

    @classmethod
    def create(cls, model: str, virtual: bool = False, **params) -> AbstractBot:
        ...
```

Adding your bot is a one-line edit (see below).

### Helpers — don't duplicate

Before writing logic, check what already exists:

- [`bot/utils.py`](../../src/flop7/bot/utils.py) — shared helpers like `overall_score(player_view)`
- [`bot/knowledge.py`](../../src/flop7/bot/knowledge.py) — `PlayerView.has_card`, `PlayerView.overall_score`, `DeckView.next_card`, `GameView.active_players`, etc.

If your bot needs a stat that two models would compute the same way, add it to `bot/utils.py` rather than duplicating it.

## Walkthrough — building a new bot

We'll build `GreedyBot`: hits whenever the next card in the draw pile (in virtual mode) wouldn't bust it, and otherwise stays. Targets the leader on Freeze. This is a small bot but it exercises every part of the contract.

### 1. Create the bot module

Create `src/flop7/bot/models/greedy.py`:

```python
"""GreedyBot — hits when the next visible card is safe."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from flop7.bot.base import AbstractBot
from flop7.bot.utils import overall_score
from flop7.core.enum.decisions import TargetEvent

if TYPE_CHECKING:
    from flop7.bot.knowledge import GameView, PlayerView


class GreedyBot(AbstractBot):
    """Peeks at the next card; hits if it wouldn't bust."""

    virtual_only = True  # depends on draw_order

    def hit_stay(self, view: GameView, player: PlayerView) -> bool:
        next_card = view.deck.next_card
        if next_card is None or not next_card.bustable:
            return True
        return not player.has_card(next_card)

    def target_selector(
        self,
        view: GameView,
        event: TargetEvent,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        if event is TargetEvent.FREEZE:
            others = [p for p in eligible if p.index != player.index] or list(eligible)
            best = max(overall_score(p) for p in others)
            return random.choice([p for p in others if overall_score(p) == best])
        # Flip Three / Second Chance: target self if eligible, else random
        if player in eligible:
            return player
        return random.choice(eligible)
```

Two things to notice:

- `virtual_only = True` because `view.deck.next_card` is `None` in real mode. The registry will refuse to instantiate this bot in a real game.
- We use `overall_score` from `bot/utils.py` instead of writing our own scoring helper.

### 2. Register it

Edit [`src/flop7/bot/registry.py`](../../src/flop7/bot/registry.py):

```python
from flop7.bot.models.greedy import GreedyBot

class Bot:
    available_bots: dict[str, type[AbstractBot]] = {
        "Basic": BasicBot,
        "Omniscient": OmniscientBot,
        "Greedy": GreedyBot,
    }
```

That's the only registration step. The TUI setup screen and the simulation runner both pull from `Bot.available_bots`, so your bot is now selectable everywhere.

### 3. (Optional) Constructor parameters

If your bot has tunable knobs (a hit threshold, a randomness factor), accept them in `__init__`:

```python
class GreedyBot(AbstractBot):
    def __init__(self, freeze_aggression: float = 1.0) -> None:
        self.freeze_aggression = freeze_aggression
```

`Bot.create("Greedy", virtual=True, freeze_aggression=0.7)` forwards keyword args through `**params`.

## Testing your bot

### Unit tests

Mirror [`tests/bot/models/test_basic.py`](../../tests/bot/models/test_basic.py) — it's the canonical pattern. Build a `GameView` with `build_game_view(engine)` and assert the bot's decisions:

```python
# tests/bot/models/test_greedy.py
from flop7.bot.knowledge import build_game_view
from flop7.bot.models.greedy import GreedyBot
from flop7.core.classes.cards import FIVE, SEVEN, TWO

from tests.conftest import make_engine


def test_hits_when_next_card_is_safe():
    engine = make_engine(cards=[FIVE], n_players=3)
    engine.players[0].hand = [TWO, SEVEN]
    view = build_game_view(engine)
    assert GreedyBot().hit_stay(view, view.players[0]) is True


def test_stays_when_next_card_would_bust():
    engine = make_engine(cards=[SEVEN], n_players=3)
    engine.players[0].hand = [TWO, SEVEN]
    view = build_game_view(engine)
    assert GreedyBot().hit_stay(view, view.players[0]) is False
```

`make_engine` from [`tests/conftest.py`](../../tests/conftest.py) is the workhorse — it builds a deterministic deck and a real `GameEngine` so `build_game_view` produces the right snapshot. Use it for every bot test.

### End-to-end games

To play a single full game with your bot and inspect the result, use [`simulation/runner.py`](../../src/flop7/simulation/runner.py):

```python
from flop7.simulation.runner import run_game
from flop7.simulation.trackers import default_trackers

trackers = default_trackers()
engine = run_game({"Greedy": 3}, trackers=trackers)

print(f"Winner: {engine.winner.name} with {engine.winner.score}")
for tracker in trackers:
    print(tracker.label, tracker.format_results())
```

`run_game` accepts a `{bot_name: count}` dict, instantiates each seat through the registry, and plays one game start to finish. It returns the finished `GameEngine` so you can inspect `engine.winner`, `engine.round_number`, etc.

### Benchmarking against baselines

The point of building a bot is to see if it's actually better. Mix it with `BasicBot` and `OmniscientBot` and run a batch:

```python
from collections import Counter
from flop7.simulation.runner import run_game

wins: Counter[str] = Counter()
for _ in range(1000):
    engine = run_game({"Greedy": 1, "Basic": 1, "Omniscient": 1})
    wins[engine.winner.name.rsplit(" ", 1)[0]] += 1

print(wins)
```

For richer output (win rates per bot type, average game length, average winning score), use [`SimulationResults`](../../src/flop7/simulation/results.py):

```python
from flop7.simulation.results import SimulationResults
from flop7.simulation.runner import run_game

config = {"Greedy": 1, "Basic": 1, "Omniscient": 1}
results = SimulationResults()
for _ in range(1000):
    engine = run_game(config)
    results.record(config, engine)

for bot in config:
    print(f"{bot}: win rate {results.win_rate(bot):.1f}%")
print(f"Avg game length: {results.avg_game_length:.1f} rounds")
```

### Custom statistics

If you want to measure something the default trackers don't surface — average bust round, frequency of self-targeted Flip Three, win rate when holding a Second Chance at round end, etc. — write a tracker. See [trackers.md](trackers.md).

## Virtual-only bots

Set `virtual_only = True` when your bot reads any field that's only populated in virtual games:

- `view.deck.draw_order` (always empty in real mode)
- `view.deck.remaining_count` (always `None` in real mode)
- `view.deck.next_card` (computed from `draw_order`)

`Bot.create("YourBot", virtual=False)` will raise `ValueError` for virtual-only bots, preventing them from being used at the table where they'd cheat by definition.

## Checklist before opening a PR

- [ ] Bot subclasses `AbstractBot` and implements both abstract methods
- [ ] `virtual_only` is set correctly
- [ ] Bot is registered in `Bot.available_bots`
- [ ] Unit tests cover hit/stay and each `TargetEvent` branch
- [ ] Bot uses helpers from `bot/utils.py` and `bot/knowledge.py` instead of recomputing state
- [ ] No engine internals (`game.deck.deal()`, `player.score = ...`) called from the bot
- [ ] `pytest` passes
