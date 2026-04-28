from flop7.simulation import SimulationResults
from flop7.tui.screens.simulate import SimulateScreen


class TestSimulateScreenResults:
    def test_show_results_uses_per_bot_seat_win_rate(self):
        results = SimulationResults()
        results.wins_by_type = {"Basic": 1}
        results.bot_entries_by_type = {"Basic": 3}

        screen = SimulateScreen()
        screen.show_results(results)

        text, _ = screen._results_text.get_text()
        assert "Win Rate per Bot Seat:" in text
        assert "33.3%" in text
        assert "1 wins / 3 entries" in text
