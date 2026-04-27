"""Simulation configuration and execution nodes."""

from __future__ import annotations

from flop7.app.nodes.base import Node
from flop7.app.prompt import Prompt
from flop7.app.simulation import (
    SimulationResults,
    run_game,
    sample_game_config,
    validate_sim_config,
)
from flop7.app.trackers import default_trackers
from flop7.bot.registry import Bot


# ── Helpers ──────────────────────────────────────────────────────────

def _available_bot_names() -> list[str]:
    """Bot names available for simulation (virtual mode, instantiable only)."""
    names = []
    for name in Bot.avaliable_bots:
        try:
            Bot.create(name, virtual=True)
            names.append(name)
        except (TypeError, ValueError):
            continue
    return names


def _parse_range(text: str, lo_bound: int, hi_bound: int) -> tuple[int, int] | str:
    """Parse 'M-N' or 'N' into a (min, max) tuple, or return an error string."""
    text = text.strip().replace(" ", "")
    if "-" in text:
        parts = text.split("-", 1)
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            return f"Enter a range like '{lo_bound}-{hi_bound}' or a single number."
        lo, hi = int(parts[0]), int(parts[1])
    elif text.isdigit():
        lo = hi = int(text)
    else:
        return f"Enter a range like '{lo_bound}-{hi_bound}' or a single number."

    if lo < lo_bound or hi > hi_bound:
        return f"Values must be between {lo_bound} and {hi_bound}."
    if lo > hi:
        return f"Minimum ({lo}) cannot exceed maximum ({hi})."
    return (lo, hi)


def _range_validator(lo_bound: int, hi_bound: int, allow_empty: bool = False):
    """Build a validator for range input."""
    def validator(text: str) -> str | None:
        if allow_empty and text.strip() == "":
            return None
        result = _parse_range(text, lo_bound, hi_bound)
        if isinstance(result, str):
            return result
        return None
    return validator


def _build_config_lines(context: dict) -> list[str]:
    """Build display lines for the configuration panel from context."""
    lines: list[str] = []
    player_range = context.get("sim_player_range")
    if player_range:
        lines.append(f"Players per game: {player_range[0]}-{player_range[1]}")

    bot_ranges = context.get("sim_bot_ranges", {})
    if bot_ranges:
        lines.append("")
        lines.append("Bots:")
        for name, (lo, hi) in bot_ranges.items():
            lines.append(f"  {name}: {lo}-{hi}")

    game_count = context.get("sim_game_count")
    if game_count is not None:
        lines.append("")
        lines.append(f"Games: {game_count:,}")

    return lines


def _update_screen(context: dict) -> None:
    """Push current config to the simulate screen if it exists."""
    screen = context.get("_sim_screen")
    if screen:
        screen.update_config(_build_config_lines(context))


# ── Player count range ───────────────────────────────────────────────

_PLAYER_COUNT_TEXT = """\
How many players per game?

Enter a range (e.g., 3-10) or press Enter for the default (3-10).
Players must be between 3 and 10.\
"""


class SimPlayerCountNode(Node):
    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=_PLAYER_COUNT_TEXT,
            validator=_range_validator(3, 10, allow_empty=True),
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        if value.strip() == "":
            context["sim_player_range"] = (3, 10)
        else:
            context["sim_player_range"] = _parse_range(value, 3, 10)

        context["sim_bot_ranges"] = {}
        _update_screen(context)
        bot_names = _available_bot_names()
        return SimBotConfigNode(index=0, bot_names=bot_names, ranges={})


# ── Bot configuration (loops per bot type) ───────────────────────────

class SimBotConfigNode(Node):
    def __init__(
        self, index: int, bot_names: list[str], ranges: dict[str, tuple[int, int]],
    ) -> None:
        self._index = index
        self._bot_names = bot_names
        self._ranges = ranges

    def _build_instruction(self) -> str:
        lines = ["Configure bot counts per game.\n"]
        lines.append("Bots:")
        for i, name in enumerate(self._bot_names):
            if i < self._index:
                lo, hi = self._ranges[name]
                lines.append(f"  {name}: {lo}-{hi}")
            elif i == self._index:
                lines.append(f"  {name}: ?")
            else:
                lines.append(f"  {name}:")
        current = self._bot_names[self._index]
        lines.append(
            f"\nHow many {current} bots per game? "
            f"Enter a range (e.g., 0-10) or press Enter for default (0-10)."
        )
        return "\n".join(lines)

    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=self._build_instruction(),
            validator=_range_validator(0, 10, allow_empty=True),
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        current = self._bot_names[self._index]
        if value.strip() == "":
            rng = (0, 10)
        else:
            rng = _parse_range(value, 0, 10)
        updated = {**self._ranges, current: rng}
        context["sim_bot_ranges"] = updated
        _update_screen(context)

        if self._index + 1 < len(self._bot_names):
            return SimBotConfigNode(
                index=self._index + 1,
                bot_names=self._bot_names,
                ranges=updated,
            )
        return SimGameCountNode()


