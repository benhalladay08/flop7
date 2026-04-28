"""Tests for TUI app event handling."""

from types import SimpleNamespace

from flop7.app.prompt import Prompt
from flop7.tui.app import TUIApp


class FakeCommandBar:
    def __init__(self):
        self.prompts = []

    def set_prompt(self, prompt):
        self.prompts.append(prompt)


class FakeLoop:
    def __init__(self):
        self.alarms = []
        self.removed = []
        self.widget = None

    def set_alarm_in(self, seconds, callback):
        handle = object()
        self.alarms.append((seconds, callback, handle))
        return handle

    def remove_alarm(self, handle):
        self.removed.append(handle)


def make_app(user_command=None) -> TUIApp:
    app = TUIApp.__new__(TUIApp)
    app.user_command = user_command or (lambda value: None)
    app.command_bar = FakeCommandBar()
    app.loop = FakeLoop()
    app.frame = SimpleNamespace(body=None)
    app._auto_advance_handle = None
    app._quit_dialog_active = False
    return app


class TestTUIAppPrompts:
    def test_set_prompt_schedules_auto_advance(self):
        app = make_app()

        app.set_prompt(Prompt("Next", auto_advance_ms=500))

        assert app.command_bar.prompts[-1].instruction == "Next"
        assert len(app.loop.alarms) == 1
        assert app.loop.alarms[0][0] == 0.5
        assert app._auto_advance_handle is app.loop.alarms[0][2]

    def test_set_prompt_cancels_existing_auto_advance(self):
        app = make_app()
        app._auto_advance_handle = object()
        old_handle = app._auto_advance_handle

        app.set_prompt(Prompt("Next"))

        assert app.loop.removed == [old_handle]
        assert app._auto_advance_handle is None


class TestTUIAppInput:
    def test_submitted_input_cancels_alarm_and_calls_user_command(self):
        received = []
        app = make_app(received.append)
        app._auto_advance_handle = object()

        app._on_submitted("hit")

        assert received == ["hit"]
        assert app.loop.removed
        assert app._auto_advance_handle is None

    def test_exit_submission_opens_quit_dialog(self, monkeypatch):
        app = make_app()
        calls = []
        monkeypatch.setattr(app, "show_quit_dialog", lambda: calls.append("quit"))

        app._on_submitted(" EXIT ")

        assert calls == ["quit"]

    def test_auto_advance_submits_empty_input(self):
        received = []
        app = make_app(received.append)
        app._auto_advance_handle = object()

        app._on_auto_advance(None, None)

        assert received == [""]
        assert app._auto_advance_handle is None

    def test_escape_dismisses_active_quit_dialog(self, monkeypatch):
        app = make_app()
        app._quit_dialog_active = True
        calls = []
        monkeypatch.setattr(app, "_dismiss_quit_dialog", lambda: calls.append("esc"))

        app._on_unhandled_input("esc")

        assert calls == ["esc"]

    def test_ctrl_c_opens_quit_dialog(self, monkeypatch):
        app = make_app()
        calls = []
        monkeypatch.setattr(app, "show_quit_dialog", lambda: calls.append("quit"))

        app._on_unhandled_input("ctrl c")

        assert calls == ["quit"]
