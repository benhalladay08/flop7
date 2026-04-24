"""Tests for flop7.core.engine.engine — GameEngine round lifecycle, scoring, and win conditions.

These tests drive the generator-based round() method using the helpers from
conftest.  Where tests assert behaviour that differs from the current source,
the test is written to match rules.md and the source is fixed.
"""
import pytest
from unittest.mock import MagicMock

from flop7.core.classes.cards import (
    Card,
    FIVE,
    THREE,
    SEVEN,
    NINE,
    TEN,
    ELEVEN,
    TWELVE,
    ZERO,
    ONE,
    TWO,
    FOUR,
    SIX,
    EIGHT,
    PLUS_FOUR,
    PLUS_TWO,
    TIMES_TWO,
    SECOND_CHANCE,
    FREEZE,
    FLIP_THREE,
)
from flop7.core.classes.player import Player
from flop7.core.engine.engine import GameEngine
from flop7.core.engine.requests import (
    CardDrawnEvent,
    CardInputRequest,
    Flip7Event,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
    TargetRequest,
)

from tests.conftest import drive_round, make_deck, make_engine, make_players


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestConstructor:

    def test_fewer_than_3_players_raises(self):
        deck = make_deck([])
        with pytest.raises(ValueError, match="at least 3"):
            GameEngine(deck, make_players(2), lambda g, p: True, lambda g, e, s: s)

    def test_exactly_3_players_ok(self):
        deck = make_deck([FIVE])
        engine = GameEngine(deck, make_players(3), lambda g, p: True, lambda g, e, s: s)
        assert len(engine.players) == 3

    def test_initial_state(self):
        deck = make_deck([])
        engine = GameEngine(deck, make_players(3), lambda g, p: True, lambda g, e, s: s)
        assert engine.round_number == 0
        assert engine.game_over is False
        assert engine.winner is None


# ---------------------------------------------------------------------------
# active_players property
# ---------------------------------------------------------------------------

class TestActivePlayers:

    def test_all_active_initially(self):
        engine = make_engine([], n_players=3)
        assert len(engine.active_players) == 3

    def test_excludes_inactive(self):
        engine = make_engine([], n_players=3)
        engine.players[0].is_active = False
        assert len(engine.active_players) == 2
        assert engine.players[0] not in engine.active_players


# ---------------------------------------------------------------------------
# Round generator — basic flow
# ---------------------------------------------------------------------------

class TestRoundBasicFlow:

    def test_first_yield_is_hit_stay_request(self):
        """First yield of round() should be HitStayRequest for the first player."""
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        gen = engine.round()
        req = next(gen)
        assert isinstance(req, HitStayRequest)
        assert req.player is engine.players[0]

    def test_stay_makes_player_inactive(self):
        """Sending False (stay) deactivates the player.

        Scenario: 3 players, all stay immediately.
        Each player gets a HitStayRequest before the round ends.
        """
        engine = make_engine([], n_players=3)
        # All 3 players stay → round ends
        events = drive_round(engine, hit_responses=[False, False, False])
        # Should see 3 HitStayRequests + RoundOverEvent
        hit_stay_events = [e for e in events if isinstance(e, HitStayRequest)]
        assert len(hit_stay_events) == 3
        assert any(isinstance(e, RoundOverEvent) for e in events)

    def test_hit_yields_card_drawn_event(self):
        """Hitting deals a card and yields CardDrawnEvent.

        Scenario: P1 hits (gets FIVE), P2 stays, P3 stays → round ends.
        After P1 hits, only P1 is active (P2, P3 stayed).
        Actually after P1 hits, P2 and P3 still need their turns.
        """
        engine = make_engine([FIVE], n_players=3)
        # P1 hits, P2 stays, P3 stays. After full loop, only P1 active →
        # loop condition (>1) fails → round ends.
        events = drive_round(engine, hit_responses=[True, False, False])
        drawn_events = [e for e in events if isinstance(e, CardDrawnEvent)]
        assert len(drawn_events) == 1
        assert drawn_events[0].card is FIVE
        assert drawn_events[0].player is engine.players[0]


