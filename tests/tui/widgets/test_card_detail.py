"""Tests for card detail rendering helpers."""

from flop7.core.classes.cards import FIVE, SECOND_CHANCE, THREE
from flop7.tui.widgets.card_detail import (
    CARD_HEIGHT,
    CARD_WIDTH,
    CardDetailPane,
    _load_card_art,
    _tile_cards,
)


class TestCardArtLoading:
    def test_load_card_art_uses_action_card_filename_alias(self):
        art = _load_card_art(SECOND_CHANCE.name)

        assert len(art) == CARD_HEIGHT
        assert art[0].startswith("╔")
        assert art[-1].startswith("╚")


class TestTileCards:
    def test_no_cards_returns_empty_string(self):
        assert _tile_cards([], max_cols=80) == ""

    def test_tiles_cards_and_wraps_when_width_is_narrow(self):
        art = _tile_cards([THREE, FIVE], max_cols=CARD_WIDTH)
        lines = art.splitlines()

        assert art.count("\n\n") >= 1
        assert lines.count("╔═══════════════╗") == 2
        assert lines.count("╚═══════════════╝") == 2


class TestCardDetailPane:
    def test_update_replaces_cards_and_forces_rebuild(self):
        pane = CardDetailPane(cards=[THREE], player_name="P1")
        pane._last_cols = 80

        pane.update([FIVE], player_name="P2")

        assert pane._cards == [FIVE]
        assert pane._player_name == "P2"
        assert pane._last_cols == 0
