import urwid

from flop7.tui.screens.home import HomeScreen
from flop7.tui.widgets.command_bar import CommandBar

class TUIApp:
    def __init__(self, user_command: callable):
        self.user_command = user_command
        self.command_bar = CommandBar()
        self.home = HomeScreen()

        self.frame = urwid.Frame(
            body=self.home,
            footer=urwid.LineBox(self.command_bar, title="Command"),
            focus_part="footer",
        )

        self.loop = urwid.MainLoop(
            self.frame,
            palette=[
                ("title", "light cyan,bold", ""),
                ("command", "white", ""),
            ],
            unhandled_input=self._on_unhandled_input,
        )

    def set_screen(self, body: urwid.Widget) -> None:
        """Swap only the body area; command bar/footer remains persistent."""
        self.frame.body = body

    def show_home(self) -> None:
        self.set_screen(HomeScreen())

    def set_command_prompt(self, prompt: str) -> None:
        self.command_bar.edit.set_caption(prompt)

    def get_command_text(self) -> str:
        return self.command_bar.get_text()

    def clear_command(self) -> None:
        self.command_bar.clear()

    def _on_unhandled_input(self, key: str) -> None:
        if key in ("q", "Q", "esc"):
            raise urwid.ExitMainLoop()

        if key == "enter":
            command = self.command_bar.get_text().strip()
            if command:
                self.user_command(command)
            self.command_bar.clear()

    def run(self):
        self.loop.run()

    def exit(self):
        raise urwid.ExitMainLoop()