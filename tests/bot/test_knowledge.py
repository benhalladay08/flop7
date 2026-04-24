"""Tests for read-only bot knowledge views."""

from dataclasses import FrozenInstanceError

import pytest

from flop7.bot.knowledge import build_game_view
from flop7.core.classes.cards import FIVE, SECOND_CHANCE, SEVEN, TEN, THREE

from tests.conftest import make_engine


class TestBuildGameView:

    def test_player_state_is_snapshotted(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        p1, p2, _ = engine.players
        p1.hand = [FIVE, SECOND_CHANCE]
        p1.score = 20
        p2.is_active = False
        p2.busted = True

        view = build_game_view(engine)

        assert view.players[0].index == 0
        assert view.players[0].name == "P1"
        assert view.players[0].hand == (FIVE, SECOND_CHANCE)
        assert view.players[0].score == 20
        assert view.players[0].active_score == 5
        assert view.players[0].has_card(SECOND_CHANCE)
        assert view.players[1].is_active is False
        assert view.players[1].busted is True
        assert view.active_player_indexes == (0, 2)
        assert [p.index for p in view.active_players] == [0, 2]

    def test_virtual_view_exposes_full_draw_order(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        engine.deck.discard([TEN])

        view = build_game_view(engine)

        assert view.deck.draw_order == (FIVE, THREE, SEVEN)
        assert view.deck.next_card is FIVE
        assert view.deck.remaining_count == 3
        assert view.deck.discard_pile == (TEN,)
        assert view.deck.discard_count == 1

    def test_real_view_hides_unknown_draw_order(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3, real_mode=True)
        engine.deck.discard([TEN])

        view = build_game_view(engine)

        assert view.real_mode is True
        assert view.deck.draw_order == ()
        assert view.deck.next_card is None
        assert view.deck.remaining_count == 0
        assert view.deck.discard_pile == (TEN,)

    def test_winner_index_is_snapshotted(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        engine.game_over = True
        engine.winner = engine.players[1]

        view = build_game_view(engine)

        assert view.game_over is True
        assert view.winner_index == 1
        assert view.winner is view.players[1]


class TestViewImmutability:

    def test_game_view_is_frozen(self):
        view = build_game_view(make_engine([FIVE, THREE, SEVEN], n_players=3))

        with pytest.raises(FrozenInstanceError):
            view.round_number = 99

    def test_player_view_is_frozen(self):
        view = build_game_view(make_engine([FIVE, THREE, SEVEN], n_players=3))

        with pytest.raises(FrozenInstanceError):
            view.players[0].name = "Mutated"

    def test_deck_view_is_frozen(self):
        view = build_game_view(make_engine([FIVE, THREE, SEVEN], n_players=3))

        with pytest.raises(FrozenInstanceError):
            view.deck.draw_order = ()
