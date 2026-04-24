"""Tests for BasicBot decision logic."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from flop7.bot.knowledge import build_game_view
from flop7.bot.models.basic import BasicBot
from flop7.core.classes.cards import (
    FIVE,
    FOUR,
    ONE,
    SECOND_CHANCE,
    SIX,
    TEN,
    THREE,
    TWELVE,
    TWO,
)
from flop7.core.enum.decisions import TargetEvent

from tests.conftest import make_engine


@pytest.fixture
def bot():
    return BasicBot()


@pytest.fixture
def game():
    """Minimal engine with 3 players; cards list does not matter here."""
    return make_engine(cards=[ONE, TWO, THREE], n_players=3)


def _view(game):
    return build_game_view(game)


def _target(bot, game, event, source_index, eligible_indexes):
    view = _view(game)
    eligible = tuple(view.players[i] for i in eligible_indexes)
    return bot.target_selector(view, event, view.players[source_index], eligible)


class TestHitStay:
    """Verify the threshold-based hit/stay logic."""

    def test_hits_when_low_score(self, bot, game):
        game.players[0].hand = [ONE, TWO]
        view = _view(game)
        assert bot.hit_stay(view, view.players[0]) is True

    def test_stays_when_high_score(self, bot, game):
        game.players[0].hand = [TWELVE, TEN, FIVE]
        view = _view(game)
        assert bot.hit_stay(view, view.players[0]) is False

    def test_boundary_25_hits(self, bot, game):
        game.players[0].hand = [TWELVE, TEN, THREE]
        view = _view(game)
        assert bot.hit_stay(view, view.players[0]) is True

    def test_boundary_26_stays(self, bot, game):
        game.players[0].hand = [TWELVE, TEN, FOUR]
        view = _view(game)
        assert bot.hit_stay(view, view.players[0]) is False

    def test_always_hits_with_second_chance(self, bot, game):
        game.players[0].hand = [TWELVE, TEN, FIVE, SECOND_CHANCE]
        view = _view(game)
        assert bot.hit_stay(view, view.players[0]) is True

    def test_hits_with_empty_hand(self, bot, game):
        game.players[0].hand = []
        view = _view(game)
        assert bot.hit_stay(view, view.players[0]) is True


class TestTargetFlipThree:
    """Verify Flip Three targeting logic."""

    def test_self_targets_with_zero_cards(self, bot, game):
        game.players[0].hand = []
        result = _target(bot, game, TargetEvent.FLIP_THREE, 0, [0, 1, 2])
        assert result.index == 0

    def test_self_targets_with_one_card(self, bot, game):
        game.players[0].hand = [ONE]
        result = _target(bot, game, TargetEvent.FLIP_THREE, 0, [0, 1, 2])
        assert result.index == 0

    def test_targets_highest_scorer_with_many_cards(self, bot, game):
        p1, p2, p3 = game.players
        p1.hand = [FIVE, SIX]
        p2.score = 50
        p3.score = 10

        result = _target(bot, game, TargetEvent.FLIP_THREE, 0, [0, 1, 2])
        assert result.index == 1

    def test_can_target_self_as_highest_scorer(self, bot, game):
        p1, p2, p3 = game.players
        p1.hand = [FIVE, SIX]
        p1.score = 100
        p2.score = 5
        p3.score = 5

        result = _target(bot, game, TargetEvent.FLIP_THREE, 0, [0, 1, 2])
        assert result.index == 0

    def test_random_tiebreak(self, bot, game):
        p1, p2, p3 = game.players
        p1.hand = [FIVE, SIX]
        p2.score = 20
        p3.score = 20
        view = _view(game)

        with patch("flop7.bot.models.basic.random.choice") as mock_choice:
            mock_choice.return_value = view.players[2]
            result = bot.target_selector(
                view,
                TargetEvent.FLIP_THREE,
                view.players[0],
                view.players,
            )

        mock_choice.assert_called_once()
        candidates = mock_choice.call_args[0][0]
        assert {c.index for c in candidates} == {1, 2}
        assert result.index == 2


class TestTargetFreeze:
    """Verify Freeze targeting logic."""

    def test_targets_highest_scorer_excluding_self(self, bot, game):
        p1, p2, p3 = game.players
        p1.score = 100
        p2.score = 80
        p3.score = 50

        result = _target(bot, game, TargetEvent.FREEZE, 0, [0, 1, 2])
        assert result.index == 1

    def test_uses_engine_provided_eligible_players(self, bot, game):
        p1, p2, p3 = game.players
        p1.score = 100
        p2.score = 80
        p3.score = 50

        result = _target(bot, game, TargetEvent.FREEZE, 0, [0, 2])
        assert result.index == 2

    def test_fallback_to_self_when_only_active(self, bot, game):
        result = _target(bot, game, TargetEvent.FREEZE, 0, [0])
        assert result.index == 0

    def test_random_tiebreak(self, bot, game):
        p2, p3 = game.players[1:]
        p2.score = 30
        p3.score = 30
        view = _view(game)
        eligible = tuple(view.players[i] for i in [0, 1, 2])

        with patch("flop7.bot.models.basic.random.choice") as mock_choice:
            mock_choice.return_value = view.players[1]
            result = bot.target_selector(
                view,
                TargetEvent.FREEZE,
                view.players[0],
                eligible,
            )

        mock_choice.assert_called_once()
        candidates = mock_choice.call_args[0][0]
        assert {c.index for c in candidates} == {1, 2}
        assert result.index == 1


class TestTargetSecondChance:
    """Verify duplicate Second Chance re-gifting logic."""

    def test_targets_lowest_scorer(self, bot, game):
        p2, p3 = game.players[1:]
        p2.score = 80
        p3.score = 20

        result = _target(bot, game, TargetEvent.SECOND_CHANCE, 0, [1, 2])
        assert result.index == 2

    def test_uses_engine_provided_eligible_players(self, bot, game):
        game.players[1].score = 10
        game.players[2].score = 50

        result = _target(bot, game, TargetEvent.SECOND_CHANCE, 0, [2])
        assert result.index == 2

    def test_fallback_to_self_when_no_eligible(self, bot, game):
        result = _target(bot, game, TargetEvent.SECOND_CHANCE, 0, [])
        assert result.index == 0

    def test_random_tiebreak(self, bot, game):
        game.players[1].score = 10
        game.players[2].score = 10
        view = _view(game)
        eligible = tuple(view.players[i] for i in [1, 2])

        with patch("flop7.bot.models.basic.random.choice") as mock_choice:
            mock_choice.return_value = view.players[1]
            result = bot.target_selector(
                view,
                TargetEvent.SECOND_CHANCE,
                view.players[0],
                eligible,
            )

        mock_choice.assert_called_once()
        candidates = mock_choice.call_args[0][0]
        assert {c.index for c in candidates} == {1, 2}
        assert result.index == 1