# ---------------------------------------------------------------------------
# Bust mechanics
# ---------------------------------------------------------------------------

class TestBust:

    def test_duplicate_number_causes_bust(self):
        """Player with FIVE already in hand draws another FIVE → bust."""
        engine = make_engine([FIVE, THREE, SEVEN, FIVE], n_players=3)
        p1 = engine.players[0]

        # P1 hit (FIVE), P2 hit (THREE), P3 hit (SEVEN),
        # P1 hit (FIVE dup → bust), P2 stay, P3 stay
        events = drive_round(
            engine,
            hit_responses=[True, True, True, True, False, False],
        )
        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 1
        assert bust_events[0].player is p1

    def test_bust_within_single_round(self):
        """P1 hits twice in one round: first gets FIVE, second gets duplicate FIVE → bust.

        With 3 players: P1 hits (FIVE), P2 hits (THREE), P3 hits (SEVEN),
        loop continues: P1 hits again (FIVE dup) → bust,
        then P2 stays, P3 stays → round ends.
        """
        engine = make_engine([FIVE, THREE, SEVEN, FIVE], n_players=3)
        p1 = engine.players[0]
        # P1 hit, P2 hit, P3 hit, P1 hit (bust), P2 stay, P3 stay
        events = drive_round(
            engine,
            hit_responses=[True, True, True, True, False, False],
        )
        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 1
        assert bust_events[0].player is p1

    def test_bust_preserves_cumulative_score(self):
        """Per rules.md: busting scores 0 for the ROUND, not the entire game.

        P1 has cumulative score 50 from prior rounds. P1 busts this round.
        After end-of-round scoring, P1's score should still be 50.
        """
        engine = make_engine([FIVE, THREE, SEVEN, FIVE], n_players=3)
        p1 = engine.players[0]
        p1.score = 50  # simulate prior rounds

        # P1 hit (FIVE), P2 hit (THREE), P3 hit (SEVEN),
        # P1 hit (FIVE dup → bust), P2 stay, P3 stay
        events = drive_round(
            engine,
            hit_responses=[True, True, True, True, False, False],
        )
        # After round, P1 should still have 50 (busted → 0 for this round)
        assert p1.score == 50, (
            f"Bust should not wipe cumulative score. Expected 50, got {p1.score}"
        )

    def test_non_bustable_card_no_bust(self):
        """Modifier cards never cause busts even if player already has one."""
        engine = make_engine([PLUS_FOUR, PLUS_FOUR], n_players=3)
        p1 = engine.players[0]
        # P1 hits twice: gets +4, then +4 again (not bustable)
        # P2 and P3 stay after first loop. But P1 needs to get both +4s.
        # Actually: P1 hit (+4), P2 stay, P3 stay → round ends (only P1 active,
        # which is ≤1 so loop exits). Let's use a different scenario.
        # P1 hit (+4), P2 hit (some card), P3 stay
        # then P1 hit (+4), P2 stay → round ends
        engine2 = make_engine([PLUS_FOUR, THREE, PLUS_FOUR], n_players=3)
        events = drive_round(
            engine2,
            hit_responses=[True, True, False, True, False],
        )
        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 0


# ---------------------------------------------------------------------------
# Second Chance absorption
# ---------------------------------------------------------------------------

