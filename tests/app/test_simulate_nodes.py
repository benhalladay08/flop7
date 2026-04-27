"""Tests for flop7.app.nodes.simulate — simulation configuration and run nodes."""

from flop7.app.nodes.simulate import (
    SimBotConfigNode,
    SimConfirmNode,
    SimDoneNode,
    SimGameCountNode,
    SimPlayerCountNode,
    SimRunNode,
    _parse_range,
)


class TestParseRange:

    def test_valid_range(self):
        assert _parse_range("3-10", 0, 10) == (3, 10)

    def test_single_number(self):
        assert _parse_range("5", 0, 10) == (5, 5)

    def test_equal_bounds(self):
        assert _parse_range("7-7", 0, 10) == (7, 7)

    def test_out_of_bounds_low(self):
        result = _parse_range("1-5", 3, 10)
        assert isinstance(result, str)

    def test_out_of_bounds_high(self):
        result = _parse_range("3-15", 3, 10)
        assert isinstance(result, str)

    def test_min_exceeds_max(self):
        result = _parse_range("7-3", 0, 10)
        assert isinstance(result, str)

    def test_non_numeric(self):
        result = _parse_range("abc", 0, 10)
        assert isinstance(result, str)

    def test_spaces_stripped(self):
        assert _parse_range(" 3 - 10 ", 0, 10) == (3, 10)


class TestSimPlayerCountNode:

    def test_default_on_empty_input(self):
        node = SimPlayerCountNode()
        context = {}
        next_node = node.on_input("", context)
        assert context["sim_player_range"] == (3, 10)
        assert isinstance(next_node, SimBotConfigNode)

    def test_custom_range(self):
        node = SimPlayerCountNode()
        context = {}
        next_node = node.on_input("4-8", context)
        assert context["sim_player_range"] == (4, 8)
        assert isinstance(next_node, SimBotConfigNode)

    def test_validator_rejects_invalid(self):
        node = SimPlayerCountNode()
        err = node.prompt.validator("1-2")
        assert err is not None

    def test_validator_accepts_valid(self):
        node = SimPlayerCountNode()
        assert node.prompt.validator("3-10") is None
        assert node.prompt.validator("") is None


class TestSimBotConfigNode:

    def test_first_bot_type(self):
        node = SimBotConfigNode(index=0, bot_names=["Basic", "Omniscient"], ranges={})
        context = {"sim_bot_ranges": {}}
        next_node = node.on_input("1-5", context)
        assert context["sim_bot_ranges"]["Basic"] == (1, 5)
        assert isinstance(next_node, SimBotConfigNode)

    def test_last_bot_type_returns_game_count(self):
        node = SimBotConfigNode(
            index=1,
            bot_names=["Basic", "Omniscient"],
            ranges={"Basic": (0, 10)},
        )
        context = {"sim_bot_ranges": {"Basic": (0, 10)}}
        next_node = node.on_input("0-5", context)
        assert context["sim_bot_ranges"]["Omniscient"] == (0, 5)
        assert isinstance(next_node, SimGameCountNode)

    def test_default_on_empty(self):
        node = SimBotConfigNode(index=0, bot_names=["Basic"], ranges={})
        context = {"sim_bot_ranges": {}}
        node.on_input("", context)
        assert context["sim_bot_ranges"]["Basic"] == (0, 10)


class TestSimGameCountNode:

    def test_stores_count(self):
        node = SimGameCountNode()
        context = {}
        next_node = node.on_input("1000", context)
        assert context["sim_game_count"] == 1000
        assert isinstance(next_node, SimConfirmNode)

    def test_accepts_commas(self):
        node = SimGameCountNode()
        context = {}
        node.on_input("10,000", context)
        assert context["sim_game_count"] == 10000

    def test_validator_rejects_zero(self):
        node = SimGameCountNode()
        assert node.prompt.validator("0") is not None

    def test_validator_rejects_too_large(self):
        node = SimGameCountNode()
        assert node.prompt.validator("200000") is not None

    def test_validator_accepts_valid(self):
        node = SimGameCountNode()
        assert node.prompt.validator("100") is None


class TestSimConfirmNode:

    def test_valid_config_returns_run_node(self):
        node = SimConfirmNode()
        context = {
            "sim_player_range": (3, 10),
            "sim_bot_ranges": {"Basic": (0, 10)},
            "sim_game_count": 10,
        }
        next_node = node.on_input("", context)
        assert isinstance(next_node, SimRunNode)

    def test_invalid_config_returns_error_confirm(self):
        node = SimConfirmNode()
        context = {
            "sim_player_range": (3, 3),
            "sim_bot_ranges": {"Basic": (0, 1), "Omniscient": (0, 1)},
            "sim_game_count": 10,
        }
        next_node = node.on_input("", context)
        assert isinstance(next_node, SimConfirmNode)
        assert next_node._error is not None

    def test_error_node_returns_to_player_count(self):
        node = SimConfirmNode(error="test error")
        context = {}
        next_node = node.on_input("", context)
        assert isinstance(next_node, SimPlayerCountNode)


class TestSimRunNode:

    def test_runs_batch_and_returns_self(self):
        node = SimRunNode(
            player_range=(3, 3),
            bot_ranges={"Basic": (3, 3)},
            total=10,
        )
        context = {}
        next_node = node.on_input("", context)
        # Should return another SimRunNode (batch of 50, but only 10 total)
        # Actually 10 < 50 so it finishes in one batch
        assert isinstance(next_node, SimDoneNode)

    def test_multiple_batches(self):
        node = SimRunNode(
            player_range=(3, 3),
            bot_ranges={"Basic": (3, 3)},
            total=100,
        )
        context = {}
        next_node = node.on_input("", context)
        # First batch of 50, 50 remaining
        assert isinstance(next_node, SimRunNode)
        next_node = next_node.on_input("", context)
        # Second batch of 50, done
        assert isinstance(next_node, SimDoneNode)

    def test_cancel_returns_done_cancelled(self):
        node = SimRunNode(
            player_range=(3, 3),
            bot_ranges={"Basic": (3, 3)},
            total=100,
        )
        context = {}
        next_node = node.on_input("cancel", context)
        assert isinstance(next_node, SimDoneNode)
        assert next_node._cancelled is True

    def test_has_auto_advance(self):
        node = SimRunNode(
            player_range=(3, 3),
            bot_ranges={"Basic": (3, 3)},
            total=10,
        )
        assert node.prompt.auto_advance_ms == 1


class TestSimDoneNode:

    def test_returns_home_node(self):
        from flop7.app.nodes.home import HomeNode
        from flop7.app.simulation import SimulationResults

        node = SimDoneNode(SimulationResults())
        context = {}
        next_node = node.on_input("home", context)
        assert isinstance(next_node, HomeNode)
        assert context["_show_home"] is True

    def test_validator_rejects_non_home(self):
        from flop7.app.simulation import SimulationResults

        node = SimDoneNode(SimulationResults())
        assert node.prompt.validator("quit") is not None
        assert node.prompt.validator("home") is None

    def test_cancelled_message(self):
        from flop7.app.simulation import SimulationResults

        node = SimDoneNode(SimulationResults(), cancelled=True)
        assert "cancelled" in node.prompt.instruction.lower()
