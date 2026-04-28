"""Tests for the bot controller adapter."""

import pytest

from flop7.bot.base import AbstractBot
from flop7.bot.controller import BotController
from flop7.core.classes.cards import FIVE, SEVEN, THREE
from flop7.core.enum.decisions import TargetEvent
from tests.conftest import make_engine


class StubBot(AbstractBot):
    def __init__(self, hit=True, target_index=1):
        self.hit = hit
        self.target_index = target_index
        self.hit_call = None
        self.target_call = None

    def hit_stay(self, view, player):
        self.hit_call = (view, player)
        return self.hit

    def target_selector(self, view, event, player, eligible):
        self.target_call = (view, event, player, eligible)
        return view.players[self.target_index]


class TestBotController:

    def test_has_bot_uses_player_index_mapping(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        controller = BotController({1: StubBot()})

        assert controller.has_bot(engine, engine.players[0]) is False
        assert controller.has_bot(engine, engine.players[1]) is True

    def test_hit_stay_maps_to_read_only_view(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        bot = StubBot(hit=False)
        controller = BotController({0: bot})

        result = controller.hit_stay(engine, engine.players[0])

        view, player = bot.hit_call
        assert result is False
        assert player.index == 0
        assert view.deck.draw_order == (FIVE, THREE, SEVEN)

    def test_target_selector_maps_view_result_to_engine_player(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        bot = StubBot(target_index=2)
        controller = BotController({0: bot})

        result = controller.target_selector(
            engine,
            TargetEvent.FREEZE,
            engine.players[0],
            [engine.players[1], engine.players[2]],
        )

        view, event, source, eligible = bot.target_call
        assert result is engine.players[2]
        assert event is TargetEvent.FREEZE
        assert source.index == 0
        assert [player.index for player in eligible] == [1, 2]
        assert view.players[2].name == engine.players[2].name

    def test_target_selector_rejects_ineligible_target(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        bot = StubBot(target_index=0)
        controller = BotController({0: bot})

        with pytest.raises(ValueError, match="ineligible target"):
            controller.target_selector(
                engine,
                TargetEvent.FREEZE,
                engine.players[0],
                [engine.players[1]],
            )

    def test_missing_bot_raises(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        controller = BotController()

        with pytest.raises(ValueError, match="No bot registered"):
            controller.hit_stay(engine, engine.players[0])
