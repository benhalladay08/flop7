"""Game-flow nodes for the orchestrator.

The game flow is driven by the engine's ``round()`` generator. ``GameRoundNode``
is a dispatcher that owns the generator and routes each yielded request/event
to a focused child node. Child nodes never hold the generator directly; on
input they return a response value back to ``GameRoundNode.advance()``, which
performs the ``.send()`` and dispatches the next yielded value.

Notification nodes (events) are auto-advanced after 2 seconds via
``Prompt.auto_advance_ms``; the user can also press Enter to advance early.
"""

from __future__ import annotations

from flop7.app.nodes.base import Node
from flop7.app.prompt import Prompt
from flop7.bot.controller import BotController
from flop7.core.classes.cards import (
    ALL_CARDS,
    FLIP_THREE,
    FREEZE,
    SECOND_CHANCE,
    TIMES_TWO,
)
from flop7.core.engine.requests import (
    CardDrawnEvent,
    CardDrawRequest,
    Flip7Event,
    FlipThreeResolvedEvent,
    FlipThreeStartEvent,
    FreezeEvent,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
    SecondChanceEvent,
    TargetRequest,
)
from flop7.core.enum.decisions import TargetEvent

AUTO_ADVANCE_MS = 2000


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
    from flop7.app.nodes.setup import _normalized_name, _unique_name
    from flop7.bot.registry import Bot
    from flop7.core.classes.deck import Deck
    from flop7.core.classes.player import Player
    from flop7.core.engine.engine import GameEngine

    game_mode = context["game_mode"]
    real_mode = game_mode == "real"
    virtual = game_mode == "virtual"

    human_names = context["player_names"]
    normalized_human_names = {_normalized_name(name) for name in human_names}
    if len(normalized_human_names) != len(human_names):
        raise ValueError("Player names must be unique.")

    players = [Player(name) for name in human_names]
    bots_by_index = {}

    for i, bot_type in enumerate(context.get("bot_types", []), 1):
        bot = Bot.create(bot_type, virtual=virtual)
        bot_index = len(players)
        bots_by_index[bot_index] = bot
        bot_name = _unique_name(
            f"Bot {i} ({bot_type})",
            [player.name for player in players],
        )
        players.append(Player(bot_name))

    bot_controller = BotController(bots_by_index)
    context["_bot_controller"] = bot_controller
    deck = Deck()

    def card_provider(game, player):
        if game.real_mode:
            raise ValueError("Real-mode card draws must be provided by the UI.")
        return game.deck.deal()

    return GameEngine(
        deck=deck,
        players=players,
        card_provider=card_provider,
        hit_stay_decider=bot_controller.hit_stay,
        target_selector=bot_controller.target_selector,
        real_mode=real_mode,
    )


# ── Validators ───────────────────────────────────────────────────────


def _hit_stay_validator(text: str) -> str | None:
    if text.strip().lower() in ("hit", "stay"):
        return None
    return "Type 'hit' or 'stay'."


def _card_input_validator(text: str) -> str | None:
    if text.strip().lower() in _CARD_LOOKUP:
        return None
    return f"Unknown card. Valid: {_VALID_CARD_DISPLAY}"


def _make_target_validator(eligible_names: list[str]):
    lower_names = [n.lower() for n in eligible_names]

    def validator(text: str) -> str | None:
        if text.strip().lower() in lower_names:
            return None
        return f"Choose a player: {', '.join(eligible_names)}"

    return validator


def _action_label(event: TargetEvent) -> str:
    return event.name.replace("_", " ").title()


# ── Round-level dispatcher ───────────────────────────────────────────


