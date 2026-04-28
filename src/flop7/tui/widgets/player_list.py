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
    if player.busted:
        return "Busted"
    if player.is_active:
        return "Active"
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
        dealer_idx: int | None = None,
        pending_draw: tuple[int, Card] | None = None,
        compact: bool = False,
    ) -> None:
        self._players = players
        self._focused_idx = focused_idx
        self._dealer_idx = dealer_idx
        self._pending_draw = pending_draw
        self._compact = compact
        super().__init__(self._build())

    def update(
        self,
        players: list[Player],
        focused_idx: int = 0,
        dealer_idx: int | None = None,
        pending_draw: tuple[int, Card] | None = None,
    ) -> None:
        self._players = players
        self._focused_idx = focused_idx
        self._dealer_idx = dealer_idx
        self._pending_draw = pending_draw
        self._w = self._build()

    def _build(self) -> urwid.Widget:
        rows: list[urwid.Widget] = []

        if self._compact:
            header_text = "  D   Player      Score  St"
        else:
            header_text = (
                "  D   Player       Cards"
                + " " * 28
                + "Score  Status"
            )

        rows.append(urwid.AttrMap(urwid.Text(header_text), "instruction"))
        rows.append(urwid.Divider("─"))

        for idx, player in enumerate(self._players):
            is_focused = idx == self._focused_idx
            is_dealer = idx == self._dealer_idx
            status = player_status(player)
            cards = self._cards_for_player(idx, player)

            if self._compact:
                text = self._compact_row(player, is_focused, status, is_dealer)
            else:
                text = self._full_row(
                    player,
                    is_focused,
                    status,
                    is_dealer,
                    cards,
                )

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

    def _cards_for_player(self, index: int, player: Player) -> list[Card]:
        cards = list(player.hand)
        if self._pending_draw and self._pending_draw[0] == index:
            cards.append(self._pending_draw[1])
        return cards

    def _full_row(
        self,
        player: Player,
        focused: bool,
        status: str,
        is_dealer: bool,
        cards: list[Card] | None = None,
    ) -> str:
        arrow = "▸ " if focused else "  "
        dealer = "[D] " if is_dealer else "    "
        display_cards = player.hand if cards is None else cards
        card_text = " ".join(_card_tag(c) for c in display_cards)
        if status == "Busted":
            card_text += " ← BUST"
        score = str(player.active_score)
        return (
            f"{arrow}{dealer}{player.name:<12} "
            f"{card_text:<40} {score:>5}  {status}"
        )

    def _compact_row(
        self,
        player: Player,
        focused: bool,
        status: str,
        is_dealer: bool,
    ) -> str:
        arrow = "▸ " if focused else "  "
        dealer = "[D] " if is_dealer else "    "
        short = {"Active": "Act", "Stayed": "Stay", "Busted": "Bust"}[status]
        score = str(player.active_score)
        return f"{arrow}{dealer}{player.name:<10} {score:>4}  {short}"
