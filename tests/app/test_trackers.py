"""Tests for flop7.app.trackers — built-in simulation event trackers."""

from __future__ import annotations

from unittest.mock import MagicMock

from flop7.app.trackers import (
    BustTracker,
    Flip7Tracker,
    OpeningFreezeTracker,
    SimTracker,
    default_trackers,
)
from flop7.core.classes.player import Player
from flop7.core.engine.requests import (
    Flip7Event,
    FreezeEvent,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
)


def _player(name: str = "P1") -> Player:
    return Player(name=name)


def _mock_engine():
    return MagicMock()


# ── Flip7Tracker ─────────────────────────────────────────────────────

class TestFlip7Tracker:

    def test_counts_flip7_events(self):
        t = Flip7Tracker()
        p = _player()
        t.on_event(Flip7Event(player=p))
        t.on_event(Flip7Event(player=p))
        t.on_game_over(_mock_engine())
        assert t._count == 2

    def test_ignores_other_events(self):
        t = Flip7Tracker()
        t.on_event(RoundOverEvent(round_number=1))
        t.on_event(HitStayRequest(player=_player()))
        assert t._count == 0

    def test_format_results_rate(self):
        t = Flip7Tracker()
        p = _player()
        for _ in range(3):
            t.on_event(Flip7Event(player=p))
        for _ in range(10):
            t.on_game_over(_mock_engine())
        lines = t.format_results()
        assert "Total: 3" in lines[0]
        assert "30.0" in lines[1]

    def test_format_results_empty(self):
        t = Flip7Tracker()
        lines = t.format_results()
        assert "Total: 0" in lines[0]
        assert "0.0" in lines[1]


# ── OpeningFreezeTracker ─────────────────────────────────────────────

class TestOpeningFreezeTracker:

    def test_counts_freeze_during_opening(self):
        t = OpeningFreezeTracker()
        p = _player()
        t.on_event(FreezeEvent(source=p, target=p))
        assert t._count == 1

    def test_ignores_freeze_after_hit_stay(self):
        t = OpeningFreezeTracker()
        p = _player()
        t.on_event(HitStayRequest(player=p))
        t.on_event(FreezeEvent(source=p, target=p))
        assert t._count == 0

    def test_resets_on_round_over(self):
        t = OpeningFreezeTracker()
        p = _player()
        t.on_event(HitStayRequest(player=p))
        t.on_event(RoundOverEvent(round_number=1))
        # Now in opening again
        t.on_event(FreezeEvent(source=p, target=p))
        assert t._count == 1

    def test_resets_on_game_over(self):
        t = OpeningFreezeTracker()
        p = _player()
        t.on_event(HitStayRequest(player=p))
        t.on_game_over(_mock_engine())
        # New game, should be in opening
        t.on_event(FreezeEvent(source=p, target=p))
        assert t._count == 1

    def test_format_results(self):
        t = OpeningFreezeTracker()
        p = _player()
        t.on_event(FreezeEvent(source=p, target=p))
        t.on_event(FreezeEvent(source=p, target=p))
        for _ in range(5):
            t.on_game_over(_mock_engine())
        lines = t.format_results()
        assert "Total: 2" in lines[0]
        assert "40.0" in lines[1]


# ── BustTracker ──────────────────────────────────────────────────────

class TestBustTracker:

    def test_counts_busts(self):
        t = BustTracker()
        p = _player()
        from flop7.core.classes.cards import FIVE
        t.on_event(PlayerBustedEvent(player=p, card=FIVE))
        t.on_event(PlayerBustedEvent(player=p, card=FIVE))
        assert t._count == 2

    def test_ignores_other_events(self):
        t = BustTracker()
        t.on_event(RoundOverEvent(round_number=1))
        t.on_event(HitStayRequest(player=_player()))
        assert t._count == 0

    def test_format_results_avg(self):
        t = BustTracker()
        p = _player()
        from flop7.core.classes.cards import FIVE
        for _ in range(6):
            t.on_event(PlayerBustedEvent(player=p, card=FIVE))
        for _ in range(3):
            t.on_game_over(_mock_engine())
        lines = t.format_results()
        assert "Total: 6" in lines[0]
        assert "2.0" in lines[1]

    def test_format_results_empty(self):
        t = BustTracker()
        lines = t.format_results()
        assert "Total: 0" in lines[0]
        assert "0.0" in lines[1]


# ── default_trackers & protocol ──────────────────────────────────────

class TestDefaultTrackers:

    def test_returns_three_trackers(self):
        trackers = default_trackers()
        assert len(trackers) == 3

    def test_all_satisfy_protocol(self):
        for t in default_trackers():
            assert isinstance(t, SimTracker)

    def test_each_has_unique_label(self):
        labels = [t.label for t in default_trackers()]
        assert len(labels) == len(set(labels))
