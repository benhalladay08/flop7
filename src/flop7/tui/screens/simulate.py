"""Simulate screen: configuration panel on the left, results on the right."""

from __future__ import annotations

from typing import TYPE_CHECKING

import urwid

if TYPE_CHECKING:
    from flop7.simulation import SimulationResults

WIDE_THRESHOLD = 120


class SimulateScreen(urwid.WidgetWrap):
    """Two-panel simulation screen.

    Left panel shows configuration as it is built up.
    Right panel shows a progress bar during the run, then final results.

    In compact mode (< 120 cols) the panels stack vertically.
    """

    def __init__(self) -> None:
        self._config_walker = urwid.SimpleFocusListWalker(
            [urwid.Text(("dimmed", "Waiting for configuration..."))]
        )
        self._config_box = urwid.ListBox(self._config_walker)

        self._status_text = urwid.Text(("dimmed", "Waiting for configuration..."))
        self._progress_bar = urwid.ProgressBar("dimmed", "active", current=0, done=1)
        self._results_text = urwid.Text("")

        self._results_pile = urwid.Pile([
            self._status_text,
            urwid.Divider(),
            self._results_text,
        ])
        self._results_box = urwid.Filler(self._results_pile, valign="top")

        self._last_mode: str | None = None
        super().__init__(urwid.SolidFill(" "))

    # --- public API ---------------------------------------------------

    def update_config(self, lines: list[str]) -> None:
        """Replace the configuration panel contents."""
        self._config_walker.clear()
        for line in lines:
            self._config_walker.append(urwid.Text(line))
        self._invalidate()

    def update_progress(self, completed: int, total: int) -> None:
        """Update the progress bar and status text during a simulation run."""
        self._progress_bar.set_completion(completed)
        self._progress_bar.done = total
        pct = completed / total * 100 if total > 0 else 0
        self._status_text.set_text(
            f"Running simulation... {completed:,}/{total:,} ({pct:.0f}%)"
        )
        self._results_pile.contents = [
            (self._status_text, ("pack", None)),
            (urwid.Divider(), ("pack", None)),
            (self._progress_bar, ("pack", None)),
        ]
        self._last_mode = None
        self._invalidate()

    def show_results(self, results: SimulationResults) -> None:
        """Replace the progress bar with the final results table."""
        self._status_text.set_text(("active", "Simulation complete!"))

        lines: list[str] = []
        lines.append("")
        lines.append("Win Rate per Bot Seat:")

        bot_types = sorted(results.bot_entries_by_type.keys())
        if not bot_types:
            bot_types = sorted(results.wins_by_type.keys())
        max_name = max((len(n) for n in bot_types), default=0)
        for name in bot_types:
            wins = results.wins_by_type.get(name, 0)
            entries = results.bot_entries_by_type.get(name, 0)
            rate = results.win_rate(name)
            lines.append(
                f"  {name:<{max_name}}  {rate:5.1f}%  "
                f"({wins:,} wins / {entries:,} entries)"
            )

        lines.append("")
        lines.append(f"Avg Game Length:   {results.avg_game_length:.1f} rounds")
        lines.append(f"Avg Winning Score: {results.avg_winning_score:.1f}")

        for tracker in getattr(results, "trackers", ()):
            lines.append("")
            lines.append(f"{tracker.label}:")
            for line in tracker.format_results():
                lines.append(f"  {line}")

        self._results_text.set_text("\n".join(lines))
        self._results_pile.contents = [
            (self._status_text, ("pack", None)),
            (urwid.Divider(), ("pack", None)),
            (self._results_text, ("pack", None)),
        ]
        self._last_mode = None
        self._invalidate()

    # --- render-time layout selection ---------------------------------

    def render(self, size, focus=False):
        maxcol = size[0] if size else 80
        mode = "wide" if maxcol >= WIDE_THRESHOLD else "compact"

        if mode != self._last_mode:
            self._last_mode = mode
            if mode == "wide":
                self._w = self._build_wide()
            else:
                self._w = self._build_compact()

        return super().render(size, focus)

    def _build_wide(self) -> urwid.Widget:
        left = urwid.LineBox(self._config_box, title="Configuration")
        right = urwid.LineBox(self._results_box, title="Results")
        return urwid.Columns([
            ("weight", 1, left),
            ("weight", 2, right),
        ])

    def _build_compact(self) -> urwid.Widget:
        left = urwid.LineBox(
            urwid.BoxAdapter(self._config_box, 8), title="Configuration",
        )
        right = urwid.LineBox(self._results_box, title="Results")
        return urwid.Pile([
            ("pack", left),
            right,
        ])
