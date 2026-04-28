"""Tests for the prompt data contract."""

from dataclasses import FrozenInstanceError

import pytest

from flop7.app.prompt import Prompt


class TestPrompt:
    def test_default_validator_accepts_anything(self):
        prompt = Prompt("Instruction")

        assert prompt.validator("anything") is None
        assert prompt.placeholder == ""
        assert prompt.auto_advance_ms is None

    def test_prompt_is_immutable(self):
        prompt = Prompt("Instruction")

        with pytest.raises(FrozenInstanceError):
            prompt.instruction = "Changed"
