# flop7

The unofficial Flip 7 terminal emulator

> NOTE: 
> This document was created with the help of Github Copilot. The architecture itself was created by Ben Halladay, and Copilot assisted in generating diagrams based on code already written by Ben Halladay.

## Overview

flop7 is a terminal based emulator for the popular game Flip 7. It allows the user to track points for a live game, or play the game virtually against others or against bots.

### Flip 7 — Game Summary

Flip 7 is a press-your-luck card game for 3+ players. Players race to be the first to accumulate **200 points** across multiple rounds.

The 94-card deck contains three categories of cards:

| Category | Cards | Bustable |
|---|---|---|
| **Number** (0–12) | 79 cards — each value N appears N times (except 0, which has 1) | Yes |
| **Action** (Flip Three, Freeze, Second Chance) | 9 cards (3 of each) | No |
| **Score Modifier** (+2, +4, +6, +8, +10, ×2) | 6 cards (1 of each) | No |

Each round, players take turns choosing to **hit** (draw a card) or **stay** (bank their points and exit the round). Drawing a duplicate number card causes a **bust** — the player scores 0 for that round. If a player collects 7 unique number cards, the round ends immediately and they receive a 15-point bonus.

Action cards allow you to target other players with special abilities: **Flip Three** forces a target to draw 3 cards, **Freeze** forces a target to bank and exit, and **Second Chance** absorbs one future duplicate.

Score modifier cards adjust end-of-round scoring: ×2 doubles the number card total (applied first), then flat bonuses (+2 through +10) are added on top.

## Repo structure overview

The codebase is organized into four domain layers plus entry points:

```text
src/flop7/
├── __main__.py              # Entry point for python -m flop7
├── cli.py                   # Entry point for flop7 command-line tool
├── app/                     # Top-level orchestration layer
├── tui/                     # Terminal user interface (urwid-based)
├── bot/                     # Bot models and decision-making strategies
└── core/                    # Game rules engine and data models
```

### Layer responsibilities

- **`app/`** — Orchestrates the application lifecycle and routes user commands to game logic
- **`tui/`** — Handles all terminal rendering and user input via urwid
- **`bot/`** — Provides bot player models with configurable decision strategies
- **`core/`** — Implements the game engine, card definitions, and rules
- **`cli.py` / `__main__.py`** — Bootstrap the application

## App design

The `app/` layer is the top-level orchestration layer. It is responsible for starting the TUI loop, receiving user commands, and routing those commands into game setup / gameplay state transitions.

### Responsibilities

1. Construct the TUI and provide a command handler callback
2. Start and stop the application lifecycle (`run`, exit behavior)
3. Coordinate screen/state transitions at the application level
4. Act as the bridge between command input and game logic entry points

### Control flow

1. `cli.py` creates `App` and calls `run()`.
2. `App` constructs `TUIApp`, injecting `handle_user_command` as the callback.
3. `TUIApp` runs the urwid `MainLoop`.
4. On Enter, the command bar text is sent back to `App.handle_user_command(...)`.
5. `App` interprets the command and triggers app-level behavior (navigation, setup, game actions).

### App orchestration diagram

```plantuml
@startuml
skinparam classAttributeIconSize 0
hide empty members

class CLI {
  +main() : None
}

class App {
  +run() : None
  +handle_user_command(command: str) : None
}

class TUIApp {
  +run() : None
  +set_screen(body) : None
  +set_command_prompt(prompt) : None
}

class GameEngine

CLI --> App : creates
App --> TUIApp : owns
TUIApp --> App : command callback
App --> GameEngine : orchestrates

@enduml
```

## Core design

### Architecture

The game logic lives in `src/flop7/core/` and is organized into four sub-packages:

```text
core/
├── classes/      # Data objects — Card, Deck, Player
├── engine/       # Game loop and action card resolution
├── enum/         # Enumerations for events and decisions
└── protocols/    # Structural typing contracts (Protocol classes)
```

#### `classes/` — Data Layer

- **`Card`** — A `@dataclass` representing a single card definition. Fields include the card's name, abbreviation, deck count, point value, bustable flag, and an optional `score_modifier` callback with an associated `score_priority`. All 22 unique card types are defined as module-level constants in `cards.py` (e.g. `ZERO`, `FLIP_THREE`, `PLUS_TWO`), and collected into `ALL_CARDS` and `CARD_MAP` for lookup.

- **`Deck`** — Manages the draw pile and discard pile. On construction it expands `ALL_CARDS` into the full 94-card list (respecting `num_in_deck`) and shuffles, unless an explicit ordered card list is provided for tests or simulations. `draw_pile[0]` is always the next virtual card. After the draw pile's last card is dealt, `reshuffle()` recycles the discard pile.

- **`Player`** — Pure state container for a single player. Tracks `name`, `hand`, cumulative `score`, and `is_active` status. The computed property `active_score` calculates the current round score by sorting modifiers by `score_priority` (×2 first, then flat bonuses) and folding them over the number-card sum.

#### `engine/` — Game Loop

