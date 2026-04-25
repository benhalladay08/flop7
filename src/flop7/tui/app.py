from __future__ import annotations

from typing import TYPE_CHECKING

import urwid

from flop7.tui.screens.game import GameScreen
from flop7.tui.screens.home import HomeScreen
from flop7.tui.widgets.command_bar import CommandBar

if TYPE_CHECKING:
    from flop7.app.prompt import Prompt


class TUIApp:
    def __init__(self, user_command: callable):
        self.user_command = user_command
        self.command_bar = CommandBar()
        self.home = HomeScreen()
        self._auto_advance_handle = None

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
                ("active", "white,bold", ""),
                ("dimmed", "dark gray", ""),
                ("busted", "light red", ""),
            ],
            unhandled_input=self._on_unhandled_input,
        )

    # --- public API ---------------------------------------------------

    def set_prompt(self, prompt: Prompt) -> None:
        """Push a new prompt to the command bar.

        If the prompt declares ``auto_advance_ms``, schedule a timer that
        will submit an empty string when it fires (unless the user submits
        something first).
        """
        self.command_bar.set_prompt(prompt)
        self._cancel_auto_advance()
        if prompt.auto_advance_ms is not None:
            seconds = prompt.auto_advance_ms / 1000.0
            self._auto_advance_handle = self.loop.set_alarm_in(
                seconds, self._on_auto_advance,
            )

    def set_screen(self, body: urwid.Widget) -> None:
        """Swap only the body area; command bar/footer remains persistent."""
        self.frame.body = body

    def show_home(self) -> None:
        self.set_screen(HomeScreen())

    def show_game(self, engine, focused_idx: int = 0) -> GameScreen:
        """Switch to the game screen and return it for later updates."""
        screen = GameScreen(engine=engine, focused_idx=focused_idx)
        self.set_screen(screen)
        return screen

    def run(self):
        self.loop.run()

    def exit(self):
        raise urwid.ExitMainLoop()

    # --- internal -----------------------------------------------------

    def _on_submitted(self, text: str) -> None:
        self._cancel_auto_advance()
        self.user_command(text)

    def _on_auto_advance(self, loop, user_data) -> None:
        self._auto_advance_handle = None
        self.user_command("")

    def _cancel_auto_advance(self) -> None:
        if self._auto_advance_handle is not None:
            self.loop.remove_alarm(self._auto_advance_handle)
            self._auto_advance_handle = None

    def _on_unhandled_input(self, key: str) -> None:
        if key in ("q", "Q", "esc"):
            raise urwid.ExitMainLoop()