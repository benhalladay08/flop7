from flop7.bot.base import AbstractBot

class OmniscientBot(AbstractBot):
    """
    Bot with perfect information about the game state. Used for testing and benchmarking.
    """

    virtual_only = True

    ...