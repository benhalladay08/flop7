from __future__ import annotations

from typing import TYPE_CHECKING

import urwid

from flop7.tui.widgets.card_detail import CardDetailPane
from flop7.tui.widgets.player_list import PlayerListWidget, player_status

if TYPE_CHECKING:
    from flop7.core.engine.engine import GameEngine

WIDE_THRESHOLD = 120


class GameScreen(urwid.WidgetWrap):
    """Game screen with automatic compact / wide layout switching.

    Compact mode (< 120 cols):
        Full-width player list with inline card notation.

    Wide mode (>= 120 cols):
        Compact player sidebar on the left, large ASCII art card
        detail pane for the focused player on the right.

    The layout mode is re-evaluated on every render pass so the screen
    adapts when the terminal is resized.
    """

    def __init__(self, engine: GameEngine, focused_idx: int = 0) -> None:
        self._engine = engine
        self._focused_idx = focused_idx
        self._last_mode: str | None = None
        super().__init__(urwid.SolidFill(" "))

    # --- public API ---------------------------------------------------

    @property
    def _players(self):
        return self._engine.players

    def set_focused(self, idx: int) -> None:
        """Change the focused player and force a layout rebuild."""
        self._focused_idx = idx
        self._last_mode = None
        self._invalidate()

    def refresh(self) -> None:
        """Force a layout rebuild on the next render pass."""
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

    # --- layout builders ----------------------------------------------

    def _build_compact(self) -> urwid.Widget:
        return PlayerListWidget(
            self._players,
            focused_idx=self._focused_idx,
            dealer_idx=self._engine.dealer_index,
            compact=False,
        )

    def _build_wide(self) -> urwid.Widget:
        focused = (
            self._players[self._focused_idx] if self._players else None
        )

        player_list = PlayerListWidget(
            self._players,
            focused_idx=self._focused_idx,
            dealer_idx=self._engine.dealer_index,
            compact=True,
        )

        detail_title = ""
        detail_cards: list = []
        if focused:
            status = player_status(focused)
            detail_title = f"{focused.name} ({status})"
            detail_cards = focused.hand

        card_detail = CardDetailPane(
            cards=detail_cards,
            player_name=detail_title,
        )

        return urwid.Columns([
            ("weight", 1, player_list),
            ("weight", 3, card_detail),
        ])
