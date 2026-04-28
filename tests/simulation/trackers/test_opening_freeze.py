"""Tests for OpeningFreezeTracker."""

from unittest.mock import MagicMock

from flop7.core.classes.player import Player
from flop7.core.engine.requests import FreezeEvent, HitStayRequest, RoundOverEvent
from flop7.simulation.trackers import OpeningFreezeTracker


def _player(name: str = "P1") -> Player:
    return Player(name=name)


def _mock_engine():
    return MagicMock()


class TestOpeningFreezeTracker:

    def test_counts_freeze_during_opening(self):
        tracker = OpeningFreezeTracker()
        player = _player()

        tracker.on_event(FreezeEvent(source=player, target=player))

        assert tracker._count == 1

    def test_ignores_freeze_after_hit_stay(self):
        tracker = OpeningFreezeTracker()
        player = _player()

        tracker.on_event(HitStayRequest(player=player))
        tracker.on_event(FreezeEvent(source=player, target=player))

        assert tracker._count == 0

    def test_resets_on_round_over(self):
        tracker = OpeningFreezeTracker()
        player = _player()

        tracker.on_event(HitStayRequest(player=player))
        tracker.on_event(RoundOverEvent(round_number=1))
        tracker.on_event(FreezeEvent(source=player, target=player))

        assert tracker._count == 1

    def test_resets_on_game_over(self):
        tracker = OpeningFreezeTracker()
        player = _player()

        tracker.on_event(HitStayRequest(player=player))
        tracker.on_game_over(_mock_engine())
        tracker.on_event(FreezeEvent(source=player, target=player))

        assert tracker._count == 1

    def test_format_results(self):
        tracker = OpeningFreezeTracker()
        player = _player()
        tracker.on_event(FreezeEvent(source=player, target=player))
        tracker.on_event(FreezeEvent(source=player, target=player))
        for _ in range(5):
            tracker.on_game_over(_mock_engine())

        lines = tracker.format_results()

        assert "Total: 2" in lines[0]
        assert "40.0" in lines[1]
