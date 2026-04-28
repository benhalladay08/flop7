"""Tests for game-flow node dispatch around card drawing."""

from flop7.app.nodes.game import (
    CardDrawnNode,
    DrawCardNode,
    GameRoundNode,
    SpecialResolvedNode,
    TargetSelectNode,
)
from flop7.bot.controller import BotController
from flop7.core.classes.cards import FIVE, FREEZE, SEVEN, THREE
from tests.conftest import make_engine


class RecordingGameScreen:
    def __init__(self):
        self.pending_draw = None
        self.focused_idx = None
        self.refresh_count = 0

    def set_pending_draw(self, player, card):
        self.pending_draw = (player, card)

    def clear_pending_draw(self):
        self.pending_draw = None

    def clear_pending_draw_unless(self, player):
        if self.pending_draw is None:
            return
        if self.pending_draw[0] is not player:
            self.clear_pending_draw()

    def set_focused(self, idx: int):
        self.focused_idx = idx

    def refresh(self):
        self.refresh_count += 1


class TestDrawCardNode:

    def test_virtual_draw_node_auto_deals_from_deck(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        round_node = GameRoundNode(engine, "virtual", BotController())

        draw_node = round_node.dispatch({})
        assert isinstance(draw_node, DrawCardNode)
        assert draw_node.is_dispatcher is True

        next_node = draw_node.dispatch({})
        assert isinstance(next_node, CardDrawnNode)
        assert engine.deck.draw_pile == [THREE, SEVEN]

    def test_real_draw_node_prompts_for_card_input(self):
        engine = make_engine([], n_players=3, real_mode=True)
        round_node = GameRoundNode(engine, "real", BotController())

        draw_node = round_node.dispatch({})
        assert isinstance(draw_node, DrawCardNode)
        assert draw_node.is_dispatcher is False
        assert draw_node.prompt.validator("5") is None

        next_node = draw_node.on_input("5", {})
        assert isinstance(next_node, CardDrawnNode)

    def test_card_drawn_sets_pending_draw_before_card_is_committed(self):
        engine = make_engine([], n_players=3, real_mode=True)
        round_node = GameRoundNode(engine, "real", BotController())
        screen = RecordingGameScreen()
        context = {"_game_screen": screen}

        draw_node = round_node.dispatch(context)
        next_node = draw_node.on_input("5", context)

        assert isinstance(next_node, CardDrawnNode)
        assert screen.pending_draw == (engine.players[1], FIVE)
        assert screen.focused_idx == 1
        assert engine.players[1].hand == []

    def test_pending_draw_clears_after_card_drawn_notification(self):
        engine = make_engine([], n_players=3, real_mode=True)
        round_node = GameRoundNode(engine, "real", BotController())
        screen = RecordingGameScreen()
        context = {"_game_screen": screen}

        draw_node = round_node.dispatch(context)
        card_drawn_node = draw_node.on_input("5", context)
        next_node = card_drawn_node.on_input("", context)

        assert isinstance(next_node, DrawCardNode)
        assert screen.pending_draw is None
        assert engine.players[1].hand == [FIVE]

    def test_targeted_action_pending_draw_clears_after_target_selected(self):
        engine = make_engine([], n_players=3, real_mode=True)
        round_node = GameRoundNode(engine, "real", BotController())
        screen = RecordingGameScreen()
        context = {"_game_screen": screen}

        draw_node = round_node.dispatch(context)
        card_drawn_node = draw_node.on_input("freeze", context)

        assert isinstance(card_drawn_node, CardDrawnNode)
        assert screen.pending_draw == (engine.players[1], FREEZE)

        target_node = card_drawn_node.on_input("", context)

        assert isinstance(target_node, TargetSelectNode)
        assert screen.pending_draw == (engine.players[1], FREEZE)

        next_node = target_node.on_input("P3", context)

        assert isinstance(next_node, SpecialResolvedNode)
        assert screen.pending_draw is None
        assert engine.players[2].hand == [FREEZE]
