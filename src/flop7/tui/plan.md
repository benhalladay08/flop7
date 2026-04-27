# TUI Plan

## Overview

A Claude Code-style terminal UI: persistent command bar at the bottom, content rendered above. Built with [urwid](https://urwid.org/).

### Architecture: Prompt-Driven Command Bar

The command bar is a passive, three-zone widget (instruction → input → error) that never interprets user input. All flow logic lives in the **orchestrator's decision tree** — a state machine of `Node` objects.

```
Orchestrator                         TUI
┌──────────────────┐    Prompt      ┌────────────────────┐
│  Node (current)  │──────────────▶│  CommandBar         │
│  ├─ prompt       │               │  ├─ instruction     │
│  └─ on_input()   │◀──────────────│  ├─ input (Edit)    │
│                  │   "submitted" │  └─ error            │
│  context: dict   │   signal      └────────────────────┘
└──────────────────┘
```

**Data contract**: `Prompt` dataclass (`app/prompt.py`) with `instruction`, `validator`, and `placeholder`. The TUI consumes it; the orchestrator constructs it.

**Decision tree**: Each `Node` (`app/nodes.py`) has a `prompt` property and `on_input(value, context)` method that returns the next `Node`. The orchestrator holds the current node and a mutable `context: dict` for accumulated state.

### Why urwid

urwid provides a widget-based layout model, built-in `MainLoop` with signal handling, and a `Columns`/`Pile`/`Frame` layout system that covers our needs without forcing CSS or a full reactive framework.

### urwid Concepts Used

| urwid primitive | Role in this project |
|---|---|
| `Frame` | Top-level layout: body + footer. |
| `Pile` | Vertical stacking (command bar zones, screen layouts). |
| `Columns` | Horizontal splits (game grid + scoreboard). |
| `Edit` | Text input in the command bar. |
| `Text` | Instructions, errors, ASCII art, labels. |
| `WidgetWrap` | Base class for custom composite widgets. |
| `AttrMap` | Palette-based styling (instruction, command, error). |
| `MainLoop` | Single event loop; screen swaps via `frame.body = widget`. |
| Signals | `CommandBar` emits `"submitted"` signal to the orchestrator. |

---

## Command Bar Widget (`widgets/command_bar.py`)

A `WidgetWrap` containing a `Pile` of three zones:

1. **Instruction** (`Text`, `"instruction"` palette) — tells the user what to type
2. **Input** (`Edit`, `"command"` palette) — `"> "` prompt for text entry
3. **Error** (`Text`, `"error"` palette) — shows validation errors, hidden when empty

**Key methods**:
- `set_prompt(prompt)` — update instruction, clear input & error, store validator
- `keypress` — on `enter`, validate and either show error or emit `"submitted"` signal; on any other key, clear the error

---

## Orchestrator Decision Tree (`app/nodes/`)

Nodes live in `app/nodes/` as a package. Each `Node` subclass defines one step:

| Node | Instruction | Transitions to |
|------|-------------|---------------|
| `HomeNode` | Welcome text + command list | `GameModeNode`, quit |
| `GameModeNode` | "virtual or real?" | `PlayerCountNode` |
| `PlayerCountNode` | "How many human players? (1–10)" | `PlayerNameNode` |
| `PlayerNameNode` | Roster with blank slots, fills as names entered | loops → `BotCountNode` or `SetupCompleteNode` |
| `BotCountNode` | "How many bots? (min–max)" with constraint explanation | `BotTypeNode` or `SetupCompleteNode` |
| `BotTypeNode` | Bot roster with blank slots + available models list | loops → `SetupCompleteNode` |
| `SetupCompleteNode` | Placeholder until game start is wired | `HomeNode` |

Rules enforced by nodes:
- 10 human players → skip bot steps entirely
- Fewer than 3 humans → minimum bot count enforced
- `real` game mode → virtual-only bot models excluded from the list

Nodes receive already-validated input (the `CommandBar` ran the validator first). The orchestrator (`app/orchestrator.py`) drives the loop: calls `node.on_input()`, gets the next node, pushes its prompt to the TUI.

---

## Screens

Screens are plain classes returning an urwid widget tree. The `TUIApp` holds the `Frame` and swaps `frame.body` to navigate.

### 1. Home Screen (`screens/home.py`)

Displayed on launch. ASCII logo + tagline, vertically centered.

### 2. Game Screen (`screens/game.py`) — planned

The game screen has two layout modes, selected at render time based on terminal width (threshold TBD, ~120 cols).

#### Compact mode (narrow terminal)

A single scrollable `ListBox` of player rows. Each row fits on one or two lines:

```
  Player        Cards                          Score  Status
─────────────────────────────────────────────────────────────
▸ Alice    [3] [7] [11] [+4] [×2]              42    Active
  Bob      [1] [5] [9] [12] [SC]               27    Stayed
  Charlie  [8] [8] ← BUST                       0    Busted
```

Cards use abbreviated inline notation: `[12]`, `[+4]`, `[×2]`, `[SC]`, `[F3]`, `[FZ]`. The active player gets an arrow indicator and palette highlight. All players are visible simultaneously; scrolling only needed with 10 players on a very small terminal.

#### Wide mode (large terminal)

A `Columns` layout: compact player list on the left, ASCII art card detail for the focused player on the right.

```
┌─ Players ────────────┬─ Alice (Active) ─────────────────────────┐
│ ▸ Alice    42  Act   │                                          │
│   Bob      27  Stay  │  ╔═══╗  ╔═══╗  ╔═══╗  ╔═══╗            │
│   Charlie   0  Bust  │  ║ 3 ║  ║ 7 ║  ║11 ║  ║+4 ║            │
│                      │  ╚═══╝  ╚═══╝  ╚═══╝  ╚═══╝            │
└──────────────────────┴──────────────────────────────────────────┘
```

The detail pane shows the focused (active) player's full hand using large ASCII art cards. Card art is defined per card in `tui/ascii/cards/` as `.txt` files (one per card: `0.txt` through `12.txt`, `plus2.txt`…`plus10.txt`, `sc.txt`, `f3.txt`, `fz.txt`). All cards share the same fixed dimensions so they tile cleanly in a horizontal flow with wrapping.

**Resize handling**: urwid reports terminal size on each render pass. The screen checks `cols` at render time and returns either the compact or wide widget tree. No polling or signal needed — it's just a conditional in the body widget's `render` method.

**Planned widgets for this screen**:
- `PlayerListWidget` — shared between both modes; narrow columns in wide mode, full columns in compact
- `CardDetailPane` — wide mode only; renders ASCII card art for one player's hand with horizontal flow and line wrapping
- `GameScreen` — assembles the layout, owns the resize check

### 3–6. Future Screens

Simulation configurator, runner, and results — to be implemented as separate screens triggered by node transitions in the orchestrator.

---

## Folder Structure

```
tui/
├── plan.md              ← this file
├── __init__.py
├── app.py               ← urwid MainLoop, palette, screen routing, signal wiring
├── screens/
│   ├── __init__.py
│   ├── home.py          ← Home screen (ASCII logo)
│   ├── game.py          ← Game screen (compact + wide modes)  [planned]
│   └── ...              ← simulation screens  [planned]
├── widgets/
│   ├── __init__.py
│   ├── command_bar.py   ← 3-zone command bar (instruction/input/error)
│   ├── player_list.py   ← scrollable player roster widget  [planned]
│   └── card_detail.py   ← ASCII card art pane for wide mode  [planned]
└── ascii/
    └── cards/           ← one .txt file per card face  [planned]
```

---

## Palette

Defined in `app.py`:

```python
palette = [
    ("title",       "light cyan,bold", ""),
    ("instruction", "light cyan",      ""),
    ("command",     "white",           ""),
    ("error",       "light red",       ""),
    ("active",      "bold",            ""),   # active player highlight
    ("dimmed",      "dark gray",       ""),   # stayed/busted players
    ("busted",      "light red",       ""),   # bust indicator
]
```
