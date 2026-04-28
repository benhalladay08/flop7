"""Tests for running all-bot simulation games."""

from flop7.simulation.runner import run_game


class TestRunGame:

    def test_returns_finished_engine(self):
        engine = run_game({"Basic": 3})
        assert engine.game_over is True
        assert engine.winner is not None
        assert engine.winner.score >= 200

    def test_player_count_matches(self):
        engine = run_game({"Basic": 5})
        assert len(engine.players) == 5

    def test_player_names_include_type(self):
        engine = run_game({"Basic": 3})
        names = [p.name for p in engine.players]
        assert names[0] == "Basic 1"
        assert names[1] == "Basic 2"
        assert names[2] == "Basic 3"

    def test_trackers_receive_events(self):
        from flop7.simulation.trackers import BustTracker, default_trackers

        trackers = default_trackers()
        run_game({"Basic": 3}, trackers=trackers)

        bust_tracker = next(t for t in trackers if isinstance(t, BustTracker))
        assert bust_tracker._games == 1

    def test_flip7_tracker_accumulates_across_games(self):
        from flop7.simulation.trackers import Flip7Tracker

        tracker = Flip7Tracker()
        for _ in range(5):
            run_game({"Basic": 3}, trackers=[tracker])
        assert tracker._games == 5
