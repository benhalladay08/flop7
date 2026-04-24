"""Tests for bot utility functions."""

from flop7.bot.knowledge import PlayerView
from flop7.bot.utils import overall_score
from flop7.core.classes.cards import FIVE, TEN


def _player_view(score=0, active_score=0):
    return PlayerView(
        index=0,
        name="Test",
        hand=(TEN, FIVE),
        score=score,
        active_score=active_score,
        is_active=True,
        busted=False,
    )


class TestOverallScore:
    """Verify overall_score combines cumulative and hand scores."""

    def test_cumulative_plus_hand(self):
        player = _player_view(score=40, active_score=15)
        assert overall_score(player) == 55

    def test_zero_when_empty(self):
        player = _player_view()
        assert overall_score(player) == 0

    def test_only_cumulative(self):
        player = _player_view(score=75)
        assert overall_score(player) == 75

    def test_only_hand_score(self):
        player = _player_view(active_score=15)
        assert overall_score(player) == 15