class GameRoundNode(Node):
    """Owns the engine's ``round()`` generator and dispatches yielded
    requests/events to focused child nodes.

    This node has no prompt of its own; ``is_dispatcher = True`` tells the
    orchestrator to call :meth:`dispatch` to obtain a real prompt-bearing
    node before showing anything.
    """

    is_dispatcher = True

    def __init__(self, engine, game_mode: str, bot_controller: BotController) -> None:
        self._engine = engine
        self._game_mode = game_mode
        self._bots = bot_controller
        self._gen = engine.round()
        self._current_event = next(self._gen)

    # The orchestrator never reaches these because ``is_dispatcher`` short-
    # circuits prompt rendering, but they must exist for the ABC contract.
    @property
    def prompt(self) -> Prompt:  # pragma: no cover - never invoked
        raise RuntimeError("GameRoundNode is a dispatcher and has no prompt.")

    def on_input(self, value: str, context: dict) -> Node | None:  # pragma: no cover
        raise RuntimeError("GameRoundNode is a dispatcher and does not accept input.")

    # --- public API ---------------------------------------------------

    def dispatch(self, context: dict | None = None) -> Node:
        """Return the child node that should handle the current event."""
        if context is None:
            context = {}
        event = self._current_event
        engine = self._engine
        bots = self._bots

        match event:
            case HitStayRequest(player=p) if not bots.has_bot(engine, p):
                return HitStayNode(self, p)
            case HitStayRequest(player=p):
                return BotDecisionNode(self, p)
            case CardDrawRequest(player=p):
                return DrawCardNode(self, p)
            case CardDrawnEvent(player=p, card=c):
                return CardDrawnNode(self, p, c)
            case TargetRequest():
                return TargetSelectNode(self, event)
            case FreezeEvent(target=t):
                return SpecialResolvedNode(self, f"{t.name} is frozen!")
            case SecondChanceEvent(target=t):
                return SpecialResolvedNode(
                    self,
                    f"{t.name} received Second Chance.",
                )
            case FlipThreeStartEvent(source=s, target=t):
                return SpecialResolvedNode(
                    self,
                    f"{s.name} plays Flip Three on {t.name}!",
                )
            case FlipThreeResolvedEvent(target=t):
                return SpecialResolvedNode(self, f"Flip Three resolved for {t.name}.")
            case PlayerBustedEvent(player=p, card=c):
                return BustNode(self, p, c)
            case Flip7Event(player=p):
                return Flip7Node(self, p)
            case RoundOverEvent(round_number=n):
                return RoundOverNode(self, n)

        raise RuntimeError(f"Unhandled engine event: {event!r}")

    def advance(self, response, context: dict) -> Node:
        """Send *response* into the generator and dispatch the next event.

        On ``StopIteration`` either start a fresh round or transition to
        the game-over node.
        """
        try:
            self._current_event = self._gen.send(response)
        except StopIteration:
            if self._engine.game_over:
                return GameOverNode(self._engine)
            self._gen = self._engine.round()
            self._current_event = next(self._gen)

        self._sync_focus(context)
        next_node = self.dispatch(context)
        # Resolve nested dispatchers (defensive — currently only this one).
        while next_node.is_dispatcher:
            next_node = next_node.dispatch(context)
        return next_node

    # --- helpers ------------------------------------------------------

    @property
    def engine(self):
        return self._engine

    @property
    def bot_controller(self) -> BotController:
        return self._bots

    @property
    def game_mode(self) -> str:
        return self._game_mode

    def _sync_focus(self, context: dict) -> None:
        """Point the game screen's focus at the player in the current event."""
        screen = context.get("_game_screen")
        if not screen:
            return
        event = self._current_event
        player = getattr(event, "player", None) or getattr(event, "source", None)
        if isinstance(event, CardDrawnEvent):
            screen.set_pending_draw(event.player, event.card)
        elif isinstance(event, TargetRequest):
            screen.clear_pending_draw_unless(event.source)
        else:
            screen.clear_pending_draw()
        if player and player in self._engine.players:
            screen.set_focused(self._engine.players.index(player))
        screen.refresh()


# ── Notification (auto-advance) nodes ────────────────────────────────


class _NotificationNode(Node):
    """Base for nodes that show a message and auto-advance after 2s."""

    def __init__(self, round_node: GameRoundNode, message: str) -> None:
        self._round = round_node
        self._message = message

    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=self._message,
            validator=lambda _: None,
            auto_advance_ms=AUTO_ADVANCE_MS,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        return self._round.advance(None, context)


class CardDrawnNode(_NotificationNode):
    def __init__(self, round_node: GameRoundNode, player, card) -> None:
        super().__init__(round_node, f"{player.name} drew {card.name}.")


class BustNode(_NotificationNode):
    def __init__(self, round_node: GameRoundNode, player, card) -> None:
        super().__init__(
            round_node,
            f"{player.name} busted! (drew duplicate {card.name}).",
        )


class Flip7Node(_NotificationNode):
    def __init__(self, round_node: GameRoundNode, player) -> None:
        super().__init__(round_node, f"{player.name} achieved Flip 7!")


class SpecialResolvedNode(_NotificationNode):
    """Generic notification for freeze / second-chance / flip-three events."""


# ── Bot decision (notification with pre-computed answer) ─────────────


