from flop7.simulation import SimulationResults
from flop7.tui.screens.simulate import SimulateScreen


class TestSimulateScreenResults:
    def test_show_results_includes_per_seat_rate_and_win_share(self):
        results = SimulationResults()
        results.wins_by_type = {"Basic": 1, "Omniscient": 2}
        results.bot_entries_by_type = {"Basic": 3, "Omniscient": 3}

        screen = SimulateScreen()
        screen.show_results(results)

        text, _ = screen._results_text.get_text()
        assert "Win Rate per Bot Seat:" in text
        assert "Percent of Wins:" in text
        assert "33.3%" in text
        assert "66.7%" in text
        assert "1 wins / 3 entries" in text
        assert "2 wins / 3 entries" in text
