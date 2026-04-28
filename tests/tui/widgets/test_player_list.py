from flop7.core.classes.cards import FIVE, THREE
from flop7.tui.widgets.player_list import PlayerListWidget, player_status
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


class TestPlayerListPendingDraw:
    def test_pending_draw_is_included_without_mutating_hand(self):
        players = make_players(3)
        players[1].hand = [THREE]
        widget = PlayerListWidget(players, pending_draw=(1, FIVE))

        cards = widget._cards_for_player(1, players[1])
        row = widget._full_row(players[1], False, "Active", False, cards)

        assert cards == [THREE, FIVE]
        assert players[1].hand == [THREE]
        assert "[3]" in row
        assert "[5]" in row


class TestPlayerStatus:
    def test_busted_state_uses_explicit_player_flag(self):
        player = make_players(1)[0]
        player.is_active = False
        player.busted = True
        player.hand = [FIVE]

        assert player_status(player) == "Busted"
