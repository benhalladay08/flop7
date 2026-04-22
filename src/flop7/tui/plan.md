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

## Orchestrator Decision Tree (`app/nodes.py`)

Each `Node` subclass defines one step in the flow:

| Node | Instruction | Transitions to |
|------|-------------|---------------|
| `HomeNode` | "Type 'play', 'simulate', or 'quit'." | `PlayerCountNode`, quit |
| `PlayerCountNode` | "How many players? (3–6)" | `PlayerNameNode` |
| `PlayerNameNode` | "Enter name for Player N of M:" | loops → `SetupCompleteNode` |
| `SetupCompleteNode` | "Setup complete! Type 'home' to return." | `HomeNode` |

Nodes receive already-validated input (the `CommandBar` ran the validator first). The orchestrator (`app/orchestrator.py`) drives the loop: calls `node.on_input()`, gets the next node, pushes its prompt to the TUI.

---

## Screens

Screens are plain classes returning an urwid widget tree. The `TUIApp` holds the `Frame` and swaps `frame.body` to navigate.

### 1. Home Screen (`screens/home.py`)

Displayed on launch. ASCII logo + tagline, vertically centered.

### 2–6. Future Screens

Game setup, game view, simulation configurator, runner, and results — to be implemented as separate screens triggered by node transitions in the orchestrator.

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
│   └── ...              ← future screens
└── widgets/
    ├── __init__.py
    ├── command_bar.py   ← 3-zone command bar (instruction/input/error)
    └── ...              ← future widgets (player_box, scoreboard, etc.)
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
]
```
