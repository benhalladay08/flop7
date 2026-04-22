from __future__ import annotations

from typing import TYPE_CHECKING

import urwid

if TYPE_CHECKING:
    from flop7.app.prompt import Prompt


class CommandBar(urwid.WidgetWrap):
    """Three-zone command bar: instruction, input, error.

    Driven entirely by a ``Prompt`` pushed from the orchestrator via
    ``set_prompt()``.  Emits the ``"submitted"`` signal with the raw
    (already-validated) input string on Enter.
    """

    signals = ["submitted"]

    def __init__(self) -> None:
        self._validator = lambda _: None

        self._instruction = urwid.Text("")
        self._edit = urwid.Edit(caption="> ")
        self._error = urwid.Text("")
        self._error_attrmap = urwid.AttrMap(self._error, "error")
        self._spacer = urwid.Text("")

        self._pile = urwid.Pile([
            urwid.AttrMap(self._instruction, "instruction"),
            urwid.Divider("─"),
            urwid.AttrMap(self._edit, "command"),
        ])
        super().__init__(self._pile)

    # --- public API ---------------------------------------------------

    def set_prompt(self, prompt: Prompt) -> None:
        """Apply a new prompt: update instruction, clear input & error."""
        self._instruction.set_text(prompt.instruction)
        self._edit.edit_text = ""
        self._set_error(None)
        self._validator = prompt.validator

    def get_text(self) -> str:
        return self._edit.edit_text

    def clear(self) -> None:
        self._edit.edit_text = ""

    # --- key handling -------------------------------------------------

    def keypress(self, size: tuple[int], key: str) -> str | None:
        if key == "enter":
            text = self._edit.edit_text.strip()
            self._edit.edit_text = ""
            error = self._validator(text)
            if error is not None:
                self._set_error(error)
            else:
                self._set_error(None)
                urwid.emit_signal(self, "submitted", text)
            return None  # consumed

        return super().keypress(size, key)

    # --- internal -----------------------------------------------------

    def _set_error(self, message: str | None) -> None:
        """Show or hide the spacer+error rows below the input."""
        if message:
            self._error.set_text(message)
            if len(self._pile.contents) == 3:
                opts = self._pile.options()
                self._pile.contents += [
                    (self._spacer, opts),
                    (self._error_attrmap, opts),
                ]
        else:
            self._error.set_text("")
            if len(self._pile.contents) > 3:
                self._pile.contents = self._pile.contents[:3]


