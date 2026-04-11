# TUI Plan

## Overview

A Claude Code-style terminal UI: persistent text input at the bottom, content rendered above. Built with [urwid](https://urwid.org/).

### Why urwid

urwid provides a widget-based layout model, built-in `MainLoop` with signal handling, and a `Columns`/`Pile`/`Frame` layout system that covers our needs without forcing CSS or a full reactive framework. It is mature, well-documented, and has no external dependencies beyond Python itself.

### urwid Concepts Used

| urwid primitive | Role in this project |
|---|---|
| `Frame` | Top-level layout: body + footer. Each screen returns a `Frame`. |
| `Pile` | Vertical stacking (logo block, player boxes, setup steps). |
| `Columns` | Horizontal splits (game grid + scoreboard). |
| `Edit` | Text input — the foundation of the command bar. |
| `Text` | Static labels, ASCII art, output panels. |
| `ListBox` / `SimpleFocusListWalker` | Scrollable regions (event log, completion list). |
| `WidgetWrap` | Base class for custom composite widgets. |
| `AttrMap` | Palette-based styling (highlight, dim, error). |
| `MainLoop` | Single event loop; `screen` swaps are done by replacing the loop's `widget`. |
| Signals | Custom signals on widgets replace Textual's message bus. |

---

## Screens

Screens are plain functions or classes that return an urwid widget tree (typically a `Frame`). The `App` class holds a reference to the `MainLoop` and swaps the top-level widget to "navigate".

### 1. Home Screen (`screens/home.py`)

Displayed on launch.

- `Frame` with:
  - **body**: `Filler` containing a `Pile` of `Text` widgets (ASCII logo, tagline, hint) — vertically centered
  - **footer**: `CommandConsole` widget
- Available commands:
  - `help` — list all commands
  - `play real` — start a real game
  - `play virtual` — start a virtual game
  - `simulate` — open the simulation configurator
  - `quit` / `exit`

---

### 2. Game Setup Flow (`screens/setup.py`)

Shared setup wizard for both real and virtual games. Steps are presented sequentially in the body as a growing `Pile`; the command console drives each step.

**Steps:**
1. How many human players? (min 1 for real, 0 allowed for virtual)
2. Name each human player (one prompt per player)
3. How many bots?
4. For each bot: name + select model (presented as a numbered list)

On completion, transitions to the Game Screen.

---

### 3. Game Screen (`screens/game.py`)

Main in-game interface. Layout:

```
┌─────────────────────────────────┬────────────┐
│                                 │ SCOREBOARD │
│   Player grid (ASCII cards)     │            │
│   Active player box highlighted │  Player 1  │
│                                 │  Player 2  │
│                                 │  ...       │
└─────────────────────────────────┴────────────┘
│ output area                                   │
│ > _                                           │  ← command console
└───────────────────────────────────────────────┘
```

Built as a `Frame`:
- **body**: `Columns` → left `Pile` of `PlayerBox` widgets, right `Scoreboard` widget
- **footer**: `CommandConsole`

**Player grid:**
- Each player has a card area rendered as ASCII art
- Active player's box is highlighted (`AttrMap` swap to `"active"` palette entry)
- Inactive players (stayed / frozen / busted) are visually dimmed (`"dimmed"` palette)
- Cards are arranged: number cards in a row, modifiers and action cards above

**Input bar prompts (real game):**
- Human turn: `Hit or stay? [h/s]`
- After hit: `Enter card drawn: ` (user types abbreviation, e.g. `7`, `F`, `+4`)
- Bot turn: `[BotName] is thinking... Enter card drawn for bot: `

**Input bar prompts (virtual game):**
- Human turn: `Hit or stay? [h/s]`
- Bot turns resolve automatically; the grid updates and output is shown in the console

---

### 4. Simulation Configurator (`screens/simulation.py`)

Launched via `simulate` command.

- `Frame` body: `Pile` containing a table (`Columns` per row) of available bot models, each with:
  - Min count
  - Max count (actual count randomised between min/max per run)
- Input: number of games to simulate
- `Run` confirmation triggers simulation

---

### 5. Simulation Runner (`screens/sim_runner.py`)

Headless simulation with a progress UI.

- `ProgressBar` widget (urwid built-in) showing games completed / total
- ETA / games-per-second `Text` widget
- Runs simulation via `MainLoop.set_alarm_in()` or a pipe-based background thread so the UI stays responsive

On completion, transitions to the Results screen.

---

### 6. Simulation Results (`screens/sim_results.py`)

Displays aggregated statistics from the simulation run:

- Win rate per model
- Average score per model
- Bust rate per model
- Round length distribution
- Export option (`export csv`) via the command console

---

## Folder Structure

```
tui/
├── plan.md              ← this file
├── __init__.py
├── app.py               ← urwid MainLoop, palette, screen routing
├── screens/
│   ├── __init__.py
│   ├── home.py          ← Home / command shell screen
│   ├── setup.py         ← Game setup wizard (shared real/virtual)
│   ├── game.py          ← Active game screen
│   ├── simulation.py    ← Simulation configurator
│   ├── sim_runner.py    ← Progress screen during simulation
│   └── sim_results.py   ← Results display
├── widgets/
│   ├── __init__.py
│   ├── command_console.py ← CommandConsole (master), CommandBar, CompletionList, CommandOutput
│   ├── card.py          ← ASCII card widget (single card rendering)
│   ├── player_box.py    ← Player's hand + name + status widget
│   ├── scoreboard.py    ← Side panel scoreboard widget
│   └── progress_bar.py  ← Simulation progress bar widget (if urwid built-in is insufficient)
└── ascii/
    └── cards.py         ← ASCII art templates for each card type
```

---

## Widget Implementation Notes

### CommandConsole (`widgets/command_console.py`)

A `WidgetWrap` containing a `Pile` of three sub-widgets stacked vertically:

1. **`CommandOutput`** — a `Text` widget that replaces its content on each call to `set_output()`. Hidden (zero-height `Text("")`) when empty.
2. **`CompletionList`** — a `Pile` of `Text` rows rendered above the input. Each row is either plain or wrapped in `AttrMap(…, "highlight")` for the selected item. Hidden when no matches.
3. **`CommandBar`** — an `Edit` widget with a `"> "` caption. Keystroke handling via `keypress()` override:
   - Printable keys / backspace → update filter, rebuild `CompletionList`
   - `up` / `down` → cycle selection in `CompletionList`
   - `enter` → accept highlighted completion or raw text, emit signal
   - `escape` → dismiss completions

**Signal**: `urwid.register_signal(CommandConsole, ["submitted"])`. Screens connect via `urwid.connect_signal(console, "submitted", handler)`.

### Screen Navigation

`app.py` holds the `MainLoop` instance. Each screen-builder function returns a widget tree. Navigation is:

```python
def navigate(self, screen_widget):
    self.loop.widget = screen_widget
```

No screen stack — if we need back-navigation later, we add a list acting as a stack.

### Palette

Defined once in `app.py` and passed to `MainLoop`:

```python
PALETTE = [
    ("primary",   "light cyan",   ""),
    ("accent",    "light green",  ""),
    ("error",     "light red",    ""),
    ("dimmed",    "dark gray",    ""),
    ("highlight", "standout",     ""),
    ("active",    "bold",         ""),
    ("bold",      "bold",         ""),
]
```

Widgets reference these names via `AttrMap`.

---

## Key Design Decisions

**urwid as the framework.** It gives us a real widget/layout system (`Frame`, `Pile`, `Columns`) without the weight of Textual's CSS engine and async machinery. Signal-based communication is simple and explicit. Background work uses `MainLoop` pipes or alarms.

**`ascii/cards.py` is isolated.** Card rendering is pure string logic with no urwid dependency — easy to unit test and reuse in a server/web context later.

**Setup wizard is one screen, not many.** Steps are rendered as a growing `Pile` of prompt/response `Text` widgets in the body, driven entirely by the command console. No separate screen transitions per step keeps navigation simple.

**Real vs. virtual diverge only in `game.py`.** The screen is instantiated with a `GameEngine` subclass — real games prompt for card input, virtual games auto-resolve bot turns. The layout and widget set are identical.

**`CommandConsole` is the drop-in footer for every screen.** Each screen builds a `Frame(body=…, footer=CommandConsole(commands))` and connects to the `"submitted"` signal. Output replaces on each command — no scrollback accumulation.

**Simulation runs in a Textual worker.** `sim_runner.py` uses `@work(thread=True)` so the progress bar stays live during computation.

**`GameEngine` is passed into screens on construction, not pulled from the app.** Each screen that needs a game engine receives it as a constructor argument. Screens should never reach up into `app.py` to access game state — this keeps screens independently testable and prevents hidden coupling through the app layer.