- **`GameEngine`** — The core engine class that owns the round lifecycle. It holds the `Deck`, player list, and two injected decision callbacks (`HitStay` and `TargetSelector`). The core loop is:
  1. `play()` calls `round()` until a player reaches 200 points.
  2. `round()` iterates active players: each either hits or stays.
  3. `hit()` processes a drawn card — checking for Second Chance absorption in `pre_hit_hook()`, resolving action cards through the action registry, and detecting busts for duplicate number cards.
  4. After the round, every player's `active_score` is added to their cumulative `score`, hands are discarded, and the win condition is checked.

- **`actions`** — Module-level functions (`flip_three`, `freeze`, `second_chance`) that implement the three action card effects. Each follows the `CardAction` protocol signature, and `get_action(card)` resolves an action handler from the card abbreviation without mutating the card constants.

#### `enum/` — Enumerations

- **`TargetEvent`** — Identifies the reason a target is being selected (Flip Three, Freeze, or Second Chance), so the `TargetSelector` callback can present appropriate context.

#### `protocols/` — Dependency Contracts

All external behavior the engine depends on is expressed as `typing.Protocol` classes, enabling structural (duck) typing:

| Protocol | Signature | Purpose |
|---|---|---|
| `HitStay` | `(game, player: Player) -> bool` | Decides whether a player hits or stays with access to full game context |
| `TargetSelector` | `(game, event, player, eligible) -> Player` | Picks one target from engine-provided legal targets |
| `CardAction` | `(game, player, card) -> Generator` | Executes a card's special effect, resolved through the action registry |
| `ScoreModifier` | `(current_score: int) -> int` | Transforms score (e.g. ×2, +4), tied to the `Card` class |

This protocol-based design decouples the engine from any concrete UI or strategy implementation — the same `GameEngine` can be driven by a TUI, a bot, or automated tests simply by injecting different callables.

### Class Diagram

```plantuml
@startuml
skinparam classAttributeIconSize 0
skinparam linetype ortho
hide empty members

package "core.classes" {
  class Card <<dataclass>> {
    +name : str
    +abbrv : str
    +num_in_deck : int
    +points : int
    +bustable : bool
    +score_priority : int
    +score_modifier : ScoreModifier | None
  }

  class Deck {
    +draw_pile : list[Card]
    +discard_pile : list[Card]
    +deal() : Card
    +discard(cards: list[Card]) : None
    +shuffle() : None
    +reshuffle() : None
    -_build_card_list() : list[Card]
  }

  class Player {
    +name : str
    +hand : list[Card]
    +score : int
    +is_active : bool
    +active_score : int  <<property>>
    +has_card(card: Card) : bool
  }
}

package "core.engine" {
  class GameEngine {
    +deck : Deck
    +players : list[Player]
    +round_number : int
    +game_over : bool
    +winner : Player | None
    -hit_stay_decider : HitStay
    -target_selector : TargetSelector
    +active_players : list[Player]  <<property>>
    +play() : None
    +round() : None
    +hit(player: Player, card: Card) : None
    +pre_hit_hook(player: Player, card: Card) : bool
    +post_hit_hook(player: Player, card: Card) : None
  }

  class "actions" as Actions <<module>> {
    +flip_three(game, player, card) : Generator
    +freeze(game, player, card) : Generator
    +second_chance(game, player, card) : Generator
    +get_action(card: Card) : CardAction | None
  }
}

package "core.protocols" {
  interface HitStay <<Protocol>> {
    +__call__(game, player: Player) : bool
  }

  interface TargetSelector <<Protocol>> {
    +__call__(game, event, player, eligible) : Player
  }

  interface CardAction <<Protocol>> {
    +__call__(game, player, card) : Generator
  }

  interface ScoreModifier <<Protocol>> {
    +__call__(current_score: int) : int
  }
}

package "core.enum" {
  enum TargetEvent {
    FLIP_THREE
    FREEZE
    SECOND_CHANCE
  }
}

' --- Relationships ---
Deck "1" o-- "*" Card : draw_pile / discard_pile
Player "1" o-- "*" Card : hand
GameEngine "1" *-- "1" Deck
GameEngine "1" *-- "2..*" Player
GameEngine --> HitStay : delegates
GameEngine --> TargetSelector : delegates
Actions --> GameEngine : operates on
Actions --> TargetEvent : reads
Actions --> CardAction : resolves
Card ..> ScoreModifier : optional callback

@enduml
```

## Interface

The terminal interface is intentionally simple: one main content area and one persistent command area at the bottom. The command area is the same on every screen, so users always interact with the app in a consistent way.

### Visual mockups

Home screen mockup:

![Home screen mockup](../tui-schema/home-page/home-page.png)

Game screen mockup:

![Game screen mockup](../tui-schema/game-view/game-view.png)

### Layout model

The UI is split into two vertical zones:

1. **Main view (top):** screen-specific content
2. **Command console (bottom):** output + input + suggestions

The main view changes based on context (home vs game), but the command console stays persistent.

### Home screen (simplified)

The home screen is mostly a landing page:

