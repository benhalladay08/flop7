from __future__ import annotations

from flop7.app.nodes.base import Node
from flop7.app.prompt import Prompt


# ── Game mode ─────────────────────────────────────────────────────────

_GAME_MODE_TEXT = """\
How would you like to play?

- virtual: All players are on the same device; bots are supported.

- real: Use Flop 7 as a scorekeeper for a physical game.\

"""


def _game_mode_validator(text: str) -> str | None:
    if text.lower() in ("virtual", "real"):
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
        context["game_mode"] = value.lower()
        return PlayerCountNode()


# ── Player count ──────────────────────────────────────────────────────

def _player_count_validator(text: str) -> str | None:
    if not text.isdigit():
        return "Enter a number between 3 and 10."
    n = int(text)
    if n < 3 or n > 10:
        return f"Must be 3–10 players, got {n}."
    return None


class PlayerCountNode(Node):
    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction="How many players? (3–10)",
            validator=_player_count_validator,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        count = int(value)
        context["player_count"] = count
        context["player_names"] = []
        return PlayerNameNode(index=1, total=count)


def _player_name_validator(text: str) -> str | None:
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
            validator=_player_name_validator,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        updated = self._names + [value]
        context["player_names"] = updated
        if self._index < self._total:
            return PlayerNameNode(index=self._index + 1, total=self._total, names=updated)
        return SetupCompleteNode()


class SetupCompleteNode(Node):
    """Temporary terminal node confirming setup is done."""

    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction="Setup complete! (Game start not yet implemented. Type 'home' to return.)",
            validator=lambda t: None if t.lower() == "home" else "Type 'home'.",
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        from flop7.app.nodes.home import HomeNode  # avoid circular import
        return HomeNode()
