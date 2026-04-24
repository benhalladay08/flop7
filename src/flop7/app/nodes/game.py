from __future__ import annotations

from flop7.app.nodes.base import Node
from flop7.app.prompt import Prompt
from flop7.core.classes.cards import ALL_CARDS, FLIP_THREE, FREEZE, SECOND_CHANCE, TIMES_TWO
from flop7.core.engine.requests import (
    CardDrawnEvent,
    CardInputRequest,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
    TargetRequest,
)


# ── Card lookup (case-insensitive, supports friendly aliases) ────────

_CARD_LOOKUP: dict = {}
for _c in ALL_CARDS:
    _CARD_LOOKUP[_c.name.lower()] = _c
    _CARD_LOOKUP[_c.abbrv.lower()] = _c
# User-friendly aliases matching the card art filenames
_CARD_LOOKUP["f3"] = FLIP_THREE
_CARD_LOOKUP["fz"] = FREEZE
_CARD_LOOKUP["sc"] = SECOND_CHANCE
_CARD_LOOKUP["x2"] = TIMES_TWO

_VALID_CARD_DISPLAY = "0–12, +2, +4, +6, +8, +10, x2, F3, FZ, SC"


# ── Engine builder ───────────────────────────────────────────────────

def _build_engine(context: dict):
    """Construct a GameEngine from the accumulated setup context."""
    from flop7.core.classes.deck import Deck
    from flop7.core.classes.player import Player
    from flop7.core.engine.engine import GameEngine

    game_mode = context["game_mode"]
    real_mode = game_mode == "real"

    players = [Player(name) for name in context["player_names"]]

    for i, bot_type in enumerate(context.get("bot_types", []), 1):
        players.append(Player(f"Bot {i} ({bot_type})"))

    deck = Deck(draw=lambda pile: pile[0])

    return GameEngine(
        deck=deck,
        players=players,
        hit_stay_decider=lambda g, p: True,   # unused in step mode
        target_selector=lambda g, e, p: p,    # unused in step mode
        real_mode=real_mode,
    )


# ── Validators ───────────────────────────────────────────────────────

def _hit_stay_validator(text: str) -> str | None:
    if text.lower() in ("hit", "stay"):
        return None
    return "Type 'hit' or 'stay'."


def _card_input_validator(text: str) -> str | None:
    if text.lower() in _CARD_LOOKUP:
        return None
    return f"Unknown card. Valid: {_VALID_CARD_DISPLAY}"


def _make_target_validator(eligible_names: list[str]):
    lower_names = [n.lower() for n in eligible_names]

    def validator(text: str) -> str | None:
        if text.lower() in lower_names:
            return None
        return f"Choose a player: {', '.join(eligible_names)}"

    return validator


# ── Game Loop Node ───────────────────────────────────────────────────

class GameLoopNode(Node):
    """Drives gameplay by wrapping the engine's round() generator.

    Each yield from the generator becomes a prompt.  User input is
    translated back into the response the generator expects and fed
    via ``.send()``.
    """

    def __init__(self, engine, game_mode: str) -> None:
        self._engine = engine
        self._game_mode = game_mode
        self._gen = self._engine.round()
        self._current = next(self._gen)

    @property
    def prompt(self) -> Prompt:
        req = self._current

        if isinstance(req, HitStayRequest):
            return Prompt(
                instruction=f"{req.player.name}'s turn — hit or stay?",
                validator=_hit_stay_validator,
            )

        if isinstance(req, CardInputRequest):
            return Prompt(
                instruction=f"What card did {req.player.name} draw?",
                validator=_card_input_validator,
            )

        if isinstance(req, TargetRequest):
            names = [p.name for p in req.eligible]
            label = req.event.name.replace("_", " ").title()
            return Prompt(
                instruction=(
                    f"{req.source.name} drew {label}!\n"
                    f"Choose a target: {', '.join(names)}"
                ),
                validator=_make_target_validator(names),
            )

        if isinstance(req, CardDrawnEvent):
            return Prompt(
                instruction=(
                    f"{req.player.name} drew {req.card.name}. "
                    f"Press enter to continue."
                ),
                validator=lambda _: None,
            )

        if isinstance(req, PlayerBustedEvent):
            return Prompt(
                instruction=(
                    f"{req.player.name} busted! "
                    f"(drew duplicate {req.card.name}). Press enter."
                ),
                validator=lambda _: None,
            )

        if isinstance(req, RoundOverEvent):
            scores = "\n".join(
                f"  {p.name}: {p.score}" for p in self._engine.players
            )
            return Prompt(
                instruction=(
                    f"Round {req.round_number} complete!\n\n"
                    f"Scores:\n{scores}\n\n"
                    f"Press enter to continue."
                ),
                validator=lambda _: None,
            )

        # Fallback
        return Prompt(instruction="Press enter to continue.", validator=lambda _: None)

    def on_input(self, value: str, context: dict) -> Node | None:
        response = self._interpret(value)

        try:
            self._current = self._gen.send(response)
        except StopIteration:
            if self._engine.game_over:
                return GameOverNode(self._engine)
            # Start the next round
            self._gen = self._engine.round()
            self._current = next(self._gen)

        # Keep game screen focused on the relevant player
        self._sync_focus(context)

        return self

    # --- internal helpers ---------------------------------------------

    def _interpret(self, value: str):
        """Translate raw user input into the response the generator expects."""
        req = self._current

        if isinstance(req, HitStayRequest):
            return value.lower() == "hit"

        if isinstance(req, CardInputRequest):
            return _CARD_LOOKUP[value.lower()]

        if isinstance(req, TargetRequest):
            lower = value.lower()
            return next(p for p in req.eligible if p.name.lower() == lower)

        return None  # notifications

    def _sync_focus(self, context: dict) -> None:
        """Point the game screen's focus at the player in the current request."""
        screen = context.get("_game_screen")
        if not screen:
            return
        req = self._current
        player = getattr(req, "player", None) or getattr(req, "source", None)
        if player and player in self._engine.players:
            screen.set_focused(self._engine.players.index(player))
        screen.refresh()


# ── Game Over Node ───────────────────────────────────────────────────

class GameOverNode(Node):
    def __init__(self, engine) -> None:
        self._engine = engine

    @property
    def prompt(self) -> Prompt:
        ranked = sorted(self._engine.players, key=lambda p: p.score, reverse=True)
        scores = "\n".join(f"  {p.name}: {p.score}" for p in ranked)
        winner = self._engine.winner
        return Prompt(
            instruction=(
                f"Game over! {winner.name} wins with {winner.score} points!\n\n"
                f"Final scores:\n{scores}\n\n"
                f"Type 'home' to return to the main menu."
            ),
            validator=lambda t: None if t.lower() == "home" else "Type 'home'.",
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        from flop7.app.nodes.home import HomeNode
        context.pop("_game_screen", None)
        context.pop("_engine", None)
        context["_show_home"] = True
        return HomeNode()
