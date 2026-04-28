"""Tests for the TUI home screen."""

from flop7.tui.screens.home import HomeScreen


class TestHomeScreen:
    def test_constructs_without_terminal_state(self):
        screen = HomeScreen()

        assert screen._w is not None