class TestSecondChanceAbsorption:

    def test_second_chance_absorbs_duplicate(self):
        """Player with SC + FIVE, draws duplicate FIVE → no bust, SC + dup discarded."""
        engine = make_engine([FIVE], n_players=3)
        p1 = engine.players[0]
        # Pre-load P1's hand with FIVE and SECOND_CHANCE
        p1.hand = [FIVE, SECOND_CHANCE]

        # P1 hits (draws FIVE dup) → SC absorbs, P2 stays, P3 stays
        events = drive_round(engine, hit_responses=[True, False, False])

        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 0
        assert not p1.has_card(SECOND_CHANCE), "SC should be consumed"
        # P1 should still be active (wasn't busted)
        # Note: is_active is reset to True at end-of-round, so check events instead
        assert not any(
            isinstance(e, PlayerBustedEvent) and e.player is p1 for e in events
        )

    def test_second_chance_discards_both_cards(self):
        """When SC absorbs a bust, both SC and the duplicate go to discard pile."""
        engine = make_engine([FIVE], n_players=3)
        p1 = engine.players[0]
        p1.hand = [FIVE, SECOND_CHANCE]
        initial_discard = len(engine.deck.discard_pile)

        drive_round(engine, hit_responses=[True, False, False])

        # SC + duplicate FIVE should be in discard (plus end-of-round hand discards)
        # The SC and dup are discarded immediately by _pre_hit.
        # Then at end-of-round, remaining hand cards are discarded too.
        # Just verify the SC and dup got there.
        assert SECOND_CHANCE in engine.deck.discard_pile
        assert engine.deck.discard_pile.count(FIVE) >= 1


# ---------------------------------------------------------------------------
# End-of-round scoring
# ---------------------------------------------------------------------------

