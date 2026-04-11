from flop7.bot.base import AbstractBot
from flop7.bot.models.basic import BasicBot
from flop7.bot.models.omniscient import OmniscientBot

class Bot:
    """
    Registry of bots. Calls for bot classes by name, and provides a list of available bots for the UI.
    """

    avaliable_bots: dict[str, type[AbstractBot]] = {
        "Basic": BasicBot,
        "Omniscient": OmniscientBot
    }

    def __init__(self, model: str, virtual: bool = False, **params) -> None:
        if model not in self.avaliable_bots:
            raise ValueError(f"Bot '{model}' not found. Available bots: {list(self.avaliable_bots.keys())}")
        
        bot_class = self.avaliable_bots[model]
        if not virtual and bot_class.virtual_only:
            raise ValueError(f"Bot '{model}' cannot be used in a non-virtual game.")
        
        return bot_class(**params)