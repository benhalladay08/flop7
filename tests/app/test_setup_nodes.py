"""Tests for setup-flow nodes."""

import pytest

from flop7.app.nodes.game import _build_engine
from flop7.app.nodes.setup import PlayerNameNode


class TestPlayerNameNode:
    def test_accepts_unique_name(self):
        node = PlayerNameNode(index=2, total=3, names=["Alice"])

        assert node.prompt.validator(" Bob ") is None

    def test_rejects_exact_duplicate_name(self):
        node = PlayerNameNode(index=2, total=3, names=["Alice"])

        assert node.prompt.validator("Alice") == "Player names must be unique."

    def test_rejects_case_insensitive_duplicate_name(self):
        node = PlayerNameNode(index=2, total=3, names=["Alice"])

        assert node.prompt.validator("alice") == "Player names must be unique."

    def test_rejects_duplicate_name_after_stripping_whitespace(self):
        node = PlayerNameNode(index=2, total=3, names=["Alice"])

        assert node.prompt.validator("  Alice  ") == "Player names must be unique."

    def test_stores_stripped_name(self):
        context = {}
        node = PlayerNameNode(index=1, total=3)

        next_node = node.on_input(" Alice ", context)

        assert context["player_names"] == ["Alice"]
        assert isinstance(next_node, PlayerNameNode)


class TestBuildEnginePlayerNames:
    def test_rejects_duplicate_names_from_context(self):
        context = {
            "game_mode": "virtual",
            "player_names": ["Alice", "alice", "Carol"],
            "bot_types": [],
        }

        with pytest.raises(ValueError, match="Player names must be unique"):
            _build_engine(context)

    def test_generated_bot_names_do_not_collide_with_human_names(self):
        context = {
            "game_mode": "virtual",
            "player_names": ["Bot 1 (Basic)", "Alice"],
            "bot_types": ["Basic"],
        }

        engine = _build_engine(context)

        names = [player.name for player in engine.players]
        assert names == ["Bot 1 (Basic)", "Alice", "Bot 1 (Basic) #2"]
        assert len({name.casefold() for name in names}) == len(names)
