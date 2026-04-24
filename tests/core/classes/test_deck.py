"""Tests for flop7.core.classes.deck — Deck construction, deal, discard, reshuffle."""
from unittest.mock import MagicMock

import pytest

from flop7.core.classes.cards import ALL_CARDS, FIVE, THREE, SEVEN, Card
from flop7.core.classes.deck import Deck

from tests.conftest import deterministic_draw, make_deck


class TestBuildCardList:
    """Deck._build_card_list expands ALL_CARDS into 94 individual cards."""

    def test_total_count(self):
        deck = Deck(draw=deterministic_draw([]))
        cards = deck._build_card_list()
        assert len(cards) == 94

    def test_each_card_appears_correct_times(self):
        deck = Deck(draw=deterministic_draw([]))
        cards = deck._build_card_list()
        for template in ALL_CARDS:
            count = sum(1 for c in cards if c is template)
            assert count == template.num_in_deck, (
                f"{template.name} expected {template.num_in_deck}, got {count}"
            )


class TestDeal:
    """Deck.deal removes from draw_pile and returns via the DrawProtocol."""

    def test_deal_returns_expected_card(self):
        deck = make_deck([FIVE, THREE, SEVEN])
        card = deck.deal()
        assert card is FIVE

    def test_deal_removes_from_draw_pile(self):
        deck = make_deck([FIVE, THREE, SEVEN])
        deck.deal()
        assert len(deck.draw_pile) == 2

    def test_sequential_deals(self):
        deck = make_deck([FIVE, THREE, SEVEN])
        c1 = deck.deal()
        c2 = deck.deal()
        c3 = deck.deal()
        assert c1 is FIVE
        assert c2 is THREE
        assert c3 is SEVEN
        assert len(deck.draw_pile) == 0

    def test_last_card_draw_reshuffles_discard_pile(self):
        deck = make_deck([FIVE])
        deck.discard([THREE])

        card = deck.deal()

        assert card is FIVE
        assert deck.draw_pile == [THREE]
        assert deck.discard_pile == []

    def test_last_card_draw_with_empty_discard_leaves_draw_pile_empty(self):
        deck = make_deck([FIVE])

        card = deck.deal()

        assert card is FIVE
        assert deck.draw_pile == []
        assert deck.discard_pile == []

    def test_empty_draw_pile_raises_without_reshuffling(self):
        deck = make_deck([])
        deck.reshuffle = MagicMock()

        with pytest.raises(IndexError, match="empty draw pile"):
            deck.deal()

        deck.reshuffle.assert_not_called()


class TestDiscard:
    """Deck.discard adds cards to the discard pile."""

    def test_discard_adds_cards(self):
        deck = make_deck([])
        deck.discard([FIVE, THREE])
        assert len(deck.discard_pile) == 2
        assert FIVE in deck.discard_pile
        assert THREE in deck.discard_pile

    def test_discard_accumulates(self):
        deck = make_deck([])
        deck.discard([FIVE])
        deck.discard([THREE])
        assert len(deck.discard_pile) == 2


class TestReshuffle:
    """Deck.reshuffle merges discard back into draw pile."""

    def test_reshuffle_moves_discard_to_draw(self):
        deck = make_deck([])
        deck.discard([FIVE, THREE, SEVEN])
        assert len(deck.draw_pile) == 0
        assert len(deck.discard_pile) == 3
        deck.reshuffle()
        assert len(deck.draw_pile) == 3
        assert len(deck.discard_pile) == 0

    def test_reshuffle_preserves_existing_draw_pile(self):
        deck = make_deck([FIVE])
        deck.discard([THREE])
        deck.reshuffle()
        assert len(deck.draw_pile) == 2
        assert FIVE in deck.draw_pile
        assert THREE in deck.draw_pile
