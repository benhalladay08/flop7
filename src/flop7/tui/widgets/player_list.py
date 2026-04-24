from __future__ import annotations

import urwid

from flop7.core.classes.cards import Card
from flop7.core.classes.player import Player

# Inline display names for cards whose Card.name isn't user-friendly
_DISPLAY_NAME = {
    "Flip Three": "F3",
    "Freeze": "FZ",
    "Second Chance": "SC",
    "x2": "×2",
}


def _card_tag(card: Card) -> str:
    """Inline card tag, e.g. '[3]', '[+4]', '[×2]', '[SC]'."""
    return f"[{_DISPLAY_NAME.get(card.name, card.name)}]"


def player_status(player: Player) -> str:
    """Determine display status: 'Active', 'Stayed', or 'Busted'."""
    if player.is_active:
        return "Active"
    bustable_names = [c.name for c in player.hand if c.bustable]
    if len(bustable_names) != len(set(bustable_names)):
        return "Busted"
    return "Stayed"


class PlayerListWidget(urwid.WidgetWrap):
    """Vertical list of players showing name, cards, score, and status.

    *compact=True* renders an abbreviated sidebar row for wide mode.
    *compact=False* renders the full row with inline card tags.
    """

    def __init__(
        self,
        players: list[Player],
        focused_idx: int = 0,
        compact: bool = False,
    ) -> None:
        self._players = players
        self._focused_idx = focused_idx
        self._compact = compact
        super().__init__(self._build())

    def update(self, players: list[Player], focused_idx: int = 0) -> None:
        self._players = players
        self._focused_idx = focused_idx
        self._w = self._build()

    def _build(self) -> urwid.Widget:
        rows: list[urwid.Widget] = []

        if self._compact:
            header_text = "  Player      Score  St"
        else:
            header_text = (
                "  Player       Cards"
                + " " * 28
                + "Score  Status"
            )

        rows.append(urwid.AttrMap(urwid.Text(header_text), "instruction"))
        rows.append(urwid.Divider("─"))

        for idx, player in enumerate(self._players):
            is_focused = idx == self._focused_idx
            status = player_status(player)

            if self._compact:
                text = self._compact_row(player, is_focused, status)
            else:
                text = self._full_row(player, is_focused, status)

            if status == "Busted":
                attr = "busted"
            elif status == "Stayed":
                attr = "dimmed"
            elif is_focused:
                attr = "active"
            else:
                attr = ""

            rows.append(urwid.AttrMap(urwid.Text(text), attr))

        pile = urwid.Pile(rows)
        return urwid.Filler(pile, valign="top")

    def _full_row(self, player: Player, focused: bool, status: str) -> str:
        arrow = "▸ " if focused else "  "
        cards = " ".join(_card_tag(c) for c in player.hand)
        if status == "Busted":
            cards += " ← BUST"
        score = str(player.active_score)
        return f"{arrow}{player.name:<12} {cards:<40} {score:>5}  {status}"

    def _compact_row(self, player: Player, focused: bool, status: str) -> str:
        arrow = "▸ " if focused else "  "
        short = {"Active": "Act", "Stayed": "Stay", "Busted": "Bust"}[status]
        score = str(player.active_score)
        return f"{arrow}{player.name:<10} {score:>4}  {short}"
