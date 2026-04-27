"""Tests for game-flow node dispatch around card drawing."""

from flop7.app.nodes.game import CardDrawnNode, DrawCardNode, GameRoundNode
from flop7.bot.controller import BotController
from flop7.core.classes.cards import FIVE, SEVEN, THREE

from tests.conftest import make_engine


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
