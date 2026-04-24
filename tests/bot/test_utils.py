"""Tests for bot utility functions."""

from flop7.bot.utils import overall_score
from flop7.core.classes.cards import FIVE, TEN
from flop7.core.classes.player import Player


class TestOverallScore:
    """Verify overall_score combines cumulative and hand scores."""

    def test_cumulative_plus_hand(self):
        """Overall score sums banked score and active hand score."""
        p = Player("Test")
        p.score = 40
        p.hand = [TEN, FIVE]  # active_score = 15
        assert overall_score(p) == 55

    def test_zero_when_empty(self):
        """Overall score is zero for a new player with no cards."""
        p = Player("Test")
        assert overall_score(p) == 0

    def test_only_cumulative(self):
        """Overall score equals cumulative when hand is empty."""
        p = Player("Test")
        p.score = 75
        p.hand = []
        assert overall_score(p) == 75

    def test_only_hand_score(self):
        """Overall score equals hand score when cumulative is zero."""
        p = Player("Test")
        p.score = 0
        p.hand = [TEN, FIVE]  # active_score = 15
        assert overall_score(p) == 15
