import urwid

_TITLE_LINES = [
    "███████╗██╗      ██████╗ ██████╗     ███████╗",
    "██╔════╝██║     ██╔═══██╗██╔══██╗    ╚════██║",
    "█████╗  ██║     ██║   ██║██████╔╝        ██╔╝",
    "██╔══╝  ██║     ██║   ██║██╔═══╝        ██╔╝",
    "██║     ███████╗╚██████╔╝██║            ██║",
    "╚═╝     ╚══════╝ ╚═════╝ ╚═╝            ╚═╝",
]
_TITLE_WIDTH = max(len(line) for line in _TITLE_LINES)
TITLE = "\n" + "\n".join(line.ljust(_TITLE_WIDTH) for line in _TITLE_LINES) + "\n"


class HomeScreen(urwid.WidgetWrap):
    """Simple home screen body content (footer is owned by TUIApp)."""

    def __init__(self) -> None:
        body = urwid.Filler(
            urwid.Pile(
                [
                    urwid.Text(("title", TITLE), align="center"),
                    urwid.Divider(),
                    urwid.Text("Type in the command bar below.", align="center"),
                ]
            ),
            valign="middle",
        )
        super().__init__(body)
