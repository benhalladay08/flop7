from flop7.bot.base import AbstractBot
from flop7.bot.models.basic import BasicBot
from flop7.bot.models.omniscient import OmniscientBot


class Bot:
    """Registry of bot classes available to the app."""

    available_bots: dict[str, type[AbstractBot]] = {
        "Basic": BasicBot,
        "Omniscient": OmniscientBot,
    }

    @classmethod
    def create(cls, model: str, virtual: bool = False, **params) -> AbstractBot:
        if model not in cls.available_bots:
            available = list(cls.available_bots.keys())
            raise ValueError(f"Bot '{model}' not found. Available bots: {available}")

        bot_class = cls.available_bots[model]
        if not virtual and bot_class.virtual_only:
            raise ValueError(f"Bot '{model}' cannot be used in a non-virtual game.")

        return bot_class(**params)
