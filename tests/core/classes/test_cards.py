"""Tests for flop7.core.classes.cards — card definitions and deck composition."""
import pytest

from flop7.core.classes.cards import (
    ALL_CARDS,
    CARD_MAP,
    FLIP_THREE,
    FREEZE,
    SECOND_CHANCE,
    PLUS_TWO,
    PLUS_FOUR,
    PLUS_SIX,
    PLUS_EIGHT,
    PLUS_TEN,
    TIMES_TWO,
    ZERO,
    ONE,
    TWO,
    THREE,
    FOUR,
    FIVE,
    SIX,
    SEVEN,
    EIGHT,
    NINE,
    TEN,
    ELEVEN,
    TWELVE,
)

# All 13 number cards in order
NUMBER_CARDS = [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, TEN, ELEVEN, TWELVE]
ACTION_CARDS = [FLIP_THREE, FREEZE, SECOND_CHANCE]
MODIFIER_CARDS = [PLUS_TWO, PLUS_FOUR, PLUS_SIX, PLUS_EIGHT, PLUS_TEN, TIMES_TWO]


class TestDeckComposition:
    """Verify the 94-card deck matches the rules."""

    def test_total_cards_in_deck(self):
        total = sum(c.num_in_deck for c in ALL_CARDS)
        assert total == 94

    def test_number_cards_total_79(self):
        total = sum(c.num_in_deck for c in NUMBER_CARDS)
        assert total == 79

    def test_action_cards_total_9(self):
        total = sum(c.num_in_deck for c in ACTION_CARDS)
        assert total == 9

    def test_modifier_cards_total_6(self):
        total = sum(c.num_in_deck for c in MODIFIER_CARDS)
        assert total == 6


class TestNumberCards:
    """Each number card N has num_in_deck == N, except 0 which has 1."""

    @pytest.mark.parametrize("card,expected", [
        (ZERO, 1),
        (ONE, 1),
        (TWO, 2),
        (THREE, 3),
        (FOUR, 4),
        (FIVE, 5),
        (SIX, 6),
        (SEVEN, 7),
        (EIGHT, 8),
        (NINE, 9),
        (TEN, 10),
        (ELEVEN, 11),
        (TWELVE, 12),
    ])
    def test_num_in_deck_equals_face_value(self, card, expected):
        assert card.num_in_deck == expected

    @pytest.mark.parametrize("card", NUMBER_CARDS)
    def test_number_cards_are_bustable(self, card):
        assert card.bustable is True

    @pytest.mark.parametrize("card", NUMBER_CARDS)
    def test_number_card_points_equal_face_value(self, card):
        assert card.points == int(card.name)


class TestActionCards:
    """FLIP_THREE, FREEZE, SECOND_CHANCE — 3 each, not bustable, 0 points."""

    @pytest.mark.parametrize("card", ACTION_CARDS)
    def test_num_in_deck_is_3(self, card):
        assert card.num_in_deck == 3

    @pytest.mark.parametrize("card", ACTION_CARDS)
    def test_not_bustable(self, card):
        assert card.bustable is False

    @pytest.mark.parametrize("card", ACTION_CARDS)
    def test_zero_points(self, card):
        assert card.points == 0


class TestModifierCards:
    """Score modifier cards — not bustable, correct modifier behaviour."""

    FLAT_MODIFIERS = [PLUS_TWO, PLUS_FOUR, PLUS_SIX, PLUS_EIGHT, PLUS_TEN]

    @pytest.mark.parametrize("card", MODIFIER_CARDS)
    def test_not_bustable(self, card):
        assert card.bustable is False

    @pytest.mark.parametrize("card,expected_points", [
        (PLUS_TWO, 2),
        (PLUS_FOUR, 4),
        (PLUS_SIX, 6),
        (PLUS_EIGHT, 8),
        (PLUS_TEN, 10),
        (TIMES_TWO, 0),
    ])
    def test_points(self, card, expected_points):
        assert card.points == expected_points

    # x2 modifier
    def test_times_two_doubles(self):
        assert TIMES_TWO.score_modifier(10) == 20

    def test_times_two_with_zero(self):
        assert TIMES_TWO.score_modifier(0) == 0

    # Flat modifiers
    @pytest.mark.parametrize("card,base,expected", [
        (PLUS_TWO, 10, 12),
        (PLUS_FOUR, 10, 14),
        (PLUS_SIX, 10, 16),
        (PLUS_EIGHT, 10, 18),
        (PLUS_TEN, 10, 20),
    ])
    def test_flat_modifier_adds_correctly(self, card, base, expected):
        assert card.score_modifier(base) == expected

    def test_times_two_priority_lower_than_flat(self):
        """x2 has score_priority 1, flat modifiers have 2 → x2 applied first."""
        assert TIMES_TWO.score_priority < PLUS_TWO.score_priority


class TestCardMap:
    """CARD_MAP maps abbreviation → card object for every card in ALL_CARDS."""

    def test_all_cards_in_map(self):
        for card in ALL_CARDS:
            assert card.abbrv in CARD_MAP
            assert CARD_MAP[card.abbrv] is card

    def test_map_size_matches_all_cards(self):
        assert len(CARD_MAP) == len(ALL_CARDS)
