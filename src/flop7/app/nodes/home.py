from __future__ import annotations

from flop7.app.nodes.base import Node
from flop7.app.prompt import Prompt

_WELCOME = """\
Welcome to Flop 7: the unofficial terminal emulator for the popular card game! \
Flop 7 can be used to play virtually with friends or used as a scorekeeper for \
real games. It also offers a few different options for bots, which you can add \
to virtual or real games.

Flop 7 also allows you to test different bot algorithms against each other, to \
see which performs best. You can run hundreds or even thousands of games, \
configured in a variety of ways. If you're interested in building your own bot, \
visit our github for more info at https://github.com/benhalladay08/flop7.

Enter one of the following commands in the command bar to proceed.

- play: Start a game of Flip 7, either virtual or IRL.

- simulate: Run a batch of virtual games to pit bots against each other.

- exit: Quit the application.\

"""


def _home_validator(text: str) -> str | None:
    if text.lower() in ("play", "simulate"):
        return None
    return "Unknown command. Type 'play', 'simulate', or 'exit'."


class HomeNode(Node):
    @property
    def prompt(self) -> Prompt:
        return Prompt(
            instruction=_WELCOME,
            validator=_home_validator,
        )

    def on_input(self, value: str, context: dict) -> Node | None:
        from flop7.app.nodes.setup import GameModeNode  # avoid circular import

        cmd = value.lower()
        if cmd == "play":
            return GameModeNode()
        if cmd == "simulate":
            from flop7.app.nodes.simulate import SimPlayerCountNode

            context["_show_simulate"] = True
            return SimPlayerCountNode()
        return None
