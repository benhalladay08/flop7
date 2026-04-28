"""Tests for simulation configuration validation and sampling."""

from flop7.simulation.config import sample_game_config, validate_sim_config


class TestValidateSimConfig:

    def test_valid_default_ranges(self):
        assert validate_sim_config((3, 10), {"Basic": (0, 10)}) is None

    def test_valid_multiple_bot_types(self):
        assert validate_sim_config((3, 10), {"Basic": (0, 10), "Omniscient": (0, 10)}) is None

    def test_valid_tight_range(self):
        assert validate_sim_config((5, 5), {"Basic": (5, 5)}) is None

    def test_invalid_bot_maxes_too_low(self):
        err = validate_sim_config((5, 10), {"Basic": (0, 2), "Omniscient": (0, 2)})
        assert err is not None
        assert "less than" in err

    def test_invalid_bot_mins_too_high(self):
        err = validate_sim_config((3, 5), {"Basic": (4, 10), "Omniscient": (4, 10)})
        assert err is not None
        assert "exceeds" in err

    def test_single_bot_type_valid(self):
        assert validate_sim_config((3, 3), {"Basic": (3, 3)}) is None


class TestSampleGameConfig:

    def test_sum_equals_player_count_in_range(self):
        for _ in range(50):
            config = sample_game_config((3, 10), {"Basic": (0, 10)})
            total = sum(config.values())
            assert 3 <= total <= 10

    def test_respects_per_type_min(self):
        for _ in range(50):
            config = sample_game_config(
                (6, 6),
                {"Basic": (3, 6), "Omniscient": (0, 3)},
            )
            assert config["Basic"] >= 3
            assert config["Omniscient"] >= 0
            assert sum(config.values()) == 6

    def test_respects_per_type_max(self):
        for _ in range(50):
            config = sample_game_config(
                (4, 4),
                {"Basic": (0, 2), "Omniscient": (0, 4)},
            )
            assert config["Basic"] <= 2
            assert config["Omniscient"] <= 4
            assert sum(config.values()) == 4

    def test_fixed_config(self):
        config = sample_game_config((5, 5), {"Basic": (5, 5)})
        assert config == {"Basic": 5}

    def test_multiple_types_sum_correctly(self):
        for _ in range(50):
            config = sample_game_config(
                (3, 10),
                {"Basic": (1, 5), "Omniscient": (1, 5)},
            )
            assert config["Basic"] >= 1
            assert config["Omniscient"] >= 1
            assert config["Basic"] <= 5
            assert config["Omniscient"] <= 5
            assert 3 <= sum(config.values()) <= 10
