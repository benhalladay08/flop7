"""Tests for flop7.app.simulation — simulation engine, sampling, and results."""

import pytest

from flop7.app.simulation import (
    SimulationResults,
    run_game,
    sample_game_config,
    validate_sim_config,
)


class TestValidateSimConfig:

    def test_valid_default_ranges(self):
        assert validate_sim_config((3, 10), {"Basic": (0, 10)}) is None

    def test_valid_multiple_bot_types(self):
        assert validate_sim_config(
            (3, 10), {"Basic": (0, 10), "Omniscient": (0, 10)}
        ) is None

    def test_valid_tight_range(self):
        assert validate_sim_config((5, 5), {"Basic": (5, 5)}) is None

    def test_invalid_bot_maxes_too_low(self):
        err = validate_sim_config((5, 10), {"Basic": (0, 2), "Omniscient": (0, 2)})
        assert err is not None
        assert "less than" in err

    def test_invalid_bot_mins_too_high(self):
        err = validate_sim_config((3, 5), {"Basic": (4, 10), "Omniscient": (4, 10)})
        assert err is not None
        assert "exceeds" in err

    def test_single_bot_type_valid(self):
        assert validate_sim_config((3, 3), {"Basic": (3, 3)}) is None


class TestSampleGameConfig:

    def test_sum_equals_player_count_in_range(self):
        for _ in range(50):
            config = sample_game_config((3, 10), {"Basic": (0, 10)})
            total = sum(config.values())
            assert 3 <= total <= 10

    def test_respects_per_type_min(self):
        for _ in range(50):
            config = sample_game_config(
                (6, 6), {"Basic": (3, 6), "Omniscient": (0, 3)},
            )
            assert config["Basic"] >= 3
            assert config["Omniscient"] >= 0
            assert sum(config.values()) == 6

    def test_respects_per_type_max(self):
        for _ in range(50):
            config = sample_game_config(
                (4, 4), {"Basic": (0, 2), "Omniscient": (0, 4)},
            )
            assert config["Basic"] <= 2
            assert config["Omniscient"] <= 4
            assert sum(config.values()) == 4

    def test_fixed_config(self):
        config = sample_game_config((5, 5), {"Basic": (5, 5)})
        assert config == {"Basic": 5}

    def test_multiple_types_sum_correctly(self):
        for _ in range(50):
            config = sample_game_config(
                (3, 10),
                {"Basic": (1, 5), "Omniscient": (1, 5)},
            )
            assert config["Basic"] >= 1
            assert config["Omniscient"] >= 1
            assert config["Basic"] <= 5
            assert config["Omniscient"] <= 5
            assert 3 <= sum(config.values()) <= 10


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


class TestSimulationResults:

    def test_record_increments_totals(self):
        results = SimulationResults()
        engine = run_game({"Basic": 3})
        results.record({"Basic": 3}, engine)

        assert results.total_games == 1
        assert results.total_rounds == engine.round_number
        assert results.total_winning_scores == engine.winner.score

    def test_avg_game_length(self):
        results = SimulationResults()
        for _ in range(10):
            engine = run_game({"Basic": 3})
            results.record({"Basic": 3}, engine)
        assert results.avg_game_length > 0

    def test_avg_winning_score(self):
        results = SimulationResults()
        for _ in range(10):
            engine = run_game({"Basic": 3})
            results.record({"Basic": 3}, engine)
        assert results.avg_winning_score >= 200

    def test_win_pct_sums_to_100(self):
        results = SimulationResults()
        for _ in range(20):
            engine = run_game({"Basic": 3})
            results.record({"Basic": 3}, engine)
        assert abs(results.win_pct("Basic") - 100.0) < 0.01

    def test_win_pct_with_manual_multi_type_results(self):
        """Verify win_pct logic with manually constructed multi-type data."""
        results = SimulationResults()
        results.total_games = 100
        results.wins_by_type = {"TypeA": 60, "TypeB": 40}
        results.games_by_type = {"TypeA": 200, "TypeB": 200}
        results.total_rounds = 800
        results.total_winning_scores = 21000

        assert abs(results.win_pct("TypeA") - 60.0) < 0.01
        assert abs(results.win_pct("TypeB") - 40.0) < 0.01
        total_pct = results.win_pct("TypeA") + results.win_pct("TypeB")
        assert abs(total_pct - 100.0) < 0.01

    def test_empty_results(self):
        results = SimulationResults()
        assert results.avg_game_length == 0.0
        assert results.avg_winning_score == 0.0
        assert results.win_pct("Basic") == 0.0

    def test_games_by_type_tracks_participation(self):
        results = SimulationResults()
        engine = run_game({"Basic": 3})
        results.record({"Basic": 3}, engine)
        assert results.games_by_type["Basic"] == 3


class TestRunGameWithTrackers:

    def test_trackers_receive_events(self):
        from flop7.app.trackers import default_trackers

        trackers = default_trackers()
        engine = run_game({"Basic": 3}, trackers=trackers)

        # After a full game, bust tracker should have seen at least some events
        bust_tracker = trackers[2]  # BustTracker
        assert bust_tracker._games == 1

    def test_flip7_tracker_accumulates_across_games(self):
        from flop7.app.trackers import Flip7Tracker

        tracker = Flip7Tracker()
        for _ in range(5):
            run_game({"Basic": 3}, trackers=[tracker])
        assert tracker._games == 5

    def test_results_with_trackers_field(self):
        from flop7.app.trackers import default_trackers

        trackers = default_trackers()
        results = SimulationResults(trackers=trackers)
        assert results.trackers is trackers
