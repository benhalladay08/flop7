from flop7.core.classes.cards import FIVE, THREE
from flop7.tui.screens.game import GameScreen
from tests.conftest import make_engine


class TestGameScreenPendingDraw:
    def test_pending_draw_is_included_for_matching_player(self):
        engine = make_engine([], n_players=3)
        screen = GameScreen(engine, focused_idx=1)
        engine.players[1].hand = [THREE]

        screen.set_pending_draw(engine.players[1], FIVE)

        assert screen._cards_for_player(1, engine.players[1]) == [THREE, FIVE]
        assert screen._cards_for_player(0, engine.players[0]) == []
        assert engine.players[1].hand == [THREE]

    def test_clear_pending_draw_removes_preview(self):
        engine = make_engine([], n_players=3)
        screen = GameScreen(engine, focused_idx=1)

        screen.set_pending_draw(engine.players[1], FIVE)
        screen.clear_pending_draw()

        assert screen._cards_for_player(1, engine.players[1]) == []
