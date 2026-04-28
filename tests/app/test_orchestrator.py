"""Tests for app-level node orchestration."""

from flop7.app.nodes.base import Node
from flop7.app.orchestrator import App
from flop7.app.prompt import Prompt


class FakeTUI:
    def __init__(self, user_command):
        self.user_command = user_command
        self.prompts = []
        self.game_screen = object()
        self.sim_screen = object()
        self.show_game_calls = []
        self.show_home_calls = 0
        self.show_simulate_calls = 0

    def set_prompt(self, prompt):
        self.prompts.append(prompt)

    def show_game(self, engine):
        self.show_game_calls.append(engine)
        return self.game_screen

    def show_simulate(self):
        self.show_simulate_calls += 1
        return self.sim_screen

    def show_home(self):
        self.show_home_calls += 1

    def run(self):
        pass


class StaticNode(Node):
    def __init__(self, next_node=None, context_updates=None):
        self.next_node = next_node
        self.context_updates = context_updates or {}

    @property
    def prompt(self) -> Prompt:
        return Prompt("static")

    def on_input(self, value: str, context: dict) -> Node | None:
        context.update(self.context_updates)
        return self.next_node


class DispatcherNode(Node):
    is_dispatcher = True

    @property
    def prompt(self) -> Prompt:
        raise AssertionError("dispatcher prompt should not be read")

    def on_input(self, value: str, context: dict) -> Node | None:
        raise AssertionError("dispatcher should not receive input")

    def dispatch(self, context: dict) -> Node:
        return StaticNode()


def test_app_initializes_home_prompt(monkeypatch):
    monkeypatch.setattr("flop7.app.orchestrator.TUIApp", FakeTUI)

    app = App()

    assert len(app.tui.prompts) == 1
    assert "Welcome to Flop 7" in app.tui.prompts[0].instruction


def test_handle_input_processes_screen_transition_flags(monkeypatch):
    monkeypatch.setattr("flop7.app.orchestrator.TUIApp", FakeTUI)
    engine = object()
    app = App()
    app._current_node = StaticNode(
        context_updates={
            "_show_game": engine,
            "_show_simulate": True,
            "_show_home": True,
        }
    )

    app._handle_input("")

    assert app.tui.show_game_calls == [engine]
    assert app.tui.show_simulate_calls == 1
    assert app.tui.show_home_calls == 1
    assert "_game_screen" not in app.context
    assert "_sim_screen" not in app.context


def test_handle_input_resolves_dispatcher_nodes(monkeypatch):
    monkeypatch.setattr("flop7.app.orchestrator.TUIApp", FakeTUI)
    app = App()
    app._current_node = StaticNode(next_node=DispatcherNode())

    app._handle_input("")

    assert isinstance(app._current_node, StaticNode)
    assert app.tui.prompts[-1].instruction == "static"
