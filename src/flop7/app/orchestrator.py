from __future__ import annotations

from flop7.app.nodes import HomeNode, Node
from flop7.tui.app import TUIApp


class App:
    def __init__(self):
        self.context: dict = {}
        self.tui = TUIApp(self._handle_input)
        self._current_node: Node = HomeNode()
        self.tui.set_prompt(self._current_node.prompt)

    def run(self):
        self.tui.run()

    def _handle_input(self, value: str) -> None:
        next_node = self._current_node.on_input(value, self.context)

        if self.context.get("_quit"):
            self.tui.exit()
            return

        # --- Screen transitions requested by nodes ---
        if "_show_game" in self.context:
            engine = self.context.pop("_show_game")
            self.context["_game_screen"] = self.tui.show_game(engine)

        if self.context.pop("_show_home", False):
            self.context.pop("_game_screen", None)
            self.tui.show_home()

        if next_node is not None:
            # Resolve dispatcher nodes immediately to a real prompt-bearing node.
            while next_node.is_dispatcher:
                next_node = next_node.dispatch()
            self._current_node = next_node
            self.tui.set_prompt(self._current_node.prompt)