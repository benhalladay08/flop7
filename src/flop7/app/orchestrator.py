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

        if next_node is not None:
            self._current_node = next_node
            self.tui.set_prompt(self._current_node.prompt)