class TestEndOfRoundScoring:

    def test_scores_accumulate(self):
        """After round, each player's active_score is added to their cumulative score."""
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        # All hit once, then all stay
        events = drive_round(
            engine,
            hit_responses=[True, True, True, False, False, False],
        )
        assert engine.players[0].score == 5   # FIVE
        assert engine.players[1].score == 3   # THREE
        assert engine.players[2].score == 7   # SEVEN

    def test_hands_cleared_after_round(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        drive_round(engine, hit_responses=[True, True, True, False, False, False])
        for p in engine.players:
            assert p.hand == []

    def test_players_reactivated_after_round(self):
        engine = make_engine([FIVE, THREE, SEVEN], n_players=3)
        drive_round(engine, hit_responses=[True, True, True, False, False, False])
        for p in engine.players:
            assert p.is_active is True

    def test_round_number_incremented(self):
        engine = make_engine([], n_players=3)
        drive_round(engine, hit_responses=[False, False, False])
        assert engine.round_number == 1

    def test_round_over_event_yielded(self):
        engine = make_engine([], n_players=3)
        events = drive_round(engine, hit_responses=[False, False, False])
        roe = [e for e in events if isinstance(e, RoundOverEvent)]
        assert len(roe) == 1
        assert roe[0].round_number == 1


# ---------------------------------------------------------------------------
# Win condition
# ---------------------------------------------------------------------------

class TestWinCondition:

    def test_game_over_when_player_reaches_200(self):
        engine = make_engine([TWELVE], n_players=3)
        p1 = engine.players[0]
        p1.score = 195  # needs 5 more to win
        # P1 hits (TWELVE → 12 pts), P2 stays, P3 stays, P1 stays → score = 195 + 12 = 207
        drive_round(engine, hit_responses=[True, False, False, False])
        assert engine.game_over is True
        assert engine.winner is p1

    def test_no_game_over_below_200(self):
        engine = make_engine([FIVE], n_players=3)
        drive_round(engine, hit_responses=[True, False, False])
        assert engine.game_over is False
        assert engine.winner is None

    def test_tiebreak_highest_total_wins(self):
        """If multiple players cross 200 in the same round, highest total wins."""
        engine = make_engine([TWELVE, ELEVEN], n_players=3)
        p1, p2, p3 = engine.players
        p1.score = 195
        p2.score = 195
        # P1 hits (TWELVE → 207), P2 hits (ELEVEN → 206), P3 stays
        # After P3 stays, only P1 and P2 active. Loop continues:
        # P1 stay, P2 stay → round ends.
        drive_round(
            engine,
            hit_responses=[True, True, False, False, False],
        )
        assert engine.game_over is True
        assert engine.winner is p1  # 207 > 206


# ---------------------------------------------------------------------------
# Round exits when < 1 active player
# ---------------------------------------------------------------------------

class TestRoundExitCondition:

    def test_round_ends_when_no_player_left(self):
        """Ensure the round doesn't end till all players have taken their turn"""
        engine = make_engine([FIVE], n_players=3)
        # P1 hits (FIVE), P2 stays, P3 stays, P1 stays → round ends
        events = drive_round(engine, hit_responses=[True, False, False, False])
        assert any(isinstance(e, RoundOverEvent) for e in events)


# ---------------------------------------------------------------------------
# play() auto-drive
# ---------------------------------------------------------------------------

class TestPlay:

    def test_play_terminates_with_always_stay(self):
        """play() with bots that always stay should never end because
        no one ever scores (everyone stays with 0 cards → 0 points forever).

        Instead, use bots that hit once then stay, with high-value cards
        so someone crosses 200.
        """
        # Build a deck with enough TWELVE cards for many rounds
        cards = [TWELVE, ELEVEN, TEN] * 100
        deck = make_deck(cards)
        players = make_players(3)

        # Each player hits once per round, then stays
        call_count = [0]

        def hit_stay(game, player):
            call_count[0] += 1
            # Hit on first turn of each round (player has no cards), stay after
            return len(player.hand) == 0

        def target_selector(game, event, source):
            return game.active_players[0]

        engine = GameEngine(
            deck=deck,
            players=players,
            hit_stay_decider=hit_stay,
            target_selector=target_selector,
        )
        engine.play()
        assert engine.game_over is True
        assert engine.winner is not None
        assert engine.winner.score >= 200


# ---------------------------------------------------------------------------
# Real mode
# ---------------------------------------------------------------------------

class TestRealMode:

    def test_real_mode_yields_card_input_request(self):
        """In real_mode, _draw yields CardInputRequest instead of auto-dealing."""
        engine = make_engine([], n_players=3, real_mode=True)
        gen = engine.round()
        # First: HitStayRequest for P1
        req = next(gen)
        assert isinstance(req, HitStayRequest)
        # Send True (hit)
        req = gen.send(True)
        # Should be CardInputRequest
        assert isinstance(req, CardInputRequest)
        assert req.player is engine.players[0]


# ---------------------------------------------------------------------------
# Reshuffle at round start
# ---------------------------------------------------------------------------

class TestReshuffle:

    def test_virtual_mode_reshuffles_at_round_start(self):
        """In virtual mode, reshuffle() is called at the start of each round."""
        engine = make_engine([], n_players=3)
        engine.deck.reshuffle = MagicMock()
        drive_round(engine, hit_responses=[False, False, False])
        engine.deck.reshuffle.assert_called_once()

    def test_real_mode_does_not_reshuffle(self):
        """In real_mode, reshuffle() is NOT called at round start."""
        engine = make_engine([], n_players=3, real_mode=True)
        engine.deck.reshuffle = MagicMock()
        # All stay immediately (send cards for real mode's CardInputRequest)
        drive_round(engine, hit_responses=[False, False, False])
        engine.deck.reshuffle.assert_not_called()


# ---------------------------------------------------------------------------
# Flip 7
# ---------------------------------------------------------------------------

class TestFlip7:
    """Flip 7: round ends immediately when a player gets 7 unique number cards,
    that player gets +15 bonus points."""

    def test_flip7_triggers_event(self):
        """Achieving 7 unique number cards yields a Flip7Event."""
        # P1 hits 7 times getting 7 unique cards; P2, P3 stay immediately.
        cards = [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        engine = make_engine(cards, n_players=3)
        # P1 hit, P2 stay, P3 stay, then P1 hits 6 more times
        hits = [True, False, False] + [True] * 6
        events = drive_round(engine, hit_responses=hits)
        flip7_events = [e for e in events if isinstance(e, Flip7Event)]
        assert len(flip7_events) == 1
        assert flip7_events[0].player is engine.players[0]

    def test_flip7_awards_15_bonus(self):
        """The Flip 7 player gets active_score + 15 bonus."""
        cards = [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        engine = make_engine(cards, n_players=3)
        hits = [True, False, False] + [True] * 6
        drive_round(engine, hit_responses=hits)
        p1 = engine.players[0]
        # 0+1+2+3+4+5+6 = 21, plus 15 bonus = 36
        assert p1.score == 36

    def test_flip7_ends_round_immediately(self):
        """No more HitStayRequests are yielded after Flip 7 triggers."""
        cards = [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        engine = make_engine(cards, n_players=3)
        hits = [True, False, False] + [True] * 6
        events = drive_round(engine, hit_responses=hits)
        # After Flip7Event, only RoundOverEvent should follow
        flip7_idx = next(i for i, e in enumerate(events) if isinstance(e, Flip7Event))
        after_flip7 = events[flip7_idx + 1:]
        hit_stay_after = [e for e in after_flip7 if isinstance(e, HitStayRequest)]
        assert hit_stay_after == []

    def test_flip7_other_players_score_normally(self):
        """Other players who stayed still get their score (no bonus)."""
        # P1 hits (FIVE), P2 hits (THREE), P3 stays.
        # Next pass: P1 hits (ZERO), P2 stays.
        # Then P1 hits 5 more times to reach 7 unique number cards.
        cards = [FIVE, THREE, ZERO, ONE, TWO, FOUR, SIX, SEVEN]
        engine = make_engine(cards, n_players=3)
        # Pass 1: P1 hit, P2 hit, P3 stay
        # Pass 2: P1 hit, P2 stay
        # Passes 3-7: P1 hit (5 more)
        hits = [True, True, False, True, False] + [True] * 5
        drive_round(engine, hit_responses=hits)
        assert engine.players[1].score == 3   # THREE only
        assert engine.players[2].score == 0   # stayed with no cards

    def test_flip7_non_bustable_cards_dont_count(self):
        """Modifier and action cards don't count toward the 7-card requirement."""
        # P1 gets 6 number cards + PLUS_FOUR (not bustable) = only 6 number cards
        cards = [ZERO, ONE, TWO, THREE, FOUR, FIVE, PLUS_FOUR]
        engine = make_engine(cards, n_players=3)
        hits = [True, False, False] + [True] * 6
        events = drive_round(engine, hit_responses=hits)
        flip7_events = [e for e in events if isinstance(e, Flip7Event)]
        assert flip7_events == []  # no flip 7

    def test_flip7_with_modifier_cards_in_hand(self):
        """Flip 7 triggers based on bustable count even with modifiers present."""
        # P1 gets PLUS_FOUR, then 7 unique number cards
        cards = [PLUS_FOUR, ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        engine = make_engine(cards, n_players=3)
        hits = [True, False, False] + [True] * 7
        events = drive_round(engine, hit_responses=hits)
        flip7_events = [e for e in events if isinstance(e, Flip7Event)]
        assert len(flip7_events) == 1
        p1 = engine.players[0]
        # 0+1+2+3+4+5+6 = 21 number + 4 modifier = 25, plus 15 bonus = 40
        assert p1.score == 40

    def test_has_flip7_false_with_fewer_than_7(self):
        """_has_flip7 returns False when player has fewer than 7 number cards."""
        engine = make_engine([], n_players=3)
        player = engine.players[0]
        player.hand = [ZERO, ONE, TWO, THREE, FOUR, FIVE]
        assert engine._has_flip7(player) is False

    def test_has_flip7_true_with_exactly_7(self):
        """_has_flip7 returns True when player has exactly 7 number cards."""
        engine = make_engine([], n_players=3)
        player = engine.players[0]
        player.hand = [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        assert engine._has_flip7(player) is True
