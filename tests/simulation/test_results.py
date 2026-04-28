"""Tests for simulation result aggregation."""

from flop7.simulation.results import SimulationResults
from flop7.simulation.runner import run_game


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

    def test_win_rate_uses_bot_entries_as_denominator(self):
        results = SimulationResults()
        engine = run_game({"Basic": 3})
        results.record({"Basic": 3}, engine)

        assert abs(results.win_rate("Basic") - (100 / 3)) < 0.01

    def test_win_rates_do_not_need_to_sum_to_100(self):
        results = SimulationResults()
        results.total_games = 100
        results.wins_by_type = {"TypeA": 60, "TypeB": 40}
        results.bot_entries_by_type = {"TypeA": 200, "TypeB": 50}
        results.total_rounds = 800
        results.total_winning_scores = 21000

        assert abs(results.win_rate("TypeA") - 30.0) < 0.01
        assert abs(results.win_rate("TypeB") - 80.0) < 0.01
        total_rate = results.win_rate("TypeA") + results.win_rate("TypeB")
        assert abs(total_rate - 110.0) < 0.01

    def test_win_share_uses_total_wins_as_denominator(self):
        results = SimulationResults()
        results.wins_by_type = {"TypeA": 60, "TypeB": 40}
        results.bot_entries_by_type = {"TypeA": 200, "TypeB": 50}

        assert abs(results.win_share("TypeA") - 60.0) < 0.01
        assert abs(results.win_share("TypeB") - 40.0) < 0.01
        total_share = results.win_share("TypeA") + results.win_share("TypeB")
        assert abs(total_share - 100.0) < 0.01

    def test_empty_results(self):
        results = SimulationResults()
        assert results.avg_game_length == 0.0
        assert results.avg_winning_score == 0.0
        assert results.win_rate("Basic") == 0.0
        assert results.win_share("Basic") == 0.0

    def test_bot_entries_by_type_tracks_participation(self):
        results = SimulationResults()
        engine = run_game({"Basic": 3})
        results.record({"Basic": 3}, engine)
        assert results.bot_entries_by_type["Basic"] == 3

    def test_results_with_trackers_field(self):
        from flop7.simulation.trackers import default_trackers

        trackers = default_trackers()
        results = SimulationResults(trackers=trackers)
        assert results.trackers is trackers
