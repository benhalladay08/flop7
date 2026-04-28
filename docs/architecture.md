# Architecture

This is the comprehensive architectural reference for Flop 7 — what each layer does, how they fit together, and the contracts that decouple them. For game rules, see [rules.md](rules.md). For step-by-step contributor guides, see the [guides/](guides/) directory.

## Contents

- [System overview](#system-overview)
- [Repo layout](#repo-layout)
- [Core layer](#core-layer)
- [Bot layer](#bot-layer)
- [App layer](#app-layer)
- [Simulation layer](#simulation-layer)
- [TUI layer](#tui-layer)
- [Cross-cutting contracts](#cross-cutting-contracts)
- [End-to-end flow](#end-to-end-flow)

---

## System overview

Flop 7 is split into five layers, each with a single responsibility and a narrow interface to its neighbors:

| Layer        | Owns                                                                  | Depends on            |
| ------------ | --------------------------------------------------------------------- | --------------------- |
| `core`       | Game state, card resolution, scoring, round lifecycle, request/event types | (nothing)        |
| `bot`        | Bot decision logic and read-only views of game state                  | `core`                |
| `simulation` | All-bot batched runs and tracker aggregation                          | `core`, `bot`         |
| `app`        | Orchestration: routing user input through node-based flows            | `core`, `bot`, `tui`  |
| `tui`        | urwid screens, widgets, and the persistent command bar                | (no app/core)         |

The engine is **generator-driven**. It yields typed requests (`CardDrawRequest`, `HitStayRequest`, `TargetRequest`) and notification events (`CardDrawnEvent`, `Flip7Event`, `FreezeEvent`, etc.), expecting the driver — bot controller, app node, or test harness — to send the response back. This decoupling is what lets the same engine power live scorekeeping, virtual play against bots, and headless simulation batches without conditionals on the calling context.

### Design principles

1. **Engine is the source of truth.** Nothing outside `core/` mutates game state. Bots and trackers consume the engine's event stream; they don't re-derive scores or simulate draws.
2. **Read-only views for outsiders.** Bots receive frozen `GameView`/`PlayerView`/`DeckView` snapshots from `bot/knowledge.py`, never the live `GameEngine`.
3. **Protocols, not base classes** for engine dependencies. The engine is parameterized by `Protocol` callables (`HitStay`, `TargetSelector`, `CardProvider`), so any object satisfying the structural type works.
4. **Extend through hooks, never duplicate.** New behaviors (bots, trackers, action cards) plug into the existing event/request stream — they don't reimplement engine logic.

---

## Repo layout

```text
src/flop7/
├── __main__.py               # Entry point for `python -m flop7`
├── cli.py                    # Entry point for the `flop7` CLI script
├── core/                     # Game engine — pure, no UI or strategy deps
│   ├── classes/              # Card, Deck, Player
│   ├── engine/               # GameEngine, action handlers, request/event types
│   ├── enum/                 # TargetEvent enum (and a placeholder GameEvent)
│   └── protocols/            # CardProvider, HitStay, TargetSelector, CardAction, ScoreModifier
├── bot/                      # Strategy layer — bots see read-only views
│   ├── base.py               # AbstractBot contract
│   ├── controller.py         # Adapter: engine requests → bot decisions
│   ├── knowledge.py          # Frozen GameView / PlayerView / DeckView snapshots
│   ├── registry.py           # Bot.available_bots + Bot.create() factory
│   ├── utils.py              # Shared helpers (overall_score, ...)
│   └── models/               # BasicBot, OmniscientBot, ...
├── simulation/               # All-bot batched runs
│   ├── runner.py             # run_game() — plays one full game
│   ├── config.py             # validate_sim_config / sample_game_config
│   ├── results.py            # SimulationResults aggregator
│   └── trackers/             # SimTracker protocol + built-in trackers
├── app/                      # Orchestration: state machine of nodes
│   ├── orchestrator.py       # App — owns the TUI and routes input through nodes
│   ├── prompt.py             # Prompt dataclass: instruction + validator + auto-advance
│   └── nodes/                # HomeNode, GameModeNode, GameRoundNode, SimRunNode, ...
└── tui/                      # urwid presentation
    ├── app.py                # TUIApp — main loop, screen swapping, command bar
    ├── screens/              # HomeScreen, GameScreen, SimulateScreen
    ├── components/           # Card art (text-rendered cards)
    └── widgets/              # CommandBar, PlayerList, CardDetail
```

---

## Core layer

The game logic lives in `src/flop7/core/`. It has zero awareness of the TUI or any bot strategy — it could be driven by a unit test, a controller, or any other generator driver.

### `core/classes/` — Data layer

#### `Card` (`cards.py`)

`@dataclass` representing a single card definition. Fields: `name`, `abbrv`, `num_in_deck`, `points`, `bustable`, plus an optional `score_modifier` callback and `score_priority` for ordering modifier application. All 22 unique card types are module-level constants (`ZERO`, `FLIP_THREE`, `PLUS_TWO`, `TIMES_TWO`, ...) and are collected into `ALL_CARDS` and `CARD_MAP` for lookup.

#### `Deck` (`deck.py`)

Owns the draw pile and discard pile. On default construction it expands `ALL_CARDS` into the 94-card list (each card repeated `num_in_deck` times) and shuffles. Tests and simulations can pass an explicit ordered `cards=` list to bypass shuffling.

| Method        | Behavior                                                                   |
| ------------- | -------------------------------------------------------------------------- |
| `deal()`      | Pops `draw_pile[0]`. If the pile is now empty, calls `reshuffle()`.        |
| `discard(cs)` | Appends to `discard_pile`.                                                 |
| `shuffle()`   | Shuffles the draw pile in place.                                           |
| `reshuffle()` | Moves the discard pile back into the draw pile and shuffles.               |

#### `Player` (`player.py`)

Pure state container — no I/O, no strategy. Tracks `name`, `hand`, cumulative `score`, `is_active` (False when stayed or frozen), and `busted` (True if the player busted this round).

The `active_score` computed property handles the layered scoring rule: cards are sorted by `score_priority`, then folded — modifier cards (×2, then flat bonuses) apply via their `score_modifier` callback; number cards add their `points`.

`has_card(card)` matches by `name`, used by the engine for duplicate-detection (busts) and Second Chance lookups.

### `core/engine/` — Game loop

#### `GameEngine` (`engine.py`)

The engine class owns the round lifecycle. It's constructed with a `Deck`, a player list (≥ 3), three injected callables, and two flags:

```python
GameEngine(
    deck=deck,
    players=players,
    card_provider=...,        # CardProvider — produces the next drawn card
    hit_stay_decider=...,     # HitStay — answers HitStayRequest
    target_selector=...,      # TargetSelector — answers TargetRequest
    real_mode=False,          # True for live scorekeeping (no draw-order reveal)
    dealer_index=0,
)
```

Class-level constants encode the rule numbers:

| Constant       | Value | Meaning                                          |
| -------------- | ----- | ------------------------------------------------ |
| `WIN_SCORE`    | 200   | First to this many points (after a round) wins.  |
| `FLIP_7_BONUS` | 15    | Bonus added when a player hits Flip 7.           |
| `FLIP_7_COUNT` | 7     | Number of unique bustable cards for Flip 7.      |

The engine exposes two driving entry points:

- **`play(listeners=None)`** — auto-drives `round()` to completion. Each listener is called with every yielded request/event, in order — this is how trackers observe the stream.
- **`round()`** — a generator producing one round of play. Callers `.send()` the response to the most recent request; events expect `None` back.

Round behavior:

1. **Opening deal.** Each active player (in seat order from the dealer's left) is dealt exactly one card. Action cards resolve immediately as they're dealt. Players frozen mid-deal are skipped.
2. **Hit/stay loop.** While at least one player is active and no Flip 7 has fired, each active player is offered hit/stay. Players with empty hands are forced to draw instead of being asked.
3. **Hit resolution** (`_hit`):
   - The pre-hit hook (`_pre_hit`) checks Second Chance absorption.
   - If the card has an action handler (Flip Three, Freeze, Second Chance), it yields from that handler.
   - Otherwise, duplicate-number cards bust the player (`PlayerBustedEvent`); a 7th unique bustable card triggers Flip 7 (`Flip7Event`) and ends the round for everyone.
4. **Scoring & cleanup.** Non-busted players' `active_score` is folded into `score`; the Flip 7 player gets `FLIP_7_BONUS`. Hands are discarded, players reset to active, dealer rotates left, and `round_number` increments.
5. **Win check.** If anyone is at or above `WIN_SCORE`, `game_over = True` and `winner = max(players, key=score)`.
6. Yields a final `RoundOverEvent(round_number=...)`.

#### Action handlers (`actions.py`)

Module-level generator functions implementing the three action cards:

| Handler         | Behavior                                                                   |
| --------------- | -------------------------------------------------------------------------- |
| `flip_three`    | Yields `TargetRequest(FLIP_THREE)`, then forces 3 sequential draws on the target. Second Chance resolves immediately; nested Flip Three / Freeze are deferred until the 3 draws complete (and skipped if the target busted). |
| `freeze`        | Yields `TargetRequest(FREEZE)`, then sets target inactive and emits `FreezeEvent`. |
| `second_chance` | Drawer keeps the shield unless they already have one — then yields `TargetRequest(SECOND_CHANCE)` to pass it to an active opponent without one (or discards if no eligible target). |

`_validate_target` runs after every `TargetRequest` to fail fast if a driver returns an ineligible or inactive target.

`get_action(card)` resolves a `Card` to its handler via the card's `abbrv` (no mutation of the card constants).

#### Request and event types (`requests.py`)

All engine yields are typed `@dataclass`es. Decision requests block the generator until `.send(value)` provides a response; events are notifications that expect `None` back.

| Type                       | Kind     | Driver responds with                          |
| -------------------------- | -------- | --------------------------------------------- |
| `CardDrawRequest`          | request  | `Card` (the drawn card)                       |
| `HitStayRequest`           | request  | `bool` (True = hit)                           |
| `TargetRequest`            | request  | `Player` (the chosen target)                  |
| `CardDrawnEvent`           | event    | —                                             |
| `PlayerBustedEvent`        | event    | —                                             |
| `Flip7Event`               | event    | —                                             |
| `FreezeEvent`              | event    | —                                             |
| `SecondChanceEvent`        | event    | —                                             |
| `FlipThreeStartEvent`      | event    | —                                             |
| `FlipThreeResolvedEvent`   | event    | —                                             |
| `RoundOverEvent`           | event    | —                                             |

### `core/enum/`

- `TargetEvent` (`decisions.py`) — `FLIP_THREE`, `FREEZE`, `SECOND_CHANCE`. Carried on `TargetRequest` so target selectors know why they're being asked.
- `GameEvent` (`event.py`) — placeholder for future UI/log message events.

### `core/protocols/` — Dependency contracts

The engine's external dependencies are expressed as `typing.Protocol` classes, enabling structural (duck) typing.

| Protocol         | Module                | Signature                                                               |
| ---------------- | --------------------- | ----------------------------------------------------------------------- |
| `CardProvider`   | `decisions.py`        | `(game, player) -> Card`                                                |
| `HitStay`        | `decisions.py`        | `(game, player) -> bool`                                                |
| `TargetSelector` | `decisions.py`        | `(game, event, player, eligible) -> Player`                             |
| `CardAction`     | `actions.py`          | `(game, player, card) -> Generator` — action cards' special effects    |
| `ScoreModifier`  | `modifier.py`         | `(current_score: int) -> int` — attached to `Card.score_modifier`       |

This is what lets a unit test drive the engine with stub callables, the bot controller drive it with `BotController.hit_stay`, and the app drive it through async node-based flows — all without the engine knowing.

---

## Bot layer

The bot layer is a strategy boundary on top of `core`. Bots receive immutable snapshots, return decisions, and never mutate state.

### `AbstractBot` (`bot/base.py`)

```python
class AbstractBot(ABC):
    virtual_only: bool = False

    @abstractmethod
    def hit_stay(self, view: GameView, player: PlayerView) -> bool: ...

    @abstractmethod
    def target_selector(
        self, view: GameView, event: TargetEvent,
        player: PlayerView, eligible: tuple[PlayerView, ...],
    ) -> PlayerView: ...
```

`virtual_only = True` marks bots that depend on hidden information (the full draw order, remaining count). The registry refuses to instantiate them in real-mode games.

### Read-only views (`bot/knowledge.py`)

| View         | Highlights                                                                              |
| ------------ | --------------------------------------------------------------------------------------- |
| `PlayerView` | `index`, `name`, `hand`, `score`, `active_score`, `is_active`, `busted`, `overall_score`, `has_card` |
| `DeckView`   | `draw_order` (full sequence in virtual mode, empty tuple in real mode), `remaining_count` (int / `None`), `discard_pile`, `next_card` |
| `GameView`   | All `players`, `active_player_indexes`, `round_number`, `dealer_index`, `real_mode`, `game_over`, `winner_index`, `win_score`, `flip_7_bonus`, `flip_7_count`, `deck` |

`build_game_view(engine)` is the single function that produces a `GameView` from a live engine. It hides `draw_order` automatically when `engine.real_mode` is True.

### `BotController` (`bot/controller.py`)

Adapter between the engine's `Player`-based callables and the bot's `PlayerView`-based interface. For each request:

1. Look up the bot for the source player's index.
2. Build a fresh `GameView` from the engine.
3. Call the bot, forwarding `view.players[index]` and `view`-mapped `eligible`.
4. Validate the bot's response; if a target is ineligible, raise.
5. Map the chosen `PlayerView` back to the engine's `Player` by index.

`BotController.hit_stay` and `BotController.target_selector` are the callables passed to `GameEngine` in simulation runs (and in mixed virtual games where some seats are bot-controlled).

### Registry (`bot/registry.py`)

`Bot.available_bots` is the `dict[str, type[AbstractBot]]` lookup the TUI setup screens and `simulation/runner.py` both consult. `Bot.create(name, virtual=False, **params)` instantiates a bot, enforces `virtual_only`, and forwards `**params` to the bot's `__init__`.

Adding a new bot is a one-line registry edit — see [guides/bots.md](guides/bots.md).

### Built-in models

| Model           | Strategy summary                                                                       |
| --------------- | -------------------------------------------------------------------------------------- |
| `BasicBot`      | Hits while `active_score ≤ 25` (or any time the player has a Second Chance). Targets the leader on Freeze; targets self on early Flip Three; passes Second Chance to the lowest opponent. |
| `OmniscientBot` | Virtual-only. Reads `DeckView.draw_order` to compute exact bust probabilities and EV. |

---

## App layer

The app layer is a state machine of `Node`s that turn user input and engine events into prompt-driven flows.

### `App` (`app/orchestrator.py`)

Owns the `TUIApp` and a single "current node." The flow per keystroke:

1. User submits text → `TUIApp` invokes `App._handle_input(value)`.
2. The current node's `on_input(value, context)` runs — it may set context flags (`_show_game`, `_show_simulate`, `_show_home`) to request screen transitions and may return a next node (or `None` to stay).
3. The orchestrator handles screen transitions, then resolves any **dispatcher nodes** (nodes with `is_dispatcher = True` and no prompt of their own) by calling `node.dispatch(context)` until it lands on a real prompt-bearing node.
4. The new node's prompt is pushed to the command bar.

`context: dict` is the shared bag the nodes use to pass state between steps (player names, bot configs, the current `GameEngine`, simulation results, etc.).

### `Prompt` (`app/prompt.py`)

```python
@dataclass(frozen=True)
class Prompt:
    instruction: str
    validator: Callable[[str], str | None]   # returns error message or None
    placeholder: str = ""
    auto_advance_ms: int | None = None        # auto-submit empty input after timeout
```

Each node returns one. `auto_advance_ms` is what makes engine-driven flows feel reactive — a `CardDrawnEvent` can show for, say, 800 ms and then advance.

### Nodes (`app/nodes/`)

The decision tree is split by phase:

| File           | Nodes                                                                                                      |
| -------------- | ---------------------------------------------------------------------------------------------------------- |
| `home.py`      | `HomeNode` (top-level menu).                                                                               |
| `setup.py`     | `GameModeNode`, `PlayerCountNode`, `PlayerNameNode`, `BotCountNode`, `BotTypeNode`, `SetupCompleteNode`.   |
| `game.py`      | `GameRoundNode`, `HitStayNode`, `BotDecisionNode`, `DrawCardNode`, `CardDrawnNode`, `TargetSelectNode`, `BustNode`, `Flip7Node`, `SpecialResolvedNode`, `RoundOverNode`, `GameOverNode`. |
| `simulate.py`  | `SimPlayerCountNode`, `SimBotConfigNode`, `SimGameCountNode`, `SimConfirmNode`, `SimRunNode`, `SimDoneNode`. |

Game-phase nodes wrap the engine's generator: each one pulls the next request/event, builds the appropriate `Prompt` for it, and on input feeds the response back into the engine before producing the next node.

---

## Simulation layer

The simulation layer drives all-bot games for benchmarking and statistics.

### `runner.py`

```python
def run_game(
    bot_types: dict[str, int],
    trackers: list[SimTracker] | None = None,
) -> GameEngine
```

Builds players named `f"{bot_type} {i+1}"`, instantiates each through `Bot.create(bot_type, virtual=True)`, and plays one full game with `BotController` answering hit/stay and target requests. Trackers are wired in as listeners on `engine.play()` and receive an `on_game_over(engine)` after the game completes.

### `config.py`

Two helpers for batched runs that vary player count and bot composition:

- `validate_sim_config(player_range, bot_ranges)` — returns an error string if the configuration is infeasible (bot maximums can't reach player minimum, or vice versa), else `None`.
- `sample_game_config(player_range, bot_ranges)` — samples a valid `{bot_name: count}` dict for one game.

### `results.py`

`SimulationResults` aggregates a batch:

| Field / property        | Meaning                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| `total_games`           | Games recorded.                                                    |
| `wins_by_type`          | Wins keyed by bot type name.                                       |
| `bot_entries_by_type`   | Total seat-instances of each bot across all games.                 |
| `total_rounds`          | Sum of `engine.round_number` across games.                         |
| `total_winning_scores`  | Sum of winners' final `score`.                                     |
| `avg_game_length`       | Rounds per game.                                                   |
| `avg_winning_score`     | Mean winning score.                                                |
| `win_rate(bot)`         | `wins[bot] / entries[bot] * 100`.                                  |
| `win_share(bot)`        | `wins[bot] / total_wins * 100`.                                    |

### Trackers (`simulation/trackers/`)

`SimTracker` is a runtime-checkable `Protocol` with `label: str`, `on_event(event)`, `on_game_over(engine)`, and `format_results() -> list[str]`. Built-ins:

| Tracker                | Counts / measures                                                   |
| ---------------------- | ------------------------------------------------------------------- |
| `BustTracker`          | Total busts and average per game.                                   |
| `Flip7Tracker`         | Flip 7 occurrences and rate per 100 games.                          |
| `OpeningFreezeTracker` | Freezes that resolved during the opening deal (before any hit/stay).|

`default_trackers()` returns a fresh `[Flip7Tracker(), BustTracker()]` for one simulation run.

To add your own, see [guides/trackers.md](guides/trackers.md).

---

## TUI layer

`TUIApp` (`tui/app.py`) owns the urwid `MainLoop`, the persistent `CommandBar` footer, and a body area that swaps between three screens.

### Screens

| Screen           | Module                       | Body content                                                       |
| ---------------- | ---------------------------- | ------------------------------------------------------------------ |
| `HomeScreen`     | `tui/screens/home.py`        | ASCII title and tagline. All interaction is through the command bar. |
| `GameScreen`     | `tui/screens/game.py`        | Player panels (one per seat) showing hand and name; active player highlighted. |
| `SimulateScreen` | `tui/screens/simulate.py`    | Live-updating run progress and final results panel.                |

`TUIApp.show_home()`, `show_game(engine)`, `show_simulate()` swap the body. `set_prompt(prompt)` pushes a new `Prompt` to the command bar and arms the auto-advance timer if `prompt.auto_advance_ms` is set.

### Widgets (`tui/widgets/`)

- `CommandBar` — the persistent input area. Renders the current `Prompt`'s instruction, holds the input line, and emits a `submitted` urwid signal on Enter.
- `PlayerList` — grid of player panels for the game screen.
- `CardDetail` — per-card render using ASCII art from `tui/components/`.

### Components (`tui/components/`)

`build.py` plus card text templates (`card_border.txt`, `numbers.txt`, `cards/*`) generate the text-rendered card art used in player panels. These are bundled as package data via `pyproject.toml`'s `tool.setuptools.package-data`.

### Quit handling

`Ctrl-C` and the literal `exit` command both open a centered confirmation overlay. `intr` is unbound at the urwid screen level so `Ctrl-C` reaches the app handler instead of killing the process.

### Layout schema

Mockups under [`tui-schema/`](../tui-schema/) capture the intended layout for each screen (`home-page/home-page.png`, `game-view/game-view.png`).

---

## Cross-cutting contracts

A short summary of the contracts that wire layers together — these are the seams to extend rather than reimplement.

| Contract                 | Defined in                          | Implementations                                                  |
| ------------------------ | ----------------------------------- | ---------------------------------------------------------------- |
| `CardProvider`           | `core/protocols/decisions.py`       | `lambda game, _player: game.deck.deal()` (sim), TUI draw nodes (live) |
| `HitStay`                | `core/protocols/decisions.py`       | `BotController.hit_stay`, TUI hit/stay node, test stubs          |
| `TargetSelector`         | `core/protocols/decisions.py`       | `BotController.target_selector`, TUI target-select node, test stubs |
| `CardAction`             | `core/protocols/actions.py`         | `flip_three`, `freeze`, `second_chance` in `core/engine/actions.py` |
| `ScoreModifier`          | `core/protocols/modifier.py`        | Closures attached to `Card.score_modifier` (×2, +N)              |
| `AbstractBot`            | `bot/base.py`                       | `BasicBot`, `OmniscientBot`                                      |
| `SimTracker`             | `simulation/trackers/base.py`       | `BustTracker`, `Flip7Tracker`, `OpeningFreezeTracker`            |
| Engine listener callable | `engine.play(listeners=...)`        | `tracker.on_event` for each tracker in a simulation run          |

---

## End-to-end flow

### Live virtual game (one human-driven hit/stay)

```
User types "hit"
  → TUIApp.CommandBar emits submitted("hit")
  → App._handle_input("hit")
  → current node (HitStayNode) returns the next node and pushes
    True back into the engine generator
  → engine resolves the hit:
      yield CardDrawRequest → app provides a Card from the deck
      yield CardDrawnEvent  → app routes to CardDrawnNode (auto-advance)
      yield (bust / Flip 7 / continue) → app routes to the next node
  → next prompt rendered in the command bar
```

### Simulation batch

```
SimRunNode sets up the config and calls run_game() many times
  → each run_game:
      engine.play(listeners=[t.on_event for t in trackers])
        → engine yields requests to its callables:
            card_provider  = lambda game, _: game.deck.deal()
            hit_stay       = BotController.hit_stay
            target_select  = BotController.target_selector
        → each yielded event also fires every tracker's on_event
      → each tracker.on_game_over(engine) after the game ends
  → SimulationResults.record(config, engine) per game
  → SimDoneNode renders aggregated results + tracker.format_results()
```

---

## Where to go next

- **[guides/development.md](guides/development.md)** — get a working dev environment.
- **[guides/bots.md](guides/bots.md)** — write, register, and benchmark a new bot.
- **[guides/trackers.md](guides/trackers.md)** — collect custom statistics across runs.
- **[rules.md](rules.md)** — the canonical Flip 7 game rules.
