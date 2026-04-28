# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo purpose

Flop 7 is an unofficial terminal Flip 7 emulator. The repo's primary purpose is **building and testing Flip 7 bots**; live virtual play and live scorekeeping share the same engine but are secondary use cases.

The headline contributor doc is `docs/guides/bots.md`. The comprehensive architectural reference is `docs/architecture.md`. The canonical game rules are in `docs/rules.md`.

## Common commands

```bash
python -m pip install -e .   # editable install (Python 3.10+)
flop7                        # launch the urwid TUI
python -m flop7              # equivalent

pytest                       # full test suite
pytest tests/bot             # bot logic only
pytest tests/simulation      # simulation runner + trackers
pytest tests/core            # engine internals
pytest -k basic              # any test matching "basic"
pytest tests/bot/models/test_basic.py::TestHitStay::test_boundary_25_hits
```

Pre-commit (ruff + black) is **planned but not yet set up** per the CONTRIBUTING.md note. Don't add ruff/black config or hooks unsolicited.

## Architecture (the parts you can't see by ls'ing)

Five layers under `src/flop7/`. The seam between them is what makes the codebase work — keep it intact.

### `core/` — generator-driven game engine

`GameEngine.round()` is a generator that yields **typed requests and events** from `core/engine/requests.py`. Drivers (bots, app nodes, tests) `.send()` responses to requests; events expect `None` back.

Request types (driver must respond): `CardDrawRequest`, `HitStayRequest`, `TargetRequest`.
Event types (notification only): `CardDrawnEvent`, `PlayerBustedEvent`, `Flip7Event`, `FreezeEvent`, `SecondChanceEvent`, `FlipThreeStartEvent`, `FlipThreeResolvedEvent`, `RoundOverEvent`.

`GameEngine.play(listeners=...)` auto-drives the generator using its three injected callables (`card_provider`, `hit_stay_decider`, `target_selector`). Listeners receive every yielded object — that's how trackers observe state.

Engine is parameterized by **`Protocol` callables** in `core/protocols/` (`CardProvider`, `HitStay`, `TargetSelector`, `CardAction`, `ScoreModifier`). Anything satisfying the structural type works — there are no base classes to extend on the engine side.

Constants on the engine class: `WIN_SCORE = 200`, `FLIP_7_BONUS = 15`, `FLIP_7_COUNT = 7`.

### `bot/` — strategy layer

Bots subclass `AbstractBot` (`bot/base.py`) and implement `hit_stay(view, player_view) -> bool` and `target_selector(view, event, player_view, eligible) -> PlayerView`. They receive **frozen views** (`GameView`/`PlayerView`/`DeckView` from `bot/knowledge.py`) — never the live engine.

`bot/registry.py` (`Bot.available_bots`, `Bot.create`) is the single registration point. The TUI and simulation runner both consult it.

`virtual_only = True` marks bots that read `DeckView.draw_order` (full draw sequence — only populated when `engine.real_mode` is False). The registry refuses to instantiate them in real games.

`BotController` (`bot/controller.py`) is the adapter that satisfies the engine's `HitStay`/`TargetSelector` protocols by building views and calling the registered bot per player index.

### `simulation/` — all-bot batched runs

`simulation/runner.py::run_game(bot_types, trackers=None)` plays one full game and returns the finished `GameEngine`. Trackers are wired in as `engine.play(listeners=[t.on_event for t in trackers])`, then `t.on_game_over(engine)` after the game ends.

Trackers satisfy `SimTracker` (Protocol in `simulation/trackers/base.py`): `label: str`, `on_event(event)`, `on_game_over(engine)`, `format_results() -> list[str]`. Plain classes with these attributes work — no subclassing.

`SimulationResults` (`simulation/results.py`) aggregates win-rate / win-share / avg-game-length stats across many `run_game` calls.

### `app/` — orchestration via state-machine of nodes

`App._handle_input(value)` runs each keystroke through the **current node's** `on_input(value, context)`. Nodes return the next node (or `None` to stay) and may set context flags (`_show_game`, `_show_simulate`, `_show_home`) to request screen transitions.

**Dispatcher nodes** (`is_dispatcher = True`, no prompt) are resolved immediately by the orchestrator via `node.dispatch(context)` — used to branch flows without a user-facing pause.

`Prompt` (`app/prompt.py`) is a frozen dataclass: `instruction`, `validator`, `placeholder`, `auto_advance_ms` (None or ms-until-empty-submit). Auto-advance is what makes engine event nodes feel reactive.

Game-phase nodes (`app/nodes/game.py`) wrap the engine generator: each pulls the next request/event, builds a `Prompt`, and on input feeds the response back.

### `tui/` — urwid presentation

`TUIApp` owns the `MainLoop` and three swappable screens (`HomeScreen`, `GameScreen`, `SimulateScreen`). The `CommandBar` footer is persistent — every screen interacts via it.

`Ctrl-C` and the literal `exit` command both open a confirmation overlay; `intr` is unbound at the urwid screen level so `Ctrl-C` doesn't kill the process.

## Project rules

These are durable rules from CONTRIBUTING.md and user guidance — apply them without being asked.

1. **Extend, don't reimplement.** Bots, trackers, and app nodes do not duplicate engine logic. They consume the request/event stream or extend through existing protocols. If a hook doesn't exist, add it to the engine — don't simulate the engine elsewhere. (This rule is also stored as `feedback_no_duplicate_core_logic.md` in user memory.)
2. **No engine internals from outside `core/`.** Bots never call `game.deck.deal()`, mutate `player.score`, etc. They use the views and return decisions.
3. **Read-only views for bots.** `build_game_view(engine)` is the only sanctioned way to expose engine state to a bot. `DeckView.draw_order` is empty when `engine.real_mode` is True — that's the structural enforcement of "no peeking in real games."

## Conventional Commits + release-please

Commit messages must use Conventional Commits prefixes — `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, with `!` or `BREAKING CHANGE:` for breaking changes. release-please reads commit history to bump `pyproject.toml` and cut tagged releases. Don't commit free-form messages.

## Tests

Test layout mirrors `src/flop7/`. Shared fixtures live in `tests/conftest.py`:

- `make_deck(cards)` — deterministic deck whose `deal()` returns `cards` in order
- `make_players(n)` — N test players named `P1`..`PN`
- `make_engine(cards, n_players, hit_responses, target_responses, ...)` — full engine with stub callables iterating over the response lists
- `drive_round(engine, hit_responses, target_responses, card_inputs)` — runs one `engine.round()` to completion, sending stubbed responses to each yielded request, returns the list of yielded objects
- `opening_cards(*indexes)` — zero-point fillers to skip past the opening deal cleanly

Reach for these before writing custom engine setup. Bot tests should mirror `tests/bot/models/test_basic.py` (build a `GameView` with `build_game_view`, assert decisions). Simulation tests should mirror `tests/simulation/test_runner.py` (call `run_game` and assert on returned engine + tracker state).