# ── Game count ───────────────────────────────────────────────────────

_GAME_COUNT_TEXT = """\
How many games to simulate? (1-100,000)\
"""


def _game_count_validator(text: str) -> str | None:
    text = text.strip().replace(",", "")
    if not text.isdigit():
        return "Enter a positive whole number (max 100,000)."
    n = int(text)
    if n < 1 or n > 100_000:
        return "Must be between 1 and 100,000."
    return None


class SimGameCountNode(Node):
    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=_GAME_COUNT_TEXT,
            validator=_game_count_validator,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        context["sim_game_count"] = int(value.strip().replace(",", ""))
        _update_screen(context)
        return SimConfirmNode()


# ── Confirm & validate ───────────────────────────────────────────────

class SimConfirmNode(Node):
    def __init__(self, error: str | None = None) -> None:
        self._error = error

    @property
    def prompt(self) -> Prompt:
        if self._error:
            return Prompt(
                instruction=(
                    f"Invalid configuration: {self._error}\n\n"
                    f"Press Enter to reconfigure."
                ),
                validator=lambda _: None,
            )
        return Prompt(
            instruction="Configuration complete! Press Enter to start the simulation.",
            validator=lambda _: None,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        if self._error:
            return SimPlayerCountNode()

        player_range = context["sim_player_range"]
        bot_ranges = context["sim_bot_ranges"]
        error = validate_sim_config(player_range, bot_ranges)
        if error:
            return SimConfirmNode(error=error)

        return SimRunNode(
            player_range=player_range,
            bot_ranges=bot_ranges,
            total=context["sim_game_count"],
        )


# ── Simulation runner (batched with auto-advance) ────────────────────

BATCH_SIZE = 50


class SimRunNode(Node):
    def __init__(
        self,
        player_range: tuple[int, int],
        bot_ranges: dict[str, tuple[int, int]],
        total: int,
        results: SimulationResults | None = None,
        completed: int = 0,
    ) -> None:
        self._player_range = player_range
        self._bot_ranges = bot_ranges
        self._total = total
        self._results = results or SimulationResults(trackers=default_trackers())
        self._completed = completed

    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=(
                f"Running simulation... {self._completed:,}/{self._total:,}. "
                f"Type 'cancel' to abort."
            ),
            validator=lambda _: None,
            auto_advance_ms=1,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        screen = context.get("_sim_screen")

        if value.strip().lower() == "cancel":
            if screen:
                screen.show_results(self._results)
            return SimDoneNode(self._results, cancelled=True)

        end = min(self._completed + BATCH_SIZE, self._total)
        for _ in range(self._completed, end):
            config = sample_game_config(self._player_range, self._bot_ranges)
            engine = run_game(config, trackers=self._results.trackers)
            self._results.record(config, engine)
        self._completed = end

        if screen:
            screen.update_progress(self._completed, self._total)

        if self._completed >= self._total:
            if screen:
                screen.show_results(self._results)
            return SimDoneNode(self._results)

        return SimRunNode(
            player_range=self._player_range,
            bot_ranges=self._bot_ranges,
            total=self._total,
            results=self._results,
            completed=self._completed,
        )


# ── Done ─────────────────────────────────────────────────────────────

class SimDoneNode(Node):
    def __init__(
        self, results: SimulationResults, cancelled: bool = False,
    ) -> None:
        self._results = results
        self._cancelled = cancelled

    @property
    def prompt(self) -> Prompt:
        if self._cancelled:
            msg = (
                f"Simulation cancelled after {self._results.total_games:,} games. "
                f"Type 'home' to return to the main menu."
            )
        else:
            msg = (
                "Simulation complete! "
                "Type 'home' to return to the main menu."
            )
        return Prompt(
            instruction=msg,
            validator=lambda t: None if t.lower() == "home" else "Type 'home'.",
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        from flop7.app.nodes.home import HomeNode

        context.pop("_sim_screen", None)
        context.pop("sim_player_range", None)
        context.pop("sim_bot_ranges", None)
        context.pop("sim_game_count", None)
        context["_show_home"] = True
        return HomeNode()
