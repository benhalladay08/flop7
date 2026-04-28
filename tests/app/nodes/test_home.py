"""Tests for home-flow nodes."""

from flop7.app.nodes.home import HomeNode, _home_validator
from flop7.app.nodes.setup import GameModeNode
from flop7.app.nodes.simulate import SimPlayerCountNode


class TestHomeValidator:
    def test_accepts_known_commands_case_insensitively(self):
        assert _home_validator(" PLAY ") is None
        assert _home_validator("simulate") is None
        assert _home_validator("exit") is None

    def test_rejects_unknown_command(self):
        assert _home_validator("settings") == (
            "Unknown command. Type 'play', 'simulate', or 'exit'."
        )


class TestHomeNode:
    def test_play_starts_setup_flow(self):
        next_node = HomeNode().on_input("play", {})

        assert isinstance(next_node, GameModeNode)

    def test_simulate_sets_screen_transition_flag(self):
        context = {}

        next_node = HomeNode().on_input("simulate", context)

        assert isinstance(next_node, SimPlayerCountNode)
        assert context["_show_simulate"] is True

    def test_exit_stays_on_home_node_for_tui_exit_handler(self):
        assert HomeNode().on_input("exit", {}) is None