- Centered ASCII title/logo for visual identity
- Short subtitle/tagline beneath the logo
- No complicated widgets in the body
- All interaction happens through the command console

Expected commands from home are simple navigation commands (for example: start real game, start virtual game, help, quit).

### Game screen (simplified)

The game screen keeps the same console at the bottom, but the top area becomes a live game board:

- Player panels are shown in a grid-like row/stack layout
- Each panel shows the player's visible cards and name
- The active player's panel can be visually emphasized
- Score and turn context are shown in the main area, not inside the input line

This gives players one stable mental model: watch the board above, type commands below.

### Command console behavior

The command console has three parts (top to bottom):

1. **Output line/block** for short status text and prompts
2. **Input line** (prefixed with `>`) where the user types commands
3. **Suggestion list** with up to three visible completions

If more than three completions are available, the user navigates them with arrow keys instead of expanding the list indefinitely. The main view above should resize as needed to preserve console visibility.

### Interaction philosophy

The TUI is command-driven rather than mouse-driven:

- The user always types explicit commands
- The system responds with clear textual prompts
- Screen changes are lightweight and immediate

This design keeps the interface fast, accessible over any terminal, and easy to test because the input/output contract is text-first.

## Virtual Bots

The bot system is a strategy layer outside `core`. Core players are plain game-state objects; bot ownership and dispatch live in adapter/controller code that converts engine requests into read-only bot views.

### Design goals

1. Support multiple bot models with minimal boilerplate
2. Keep bot decision logic isolated from core mutation and TUI prompts
3. Allow advanced models (like omniscient) in virtual mode only
4. Make model registration and selection simple for setup screens

### Planned architecture

Bot logic lives in `src/flop7/bot/`.

```text
bot/
├── base.py                  # AbstractBot contract
├── controller.py            # engine request -> bot view adapter
├── registry.py              # model-name -> bot-class lookup
├── knowledge.py             # frozen game-state views
├── utils.py                 # shared strategy helpers
└── models/
  ├── basic.py             # baseline probability-driven bot
  └── omniscient.py        # full-information virtual-only bot
```

### Base bot contract

All bot models implement `AbstractBot` in `bot/base.py`:

- `hit_stay(view, player_view) -> bool`
- `target_selector(view, event, player_view, eligible_views) -> PlayerView`

Bots receive frozen `GameView`, `PlayerView`, and `DeckView` snapshots instead of the mutable `GameEngine`. In virtual mode, `DeckView.draw_order` exposes the full future draw order; in real mode, unknown future cards are represented by an empty draw order.

### Model registry

`bot/registry.py` provides the `Bot` class, a central registry and factory for bot model instantiation. It maintains a class-level mapping of model names to implementations:

- `Basic` -> `BasicBot`
- `Omniscient` -> `OmniscientBot`

Instantiation is handled via the factory:

```python
Bot.create("Basic", virtual=False, **params)
```

The `virtual` flag is used to validate that virtual-only models are not used in real (non-virtual) games. This keeps setup/UI code decoupled from model class imports — the interface layer can request a bot by name without knowing the concrete class.

### Model behavior (initial set)

#### Basic bot

The baseline model targets straightforward, explainable strategy:

- Hit while active score is 25 or less
- Always hit with Second Chance
- For action cards, choose from the engine-provided eligible targets

This model is intended to be predictable and easy to benchmark.

#### Omniscient bot

The omniscient model is a benchmarking model for virtual play:

- Reads full hidden deck state
- Computes exact or near-exact bust probabilities from remaining cards
- Uses deeper expected-value decisions than Basic

Because it uses hidden information, it should be restricted to virtual games and never used for live/real deck tracking mode.

### Knowledge and utility layers

Two shared modules keep bot logic decoupled from mutable engine objects:

- `knowledge.py`: builds frozen `GameView`, `PlayerView`, and `DeckView` snapshots
- `utils.py`: common helper math such as overall score and future probability helpers

The intent is to prevent duplicate math and state-derivation code across models.

### Bot UML diagram

```plantuml
@startuml
skinparam classAttributeIconSize 0
hide empty members

abstract class AbstractBot {
  +hit_stay(view, player_view) : bool
  +target_selector(view, event, player_view, eligible_views) : PlayerView
}

class BasicBot
class OmniscientBot
class BotController
class GameView
class PlayerView
class DeckView

class Bot {
  +avaliable_bots : dict
  +create(model, virtual=False, **params) : AbstractBot
}

class BotUtils

BotController --> AbstractBot : calls
BotController --> GameView : builds
GameView o-- PlayerView
GameView o-- DeckView
AbstractBot ..> BotUtils : uses

AbstractBot <|-- BasicBot
AbstractBot <|-- OmniscientBot
Bot --> BasicBot
Bot --> OmniscientBot

@enduml
```

### Sequence overview

1. Game engine yields a `HitStayRequest` or `TargetRequest`.
2. The app/controller identifies whether the source player is bot-controlled.
3. `BotController` builds a frozen `GameView` and calls the configured bot.
4. The bot returns a boolean or eligible `PlayerView`.
5. `BotController` maps the result back to the engine's expected `Player` object.
