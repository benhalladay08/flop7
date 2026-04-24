from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import urwid

from flop7.core.classes.cards import Card

CARDS_DIR = Path(__file__).resolve().parent.parent / "components" / "cards"

# Card names whose filename differs from Card.name
_NAME_TO_FILE = {
    "Flip Three": "F3",
    "Freeze": "FZ",
    "Second Chance": "SC",
}

CARD_WIDTH = 17
CARD_HEIGHT = 12


@lru_cache(maxsize=None)
def _load_card_art(card_name: str) -> tuple[str, ...]:
    """Load ASCII art lines for a card from its .txt file (cached)."""
    filename = _NAME_TO_FILE.get(card_name, card_name)
    path = CARDS_DIR / f"{filename}.txt"
    return tuple(path.read_text().splitlines())


def _tile_cards(cards: list[Card], max_cols: int) -> str:
    """Tile card art blocks horizontally, wrapping to new rows as needed."""
    if not cards:
        return ""

    gap = 2
    cards_per_row = max(1, (max_cols + gap) // (CARD_WIDTH + gap))
    art_blocks = [_load_card_art(c.name) for c in cards]

    all_lines: list[str] = []
    for start in range(0, len(art_blocks), cards_per_row):
        row_blocks = art_blocks[start : start + cards_per_row]
        for line_idx in range(CARD_HEIGHT):
            parts = []
            for block in row_blocks:
                line = block[line_idx] if line_idx < len(block) else ""
                parts.append(f"{line:<{CARD_WIDTH}}")
            all_lines.append("  ".join(parts))
        all_lines.append("")  # blank line between card rows

    return "\n".join(all_lines)


class CardDetailPane(urwid.WidgetWrap):
    """Displays large ASCII art cards for one player's hand.

    Recalculates the horizontal layout on each render pass so that
    card rows wrap correctly when the terminal is resized.
    """

    def __init__(
        self,
        cards: list[Card] | None = None,
        player_name: str = "",
    ) -> None:
        self._cards = cards or []
        self._player_name = player_name
        self._last_cols: int = 0
        super().__init__(self._build(80))

    def update(self, cards: list[Card], player_name: str = "") -> None:
        self._cards = cards
        self._player_name = player_name
        self._last_cols = 0  # force rebuild on next render

    def render(self, size, focus=False):
        maxcol = size[0] if size else 80
        if maxcol != self._last_cols:
            self._last_cols = maxcol
            self._w = self._build(maxcol)
        return super().render(size, focus)

    def _build(self, maxcol: int) -> urwid.Widget:
        title = f" {self._player_name} " if self._player_name else ""
        if not self._cards:
            inner = urwid.Filler(
                urwid.Text("No cards to display", align="center"),
                valign="middle",
            )
        else:
            # Subtract 4 for the LineBox borders (2 per side)
            art = _tile_cards(self._cards, max_cols=max(CARD_WIDTH, maxcol - 4))
            inner = urwid.Filler(urwid.Text(art, wrap="clip"), valign="top")

        return urwid.LineBox(inner, title=title)
