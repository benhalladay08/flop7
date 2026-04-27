from flop7.tui.widgets.player_list import PlayerListWidget

from tests.conftest import make_players


class TestPlayerListDealerBadge:
    def test_full_row_marks_dealer(self):
        players = make_players(3)
        widget = PlayerListWidget(players, dealer_idx=1)

        dealer_row = widget._full_row(players[1], False, "Active", True)
        non_dealer_row = widget._full_row(players[0], False, "Active", False)

        assert "[D]" in dealer_row
        assert "[D]" not in non_dealer_row

    def test_compact_row_marks_dealer(self):
        players = make_players(3)
        widget = PlayerListWidget(players, dealer_idx=1, compact=True)

        dealer_row = widget._compact_row(players[1], False, "Active", True)
        non_dealer_row = widget._compact_row(players[0], False, "Active", False)

        assert "[D]" in dealer_row
        assert "[D]" not in non_dealer_row
