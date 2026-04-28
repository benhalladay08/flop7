from __future__ import annotations

from flop7.app.nodes.base import Node
from flop7.app.prompt import Prompt
from flop7.bot.registry import Bot

# ── Helpers ───────────────────────────────────────────────────────────────────────


def _available_bot_names(game_mode: str) -> list[str]:
    """Return bot model names valid for the given game mode."""
    names = []
    for name, cls in Bot.available_bots.items():
        if game_mode == "virtual" or not cls.virtual_only:
            names.append(name)
    return names


def _normalized_name(name: str) -> str:
    """Normalize player names for uniqueness checks and target input."""
    return name.strip().casefold()


def _unique_name(base: str, existing_names: list[str]) -> str:
    """Return a player name that does not collide with existing names."""
    existing = {_normalized_name(name) for name in existing_names}
    if _normalized_name(base) not in existing:
        return base

    suffix = 2
    while True:
        candidate = f"{base} #{suffix}"
        if _normalized_name(candidate) not in existing:
            return candidate
        suffix += 1


# ── Game mode ────────────────────────────────────────────────────────────────

_GAME_MODE_TEXT = """\
How would you like to play?

- virtual: All players are on the same device; bots are supported.

- real: Use Flop 7 as a scorekeeper for a physical game.\
"""


def _game_mode_validator(text: str) -> str | None:
    if text.strip().lower() in ("virtual", "real"):
        return None
    return "Type 'virtual' or 'real'."


class GameModeNode(Node):
    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=_GAME_MODE_TEXT,
            validator=_game_mode_validator,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        context["game_mode"] = value.strip().lower()
        return PlayerCountNode()


# ── Player count ─────────────────────────────────────────────────────────

_PLAYER_COUNT_TEXT = """\
How many human players? (1–10)

Note: a game requires at least 3 participants in total. If you select \
fewer than 3 human players you will need to add bots to make up the \
difference. If you select 10 human players, no bots can be added.\
"""


def _player_count_validator(text: str) -> str | None:
    text = text.strip()
    if not text.isdigit():
        return "Enter a whole number between 1 and 10."
    n = int(text)
    if n < 1 or n > 10:
        return f"Must be 1–10 players, got {n}."
    return None


class PlayerCountNode(Node):
    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=_PLAYER_COUNT_TEXT,
            validator=_player_count_validator,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        count = int(value.strip())
        context["player_count"] = count
        context["player_names"] = []
        return PlayerNameNode(index=1, total=count)


# ── Player names ─────────────────────────────────────────────────────────


def _make_player_name_validator(existing_names: list[str]):
    existing = {_normalized_name(name) for name in existing_names}

    def validator(text: str) -> str | None:
        error = _player_name_validator(text)
        if error is not None:
            return error
        if _normalized_name(text) in existing:
            return "Player names must be unique."
        return None

    return validator


def _player_name_validator(text: str) -> str | None:
    text = text.strip()
    if not text:
        return "Name cannot be empty."
    if len(text) > 20:
        return "Name must be 20 characters or fewer."
    return None


class PlayerNameNode(Node):
    def __init__(self, index: int, total: int, names: list[str] | None = None) -> None:
        self._index = index
        self._total = total
        self._names: list[str] = names or []

    def _build_instruction(self) -> str:
        roster = "Players:\n"
        for i in range(1, self._total + 1):
            name = self._names[i - 1] if i - 1 < len(self._names) else ""
            roster += f"{i}. {name}\n"
        roster += f"\nInput the name of player {self._index}:"
        return roster

    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=self._build_instruction(),
            validator=_make_player_name_validator(self._names),
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        updated = self._names + [value.strip()]
        context["player_names"] = updated
        if self._index < self._total:
            return PlayerNameNode(
                index=self._index + 1,
                total=self._total,
                names=updated,
            )

        # All human players named — move to bot selection
        player_count = self._total
        max_bots = 10 - player_count
        if max_bots == 0:
            # 10 human players: skip bot steps entirely
            context["bot_count"] = 0
            context["bot_types"] = []
            return SetupCompleteNode()

        return BotCountNode(
            player_count=player_count,
            game_mode=context.get("game_mode", "virtual"),
        )


