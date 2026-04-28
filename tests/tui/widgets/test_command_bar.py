"""Tests for the command bar widget."""

import urwid

from flop7.app.prompt import Prompt
from flop7.tui.widgets.command_bar import CommandBar


class TestCommandBar:
    def test_set_prompt_updates_instruction_and_clears_input_and_error(self):
        bar = CommandBar()
        bar._edit.edit_text = "old"
        bar._set_error("bad")

        bar.set_prompt(Prompt("New prompt", validator=lambda _: None))

        assert bar.get_text() == ""
        assert bar._instruction.text == "New prompt"
        assert bar._error.text == ""
        assert len(bar._pile.contents) == 3

    def test_enter_with_invalid_input_shows_error_without_submit(self):
        bar = CommandBar()
        submitted = []
        urwid.connect_signal(bar, "submitted", submitted.append)
        bar.set_prompt(Prompt("Prompt", validator=lambda _: "Nope"))
        bar._edit.edit_text = "bad"

        assert bar.keypress((80,), "enter") is None

        assert submitted == []
        assert bar._error.text == "Nope"
        assert len(bar._pile.contents) == 5

    def test_enter_with_valid_input_submits_stripped_text(self):
        bar = CommandBar()
        submitted = []
        urwid.connect_signal(bar, "submitted", submitted.append)
        bar.set_prompt(Prompt("Prompt", validator=lambda _: None))
        bar._edit.edit_text = "  hit  "

        assert bar.keypress((80,), "enter") is None

        assert submitted == ["hit"]
        assert bar._error.text == ""
        assert bar.get_text() == ""

    def test_exit_bypasses_prompt_validator(self):
        bar = CommandBar()
        submitted = []
        urwid.connect_signal(bar, "submitted", submitted.append)
        bar.set_prompt(Prompt("Prompt", validator=lambda _: "Nope"))
        bar._edit.edit_text = "exit"

        bar.keypress((80,), "enter")

        assert submitted == ["exit"]
        assert bar._error.text == ""
