"""Tests for flop7.core.classes.player — Player state, scoring, and hand management."""
import pytest

from flop7.core.classes.cards import (
    FIVE,
    THREE,
    SEVEN,
    ELEVEN,
    TWELVE,
    PLUS_TWO,
    PLUS_FOUR,
    PLUS_SIX,
    TIMES_TWO,
    SECOND_CHANCE,
    FREEZE,
)
from flop7.core.classes.player import Player


class TestInitialState:
    """Player starts with correct defaults."""

    def test_name(self):
        p = Player("Alice")
        assert p.name == "Alice"

    def test_empty_hand(self):
        p = Player("Alice")
        assert p.hand == []

    def test_score_zero(self):
        p = Player("Alice")
        assert p.score == 0

    def test_is_active(self):
        p = Player("Alice")
        assert p.is_active is True


class TestActiveScore:
    """active_score must follow rules.md scoring order:
    1. Sum number card values
    2. x2 doubles the sum
    3. Flat modifiers (+N) added last
    """

    def test_number_cards_only(self):
        p = Player("A")
        p.hand = [FIVE, THREE, SEVEN]
        assert p.active_score == 15

    def test_rules_example(self):
        """Rules.md example: 11 + 5 + 12 = 28, x2 → 56, +4 → 60."""
        p = Player("A")
        p.hand = [ELEVEN, FIVE, TWELVE, TIMES_TWO, PLUS_FOUR]
        assert p.active_score == 60

    def test_x2_before_flat_modifiers(self):
        """[5, 3] + x2 + +4 → (5+3)*2 + 4 = 20."""
        p = Player("A")
        p.hand = [FIVE, THREE, TIMES_TWO, PLUS_FOUR]
        assert p.active_score == 20

    def test_flat_modifiers_only(self):
        """+4 + +6 = 10 even without number cards."""
        p = Player("A")
        p.hand = [PLUS_FOUR, PLUS_SIX]
        assert p.active_score == 10

    def test_x2_with_no_number_cards(self):
        """x2(0) = 0, then +4 → 4."""
        p = Player("A")
        p.hand = [TIMES_TWO, PLUS_FOUR]
        assert p.active_score == 4

    def test_empty_hand(self):
        p = Player("A")
        assert p.active_score == 0

    def test_single_number_card(self):
        p = Player("A")
        p.hand = [TWELVE]
        assert p.active_score == 12

    def test_multiple_flat_modifiers(self):
        """+2 + +4 = 6 on an empty number base."""
        p = Player("A")
        p.hand = [PLUS_TWO, PLUS_FOUR]
        assert p.active_score == 6

    def test_action_cards_contribute_zero(self):
        """Second Chance / Freeze in hand don't add to score."""
        p = Player("A")
        p.hand = [FIVE, SECOND_CHANCE, FREEZE]
        assert p.active_score == 5


class TestHasCard:
    """has_card matches by card name."""

    def test_card_present(self):
        p = Player("A")
        p.hand = [FIVE]
        assert p.has_card(FIVE) is True

    def test_card_absent(self):
        p = Player("A")
        p.hand = [THREE]
        assert p.has_card(FIVE) is False

    def test_empty_hand(self):
        p = Player("A")
        assert p.has_card(FIVE) is False

    def test_second_chance_present(self):
        p = Player("A")
        p.hand = [SECOND_CHANCE]
        assert p.has_card(SECOND_CHANCE) is True