# ── Bot count ────────────────────────────────────────────────────────────────


def _make_bot_count_validator(min_bots: int, max_bots: int):
    def validator(text: str) -> str | None:
        text = text.strip()
        if not text.isdigit():
            return f"Enter a number between {min_bots} and {max_bots}."
        n = int(text)
        if n < min_bots or n > max_bots:
            return f"Must be {min_bots}–{max_bots} bots, got {n}."
        return None

    return validator


class BotCountNode(Node):
    def __init__(self, player_count: int, game_mode: str) -> None:
        self._player_count = player_count
        self._game_mode = game_mode
        self._min_bots = max(0, 3 - player_count)
        self._max_bots = 10 - player_count

    def _build_instruction(self) -> str:
        lines = [f"How many bots? ({self._min_bots}–{self._max_bots})"]
        if self._min_bots > 0:
            lines.append(
                f"\nWith {self._player_count} human player(s), you need at least "
                f"{self._min_bots} bot(s) to reach the 3-player minimum."
            )
        else:
            lines.append("\nEnter 0 to play without bots.")
        return "\n".join(lines)

    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=self._build_instruction(),
            validator=_make_bot_count_validator(self._min_bots, self._max_bots),
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        count = int(value.strip())
        context["bot_count"] = count
        context["bot_types"] = []
        if count == 0:
            return SetupCompleteNode()
        return BotTypeNode(
            index=1,
            total=count,
            game_mode=self._game_mode,
            types=[],
        )


# ── Bot type selection ─────────────────────────────────────────────────────────────


def _make_bot_type_validator(valid_names: list[str]):
    lower_names = [n.lower() for n in valid_names]
    options = ", ".join(f"'{n}'" for n in valid_names)

    def validator(text: str) -> str | None:
        if text.strip().lower() in lower_names:
            return None
        return f"Choose one of: {options}."

    return validator


class BotTypeNode(Node):
    def __init__(self, index: int, total: int, game_mode: str, types: list[str]) -> None:
        self._index = index
        self._total = total
        self._game_mode = game_mode
        self._types = types
        self._valid_names = _available_bot_names(game_mode)

    def _build_instruction(self) -> str:
        lines = ["Bots:\n"]
        for i in range(1, self._total + 1):
            t = self._types[i - 1] if i - 1 < len(self._types) else ""
            lines.append(f"{i}. {t}")
        lines.append(f"\nSelect the model for bot {self._index} of {self._total}:")
        lines.append("\nAvailable models:")
        for name, cls in Bot.available_bots.items():
            if name in self._valid_names:
                tag = " (virtual only)" if cls.virtual_only else ""
                lines.append(f"  - {name}{tag}")
        return "\n".join(lines)

    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=self._build_instruction(),
            validator=_make_bot_type_validator(self._valid_names),
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        canonical = next(n for n in self._valid_names if n.lower() == value.strip().lower())
        updated = self._types + [canonical]
        context["bot_types"] = updated
        if self._index < self._total:
            return BotTypeNode(
                index=self._index + 1,
                total=self._total,
                game_mode=self._game_mode,
                types=updated,
            )
        return SetupCompleteNode()


# ── Setup complete ────────────────────────────────────────────────────────────────


class SetupCompleteNode(Node):
    """Builds the engine from setup context and starts the game."""

    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction="Setup complete! Press enter to start the game.",
            validator=lambda t: None,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        from flop7.app.nodes.game import GameRoundNode, _build_engine

        engine = _build_engine(context)
        context["_engine"] = engine
        context["_show_game"] = engine
        return GameRoundNode(
            engine,
            context["game_mode"],
            context["_bot_controller"],
        )
