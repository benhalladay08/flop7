"""Tests for BasicBot decision logic."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from flop7.bot.models.basic import BasicBot
from flop7.core.classes.cards import (
    FIVE,
    FOUR,
    NINE,
    ONE,
    SECOND_CHANCE,
    SEVEN,
    SIX,
    TEN,
    THREE,
    TWELVE,
    TWO,
)
from flop7.core.classes.player import Player
from flop7.core.enum.decisions import TargetEvent

from tests.conftest import make_deck, make_engine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bot():
    return BasicBot()


@pytest.fixture
def game():
    """Minimal engine with 3 players – cards list doesn't matter here."""
    return make_engine(cards=[ONE, TWO, THREE], n_players=3)


# ---------------------------------------------------------------------------
# TestHitStay
# ---------------------------------------------------------------------------

class TestHitStay:
    """Verify the threshold-based hit/stay logic."""

    def test_hits_when_low_score(self, bot, game):
        """Bot hits when active_score is well below threshold."""
        p = game.players[0]
        p.hand = [ONE, TWO]  # active_score = 3
        assert bot.hit_stay(game, p) is True

    def test_stays_when_high_score(self, bot, game):
        """Bot stays when active_score exceeds 25."""
        p = game.players[0]
        p.hand = [TWELVE, TEN, FIVE]  # active_score = 27
        assert bot.hit_stay(game, p) is False

    def test_boundary_25_hits(self, bot, game):
        """Exactly 25 is at or below threshold – bot hits."""
        p = game.players[0]
        p.hand = [TWELVE, TEN, THREE]  # active_score = 25
        assert bot.hit_stay(game, p) is True

    def test_boundary_26_stays(self, bot, game):
        """26 exceeds threshold – bot stays."""
        p = game.players[0]
        p.hand = [TWELVE, TEN, FOUR]  # active_score = 26
        assert bot.hit_stay(game, p) is False

    def test_always_hits_with_second_chance(self, bot, game):
        """Bot always hits when it holds a Second Chance, even at high score."""
        p = game.players[0]
        p.hand = [TWELVE, TEN, FIVE, SECOND_CHANCE]  # active_score = 27
        assert bot.hit_stay(game, p) is True

    def test_hits_with_empty_hand(self, bot, game):
        """Bot hits with an empty hand (score 0)."""
        p = game.players[0]
        p.hand = []
        assert bot.hit_stay(game, p) is True


# ---------------------------------------------------------------------------
# TestTargetFlipThree
# ---------------------------------------------------------------------------

class TestTargetFlipThree:
    """Verify Flip Three targeting logic."""

    def test_self_targets_with_zero_cards(self, bot, game):
        """Bot targets itself when it has no cards."""
        p = game.players[0]
        p.hand = []
        result = bot.target_selector(game, TargetEvent.FLIP_THREE, p)
        assert result is p

    def test_self_targets_with_one_card(self, bot, game):
        """Bot targets itself when it has exactly one card."""
        p = game.players[0]
        p.hand = [ONE]
        result = bot.target_selector(game, TargetEvent.FLIP_THREE, p)
        assert result is p

    def test_targets_highest_scorer_with_many_cards(self, bot, game):
        """With 2+ cards, bot targets the player with the highest overall score."""
        p1, p2, p3 = game.players
        p1.hand = [FIVE, SIX]  # active_score = 11, overall = 11
        p2.score = 50  # overall = 50
        p3.score = 10  # overall = 10

        result = bot.target_selector(game, TargetEvent.FLIP_THREE, p1)
        assert result is p2

    def test_can_target_self_as_highest_scorer(self, bot, game):
        """Bot may target itself if it has the highest overall score."""
        p1, p2, p3 = game.players
        p1.hand = [FIVE, SIX]  # active_score = 11
        p1.score = 100  # overall = 111
        p2.score = 5
        p3.score = 5

        result = bot.target_selector(game, TargetEvent.FLIP_THREE, p1)
        assert result is p1

    def test_random_tiebreak(self, bot, game):
        """Tied players are passed to random.choice for tiebreaking."""
        p1, p2, p3 = game.players
        p1.hand = [FIVE, SIX]
        # p2 and p3 tied at 20
        p2.score = 20
        p3.score = 20

        with patch("flop7.bot.models.basic.random.choice") as mock_choice:
            mock_choice.return_value = p3
            result = bot.target_selector(game, TargetEvent.FLIP_THREE, p1)

        mock_choice.assert_called_once()
        candidates = mock_choice.call_args[0][0]
        assert set(candidates) == {p2, p3}
        assert result is p3


