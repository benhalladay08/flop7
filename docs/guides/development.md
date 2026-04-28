# Local development

This guide gets a working Flop 7 dev environment up on your machine. If you only want to run the game, see [install.md](../install.md) instead.

## Requirements

- Python 3.10+
- `pip` and a virtual environment manager of your choice (`venv`, `uv`, `pyenv-virtualenv`, etc.)

## Clone and install

```bash
git clone https://github.com/benhalladay08/flop7.git
cd flop7
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The `-e` (editable) install means changes to `src/flop7/` take effect immediately without reinstalling.

## Run the app

```bash
flop7
# or
python -m flop7
```

Both invoke `flop7.cli:main`, which boots the urwid TUI.

## Run the tests

```bash
pytest
```

The suite covers core engine, bots, simulation, and TUI components.

### Useful subsets

```bash
pytest tests/bot                   # bot logic only
pytest tests/simulation            # simulation runner + trackers
pytest tests/core                  # engine internals
pytest -k basic                    # any test matching "basic"
```

## Project layout

```
src/flop7/
├── cli.py            # `flop7` entry point
├── __main__.py       # `python -m flop7` entry point
├── core/             # game engine, cards, deck, requests/events — no UI deps
├── bot/              # bot models + view adapters
├── simulation/       # all-bot batched runs, trackers, results
├── app/              # orchestration: routes user commands into engine flow
└── tui/              # urwid screens, components, widgets
```

See [architecture.md](../architecture.md) for a comprehensive layer-by-layer reference.

## Test fixtures

Most engine-level tests are built on helpers in [`tests/conftest.py`](../../tests/conftest.py):

| Helper           | Purpose                                                                  |
| ---------------- | ------------------------------------------------------------------------ |
| `make_deck`      | Build a `Deck` whose `deal()` returns cards in the order you specify     |
| `make_players`   | Create N test players named `P1`–`PN`                                    |
| `make_engine`    | Build a full `GameEngine` with deterministic deck and stub callables     |
| `drive_round`    | Run one `engine.round()` generator, sending stubbed responses            |
| `opening_cards`  | Zero-point filler cards for skipping past the opening deal in a test     |

Reach for these before writing your own engine setup — they keep tests short and consistent.

## TUI tips

The TUI is urwid-based. If you're working on a screen or component, run the app in a terminal that supports 256 colors and at least an 80-column width. The schema mockups under `tui-schema/` show the intended layout for each screen.
