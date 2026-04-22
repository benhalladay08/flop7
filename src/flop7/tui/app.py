from __future__ import annotations

from typing import TYPE_CHECKING

import urwid

from flop7.tui.screens.home import HomeScreen
from flop7.tui.widgets.command_bar import CommandBar

if TYPE_CHECKING:
    from flop7.app.prompt import Prompt


class TUIApp:
    def __init__(self, user_command: callable):
        self.user_command = user_command
        self.command_bar = CommandBar()
        self.home = HomeScreen()

        urwid.connect_signal(self.command_bar, "submitted", self._on_submitted)

        self.frame = urwid.Frame(
            body=self.home,
            footer=urwid.LineBox(self.command_bar, title="Command"),
            focus_part="footer",
        )

        self.loop = urwid.MainLoop(
            self.frame,
            palette=[
                ("title", "light cyan,bold", ""),
                ("instruction", "light cyan", ""),
                ("command", "white", ""),
                ("error", "light red", ""),
            ],
            unhandled_input=self._on_unhandled_input,
        )

    # --- public API ---------------------------------------------------

    def set_prompt(self, prompt: Prompt) -> None:
        """Push a new prompt to the command bar."""
        self.command_bar.set_prompt(prompt)

    def set_screen(self, body: urwid.Widget) -> None:
        """Swap only the body area; command bar/footer remains persistent."""
        self.frame.body = body

    def show_home(self) -> None:
        self.set_screen(HomeScreen())

    def run(self):
        self.loop.run()

    def exit(self):
        raise urwid.ExitMainLoop()

    # --- internal -----------------------------------------------------

    def _on_submitted(self, text: str) -> None:
        self.user_command(text)

    def _on_unhandled_input(self, key: str) -> None:
        if key in ("q", "Q", "esc"):
            raise urwid.ExitMainLoop()