class BotDecisionNode(Node):
    """Display and auto-advance the bot's hit/stay decision.

    The decision is pre-computed at construction time so it can be displayed
    to the user. On advance the same value is sent into the engine generator.
    """

    def __init__(self, round_node: GameRoundNode, player) -> None:
        self._round = round_node
        self._player = player
        self._decision = round_node.bot_controller.hit_stay(
            round_node.engine,
            player,
        )

    @property
    def prompt(self) -> Prompt:
        action = "HIT" if self._decision else "STAY"
        return Prompt(
            instruction=f"{self._player.name} chose to {action}.",
            validator=lambda _: None,
            auto_advance_ms=AUTO_ADVANCE_MS,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        return self._round.advance(self._decision, context)


# ── Input nodes ──────────────────────────────────────────────────────


class HitStayNode(Node):
    """Prompt a human player to hit or stay."""

    def __init__(self, round_node: GameRoundNode, player) -> None:
        self._round = round_node
        self._player = player

    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=f"{self._player.name}'s turn — hit or stay?",
            validator=_hit_stay_validator,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        return self._round.advance(value.strip().lower() == "hit", context)


class DrawCardNode(Node):
    """Resolve a card draw request for real or virtual play."""

    def __init__(self, round_node: GameRoundNode, player) -> None:
        self._round = round_node
        self._player = player
        self.is_dispatcher = not round_node.engine.real_mode

    @property
    def prompt(self) -> Prompt:
        if not self._round.engine.real_mode:
            raise RuntimeError("Virtual draw nodes are resolved by dispatch().")
        return Prompt(
            instruction=(
                f"What card did {self._player.name} draw?\n" f"Valid: {_VALID_CARD_DISPLAY}"
            ),
            validator=_card_input_validator,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        card = _CARD_LOOKUP[value.strip().lower()]
        return self._round.advance(card, context)

    def dispatch(self, context: dict | None = None) -> Node:
        if context is None:
            context = {}
        card = self._round.engine.card_provider(self._round.engine, self._player)
        return self._round.advance(card, context)


class TargetSelectNode(Node):
    """Handle ``TargetRequest`` for both human and bot sources.

    Human sources prompt for input; bot sources pre-compute the target,
    show a brief notification, and auto-advance.
    """

    def __init__(self, round_node: GameRoundNode, request: TargetRequest) -> None:
        self._round = round_node
        self._request = request
        self._is_bot = round_node.bot_controller.has_bot(
            round_node.engine,
            request.source,
        )
        self._bot_target = None
        if self._is_bot:
            self._bot_target = round_node.bot_controller.target_selector(
                round_node.engine,
                request.event,
                request.source,
                request.eligible,
            )

    @property
    def prompt(self) -> Prompt:
        req = self._request
        label = _action_label(req.event)
        if self._is_bot:
            return Prompt(
                instruction=(
                    f"{req.source.name} drew {label}!\n"
                    f"{req.source.name} targets {self._bot_target.name}."
                ),
                validator=lambda _: None,
                auto_advance_ms=AUTO_ADVANCE_MS,
            )
        names = [p.name for p in req.eligible]
        return Prompt(
            instruction=(
                f"{req.source.name} drew {label}!\n" f"Choose a target: {', '.join(names)}"
            ),
            validator=_make_target_validator(names),
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        if self._is_bot:
            return self._round.advance(self._bot_target, context)
        lower = value.strip().lower()
        target = next(p for p in self._request.eligible if p.name.lower() == lower)
        return self._round.advance(target, context)


# ── Round / game over ────────────────────────────────────────────────


class RoundOverNode(Node):
    """Display the scoreboard and wait for Enter (no auto-advance)."""

    def __init__(self, round_node: GameRoundNode, round_number: int) -> None:
        self._round = round_node
        self._round_number = round_number

    @property
    def prompt(self) -> Prompt:
        scores = "\n".join(f"  {p.name}: {p.score}" for p in self._round.engine.players)
        return Prompt(
            instruction=(
                f"Round {self._round_number} complete!\n\n"
                f"Scores:\n{scores}\n\n"
                f"Press enter to continue."
            ),
            validator=lambda _: None,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        return self._round.advance(None, context)


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
            validator=lambda t: (None if t.strip().lower() == "home" else "Type 'home'."),
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        from flop7.app.nodes.home import HomeNode

        context.pop("_game_screen", None)
        context.pop("_engine", None)
        context.pop("_bot_controller", None)
        context["_show_home"] = True
        return HomeNode()
