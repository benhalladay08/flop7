import pytest

from flop7.bot.models.basic import BasicBot
from flop7.bot.models.omniscient import OmniscientBot
from flop7.bot.registry import Bot


class TestBotRegistry:
    def test_available_bots_contains_registered_models(self):
        assert Bot.available_bots["Basic"] is BasicBot
        assert Bot.available_bots["Omniscient"] is OmniscientBot

    def test_create_uses_available_bots(self):
        assert isinstance(Bot.create("Basic"), BasicBot)

    def test_unknown_bot_lists_available_names(self):
        with pytest.raises(ValueError, match="Available bots"):
            Bot.create("Missing")
