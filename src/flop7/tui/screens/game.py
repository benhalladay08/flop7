from __future__ import annotations

from typing import TYPE_CHECKING

import urwid

from flop7.tui.widgets.card_detail import CardDetailPane
from flop7.tui.widgets.player_list import PlayerListWidget, player_status

if TYPE_CHECKING:
    from flop7.core.classes.cards import Card
    from flop7.core.classes.player import Player
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
        self._pending_draw: tuple[int, Card] | None = None
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

    def set_pending_draw(self, player: Player, card: Card) -> None:
        """Show a just-drawn card before the engine commits it to a hand."""
        self._pending_draw = (self._engine.players.index(player), card)
        self._last_mode = None
        self._invalidate()

    def clear_pending_draw(self) -> None:
        """Clear any display-only card preview."""
        if self._pending_draw is None:
            return
        self._pending_draw = None
        self._last_mode = None
        self._invalidate()

    def clear_pending_draw_unless(self, player: Player) -> None:
        """Keep a pending preview only if it belongs to the given player."""
        if self._pending_draw is None:
            return
        if self._pending_draw[0] == self._engine.players.index(player):
            return
        self.clear_pending_draw()

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
            pending_draw=self._pending_draw,
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
            pending_draw=self._pending_draw,
            compact=True,
        )

        detail_title = ""
        detail_cards: list[Card] = []
        if focused:
            status = player_status(focused)
            detail_title = f"{focused.name} ({status})"
            detail_cards = self._cards_for_player(self._focused_idx, focused)

        card_detail = CardDetailPane(
            cards=detail_cards,
            player_name=detail_title,
        )

        return urwid.Columns([
            ("weight", 1, player_list),
            ("weight", 3, card_detail),
        ])

    def _cards_for_player(self, index: int, player: Player) -> list[Card]:
        cards = list(player.hand)
        if self._pending_draw and self._pending_draw[0] == index:
            cards.append(self._pending_draw[1])
        return cards
