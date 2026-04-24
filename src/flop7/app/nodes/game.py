from __future__ import annotations

from flop7.app.nodes.base import Node
from flop7.app.prompt import Prompt
from flop7.bot.controller import BotController
from flop7.core.classes.cards import ALL_CARDS, FLIP_THREE, FREEZE, SECOND_CHANCE, TIMES_TWO
from flop7.core.engine.requests import (
    CardDrawnEvent,
    CardInputRequest,
    Flip7Event,
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
    from flop7.bot.registry import Bot
    from flop7.core.classes.deck import Deck
    from flop7.core.classes.player import Player
    from flop7.core.engine.engine import GameEngine

    game_mode = context["game_mode"]
    real_mode = game_mode == "real"
    virtual = game_mode == "virtual"

    players = [Player(name) for name in context["player_names"]]
    bots_by_index = {}

    for i, bot_type in enumerate(context.get("bot_types", []), 1):
        bot = Bot.create(bot_type, virtual=virtual)
        bot_index = len(players)
        bots_by_index[bot_index] = bot
        players.append(Player(f"Bot {i} ({bot_type})"))

    bot_controller = BotController(bots_by_index)
    context["_bot_controller"] = bot_controller
    deck = Deck()

    return GameEngine(
        deck=deck,
        players=players,
        hit_stay_decider=bot_controller.hit_stay,
        target_selector=bot_controller.target_selector,
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

    def __init__(
        self,
        engine,
        game_mode: str,
        bot_controller: BotController | None = None,
    ) -> None:
        self._engine = engine
        self._game_mode = game_mode
        self._bot_controller = bot_controller or BotController()
        self._gen = self._engine.round()
        self._current = next(self._gen)
        self._bot_decision: bool | None = None
        self._bot_target = None

    @property
    def prompt(self) -> Prompt:
        req = self._current

        if isinstance(req, HitStayRequest):
            if self._bot_controller.has_bot(self._engine, req.player):
                decision = self._bot_controller.hit_stay(self._engine, req.player)
                self._bot_decision = decision
                action = "HIT" if decision else "STAY"
                return Prompt(
                    instruction=f"{req.player.name} chose to {action} — press enter",
                    validator=lambda _: None,
                )
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
            if self._bot_controller.has_bot(self._engine, req.source):
                target = self._bot_controller.target_selector(
                    self._engine, req.event, req.source, req.eligible,
                )
                self._bot_target = target
                label = req.event.name.replace("_", " ").title()
                return Prompt(
                    instruction=(
                        f"{req.source.name} drew {label}!\n"
                        f"{req.source.name} targets {target.name} — press enter"
                    ),
                    validator=lambda _: None,
                )
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

        if isinstance(req, Flip7Event):
            return Prompt(
                instruction=(
                    f"{req.player.name} achieved Flip 7! "
                    f"Round over — press enter."
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
            if self._bot_controller.has_bot(self._engine, req.player):
                decision = self._bot_decision
                self._bot_decision = None
                return decision
            return value.lower() == "hit"

        if isinstance(req, CardInputRequest):
            return _CARD_LOOKUP[value.lower()]

        if isinstance(req, TargetRequest):
            if self._bot_controller.has_bot(self._engine, req.source):
                target = self._bot_target
                self._bot_target = None
                return target
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
        context.pop("_bot_controller", None)
        context["_show_home"] = True
        return HomeNode()
