"""Tests for BustTracker."""

from unittest.mock import MagicMock

from flop7.core.classes.cards import FIVE
from flop7.core.classes.player import Player
from flop7.core.engine.requests import HitStayRequest, PlayerBustedEvent, RoundOverEvent
from flop7.simulation.trackers import BustTracker


def _player(name: str = "P1") -> Player:
    return Player(name=name)


def _mock_engine():
    return MagicMock()


class TestBustTracker:

    def test_counts_busts(self):
        tracker = BustTracker()
        player = _player()

        tracker.on_event(PlayerBustedEvent(player=player, card=FIVE))
        tracker.on_event(PlayerBustedEvent(player=player, card=FIVE))

        assert tracker._count == 2

    def test_ignores_other_events(self):
        tracker = BustTracker()

        tracker.on_event(RoundOverEvent(round_number=1))
        tracker.on_event(HitStayRequest(player=_player()))

        assert tracker._count == 0

    def test_format_results_avg(self):
        tracker = BustTracker()
        player = _player()
        for _ in range(6):
            tracker.on_event(PlayerBustedEvent(player=player, card=FIVE))
        for _ in range(3):
            tracker.on_game_over(_mock_engine())

        lines = tracker.format_results()

        assert "Total: 6" in lines[0]
        assert "2.0" in lines[1]

    def test_format_results_empty(self):
        tracker = BustTracker()

        lines = tracker.format_results()

        assert "Total: 0" in lines[0]
        assert "0.0" in lines[1]