# ---------------------------------------------------------------------------
# TestTargetFreeze
# ---------------------------------------------------------------------------

class TestTargetFreeze:
    """Verify Freeze targeting logic."""

    def test_targets_highest_scorer_excluding_self(self, bot, game):
        """Bot freezes the highest-scoring opponent."""
        p1, p2, p3 = game.players
        p1.score = 100
        p2.score = 80
        p3.score = 50

        result = bot.target_selector(game, TargetEvent.FREEZE, p1)
        assert result is p2

    def test_skips_inactive_players(self, bot, game):
        """Inactive players are not eligible for freeze."""
        p1, p2, p3 = game.players
        p2.score = 80
        p2.is_active = False
        p3.score = 50

        result = bot.target_selector(game, TargetEvent.FREEZE, p1)
        assert result is p3

    def test_fallback_to_self_when_only_active(self, bot, game):
        """If all other players are inactive, bot targets itself."""
        p1, p2, p3 = game.players
        p2.is_active = False
        p3.is_active = False

        result = bot.target_selector(game, TargetEvent.FREEZE, p1)
        assert result is p1

    def test_random_tiebreak(self, bot, game):
        """Tied opponents are passed to random.choice."""
        p1, p2, p3 = game.players
        p2.score = 30
        p3.score = 30

        with patch("flop7.bot.models.basic.random.choice") as mock_choice:
            mock_choice.return_value = p2
            result = bot.target_selector(game, TargetEvent.FREEZE, p1)

        mock_choice.assert_called_once()
        candidates = mock_choice.call_args[0][0]
        assert set(candidates) == {p2, p3}
        assert result is p2


# ---------------------------------------------------------------------------
# TestTargetSecondChance
# ---------------------------------------------------------------------------

class TestTargetSecondChance:
    """Verify Second Chance targeting logic."""

    def test_targets_self_without_sc(self, bot, game):
        """Bot gives Second Chance to itself when it doesn't already have one."""
        p1 = game.players[0]
        p1.hand = [FIVE]

        result = bot.target_selector(game, TargetEvent.SECOND_CHANCE, p1)
        assert result is p1

    def test_targets_lowest_scorer_when_has_sc(self, bot, game):
        """When bot already has SC, it gives it to the lowest-scoring eligible player."""
        p1, p2, p3 = game.players
        p1.hand = [SECOND_CHANCE]
        p2.score = 80
        p3.score = 20

        result = bot.target_selector(game, TargetEvent.SECOND_CHANCE, p1)
        assert result is p3

    def test_skips_players_who_have_sc(self, bot, game):
        """Players who already have SC are not eligible."""
        p1, p2, p3 = game.players
        p1.hand = [SECOND_CHANCE]
        p2.hand = [SECOND_CHANCE]
        p2.score = 10  # lowest but ineligible
        p3.score = 50

        result = bot.target_selector(game, TargetEvent.SECOND_CHANCE, p1)
        assert result is p3

    def test_fallback_to_self_when_no_eligible(self, bot, game):
        """If all active players have SC, bot returns itself."""
        p1, p2, p3 = game.players
        p1.hand = [SECOND_CHANCE]
        p2.hand = [SECOND_CHANCE]
        p3.hand = [SECOND_CHANCE]

        result = bot.target_selector(game, TargetEvent.SECOND_CHANCE, p1)
        assert result is p1

    def test_random_tiebreak(self, bot, game):
        """Tied lowest-scoring eligible players go through random.choice."""
        p1, p2, p3 = game.players
        p1.hand = [SECOND_CHANCE]
        p2.score = 10
        p3.score = 10

        with patch("flop7.bot.models.basic.random.choice") as mock_choice:
            mock_choice.return_value = p2
            result = bot.target_selector(game, TargetEvent.SECOND_CHANCE, p1)

        mock_choice.assert_called_once()
        candidates = mock_choice.call_args[0][0]
        assert set(candidates) == {p2, p3}
        assert result is p2
