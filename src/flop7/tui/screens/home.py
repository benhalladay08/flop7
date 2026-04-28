import urwid

TITLE = """
███████╗██╗      ██████╗ ██████╗     ███████╗
██╔════╝██║     ██╔═══██╗██╔══██╗    ╚════██║
█████╗  ██║     ██║   ██║██████╔╝        ██╔╝
██╔══╝  ██║     ██║   ██║██╔═══╝        ██╔╝
██║     ███████╗╚██████╔╝██║            ██║ 
╚═╝     ╚══════╝ ╚═════╝ ╚═╝            ╚═╝ 
"""


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
