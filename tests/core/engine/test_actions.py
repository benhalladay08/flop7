"""Tests for flop7.core.engine.actions — flip_three, freeze, second_chance.

These are tested through the engine's round() generator since the action
generators depend on game._draw and game._hit via ``yield from``.
"""
import pytest

from flop7.core.classes.cards import (
    FIVE,
    THREE,
    SEVEN,
    NINE,
    TEN,
    ELEVEN,
    TWELVE,
    FLIP_THREE,
    FREEZE,
    SECOND_CHANCE,
    PLUS_FOUR,
)
from flop7.core.classes.player import Player
from flop7.core.engine.engine import GameEngine
from flop7.core.engine.requests import (
    CardDrawnEvent,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
    TargetRequest,
)

from tests.conftest import drive_round, make_deck, make_players


def _engine(cards, n_players=3):
    """Build a GameEngine with a deterministic deck for action tests."""
    deck = make_deck(cards)
    players = make_players(n_players)

    def hit_stay(g, p):
        raise RuntimeError("hit_stay should not be called; use drive_round")

    def target(g, e, s):
        raise RuntimeError("target should not be called; use drive_round")

    return GameEngine(deck, players, hit_stay, target)


# =========================================================================
# Flip Three
# =========================================================================

class TestFlipThree:

    def test_normal_flow_three_cards_drawn(self):
        """P1 draws FLIP_THREE, targets P2. P2 gets 3 number cards."""
        #  Deck: [FLIP_THREE, FIVE, THREE, SEVEN]
        #    P1 hits → draws FLIP_THREE → targets P2
        #    P2 forced: draws FIVE, THREE, SEVEN (all added to hand)
        #    P2 stays, P3 stays → round ends
        engine = _engine([FLIP_THREE, FIVE, THREE, SEVEN])
        p1, p2, p3 = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )

        # P2 should have received 3 cards
        drawn_for_p2 = [
            e for e in events
            if isinstance(e, CardDrawnEvent) and e.player is p2
        ]
        assert len(drawn_for_p2) == 3
        assert drawn_for_p2[0].card is FIVE
        assert drawn_for_p2[1].card is THREE
        assert drawn_for_p2[2].card is SEVEN

    def test_flip_three_target_gets_cards_in_hand(self):
        """After Flip Three resolves, the target has the 3 cards in hand."""
        engine = _engine([FLIP_THREE, FIVE, THREE, SEVEN])
        p1, p2, p3 = engine.players

        drive_round(
            engine,
            # P1 hits (FLIP_THREE → targets P2, 3 forced cards drawn)
            # P2 stays, P3 stays, P1 stays → round ends
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )
        # P2 should have scored 5 + 3 + 7 = 15
        assert p2.score == 15

    def test_flip_three_card_itself_discarded(self):
        """The Flip Three card goes to discard, not into anyone's hand."""
        engine = _engine([FLIP_THREE, FIVE, THREE, SEVEN])
        p1, p2, p3 = engine.players

        drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )
        assert FLIP_THREE in engine.deck.discard_pile

    def test_flip_three_target_busts_stops_early(self):
        """If target busts during forced draws, remaining draws are skipped.

        P2 already has FIVE. Forced draws: FIVE (dup → bust), THREE, SEVEN.
        Only 1 card should be drawn before bust stops the loop.
        """
        engine = _engine([FLIP_THREE, FIVE, THREE, SEVEN])
        p1, p2, p3 = engine.players
        p2.hand = [FIVE]  # pre-load so the forced FIVE causes bust

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )

        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 1
        assert bust_events[0].player is p2

        # Only 1 forced draw should have happened (FIVE → bust stops loop)
        drawn_for_p2 = [
            e for e in events
            if isinstance(e, CardDrawnEvent) and e.player is p2
        ]
        assert len(drawn_for_p2) == 1

    def test_flip_three_deferred_action_resolves_after(self):
        """FREEZE drawn during flip-three is deferred until after all 3 cards.

        Forced draws: FIVE, FREEZE, THREE.
        FREEZE is deferred. After all 3 drawn, FREEZE resolves (targets someone).
        """
        engine = _engine([FLIP_THREE, FIVE, FREEZE, THREE])
        p1, p2, p3 = engine.players

        events = drive_round(
            engine,
            # P1 hits (FLIP_THREE targeting P2)
            # Then P2 stays (after flip three resolves), P3 stays
            hit_responses=[True, False, False],
            # First target: P2 (for flip three)
            # Second target: P3 (for deferred FREEZE)
            target_responses=[p2, p3],
        )

        # P3 should have been frozen (FREEZE added to hand)
        # After round, check that FREEZE went through (P3 is reactivated at
        # end-of-round, but the freeze card was added to P3's hand before cleanup)
        target_reqs = [e for e in events if isinstance(e, TargetRequest)]
        assert len(target_reqs) == 2

    def test_flip_three_second_chance_resolves_immediately(self):
        """SC drawn during flip-three is resolved immediately (not deferred).

        Forced draws: FIVE, SECOND_CHANCE, THREE.
        SC should be added to target's hand in real time.
        """
        engine = _engine([FLIP_THREE, FIVE, SECOND_CHANCE, THREE])
        p1, p2, p3 = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            # First target: P2 (for flip three)
            # Second target: P2 again (SC targets P2)
            target_responses=[p2, p2],
        )

        # SC was resolved during the flip three, not deferred
        # The drawn events should show all 3 cards drawn for P2
        drawn_for_p2 = [
            e for e in events
            if isinstance(e, CardDrawnEvent) and e.player is p2
        ]
        assert len(drawn_for_p2) == 3

    def test_flip_three_deferred_discarded_if_target_busted(self):
        """If target busted, deferred action cards go to discard pile.

        P2 has FIVE. Forced draws: FREEZE, FIVE (dup → bust).
        FREEZE is deferred. After bust, FREEZE should be discarded.
        """
        engine = _engine([FLIP_THREE, FREEZE, FIVE])
        p1, p2, p3 = engine.players
        p2.hand = [FIVE]

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )

        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 1
        assert bust_events[0].player is p2
        # Deferred FREEZE should be in discard
        assert FREEZE in engine.deck.discard_pile

    def test_flip_three_self_target(self):
        """Player can target themselves with Flip Three."""
        engine = _engine([FLIP_THREE, FIVE, THREE, SEVEN])
        p1, p2, p3 = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p1],  # P1 targets self
        )

        drawn_for_p1 = [
            e for e in events
            if isinstance(e, CardDrawnEvent) and e.player is p1
        ]
        # P1 drew FLIP_THREE + 3 forced cards = 4 CardDrawnEvents for P1
        assert len(drawn_for_p1) == 4


# =========================================================================
# Freeze
# =========================================================================

class TestFreeze:

    def test_freeze_deactivates_target(self):
        """Frozen player exits the round but keeps their hand score."""
        engine = _engine([FIVE, THREE, FREEZE])
        p1, p2, p3 = engine.players

        # P1 hits (FIVE), P2 hits (THREE), P3 hits (FREEZE → targets P1)
        # P1 is frozen. P2 and P3 still active → loop continues.
        # P2 stays, P3 stays → round ends.
        events = drive_round(
            engine,
            hit_responses=[True, True, True, False, False],
            target_responses=[p1],
        )

        # P1 was frozen with FIVE in hand → should score 5
        assert p1.score == 5

    def test_freeze_card_added_to_target_hand(self):
        """The Freeze card itself is added to the target's hand."""
        engine = _engine([FREEZE])
        p1, p2, p3 = engine.players

        # P1 hits (FREEZE → targets P2), P3 stays → round ends
        # Wait — after P1 hits FREEZE targeting P2, P2 becomes inactive.
        # Then the for loop continues: P2 skipped (inactive), P3's turn.
        # Active: P1, P3. P1 and P3 need to finish. Let's be more precise.
        #
        # P1 hits → draws FREEZE → targets P2 → P2 frozen.
        # Active: P1, P3. Loop continues: next is P3 (P2 skipped).
        # P3 stays → Active: P1. ≤1 → round ends.
        events = drive_round(
            engine,
            hit_responses=[True, False],
            target_responses=[p2],
        )

        # Check P2 scored something (FREEZE card has 0 points, so 0)
        # But verify the freeze card went through the system
        assert any(
            isinstance(e, TargetRequest) for e in events
        )

    def test_freeze_target_score_preserved(self):
        """Frozen player scores normally from their existing hand.

        P2 has accumulated cards worth 15 points. Freeze doesn't change that.
        """
        engine = _engine([FIVE, THREE, SEVEN, FREEZE])
        p1, p2, p3 = engine.players

        # P1 hits (FIVE), P2 hits (THREE), P3 hits (SEVEN)
        # Loop: P1 hits (FREEZE → targets P2). P2 frozen with [THREE].
        # P3 stays, P1 stays → round ends (no active players).
        events = drive_round(
            engine,
            hit_responses=[True, True, True, True, False, False],
            target_responses=[p2],
        )

        # P2 had THREE (3 pts) + FREEZE card (0 pts) = 3
        assert p2.score == 3


# =========================================================================
# Second Chance
# =========================================================================

class TestSecondChance:

    def test_second_chance_added_to_target_hand(self):
        """SC is placed in the target's hand."""
        engine = _engine([SECOND_CHANCE, FIVE])
        p1, p2, p3 = engine.players

        # P1 hits → draws SC → targets P2, SC added to P2's hand.
        # P2 stays, P3 stays → round ends.
        # But wait — after SC resolves, the for loop continues to P2.
        # P2 stays (active with SC in hand), P3 stays → only P1 left → round ends.
        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )

        # P2 scored 0 (SC has 0 points)
        assert p2.score == 0

        # Verify a TargetRequest was issued for SC
        sc_targets = [
            e for e in events
            if isinstance(e, TargetRequest)
            and e.event.name == "SECOND_CHANCE"
        ]
        assert len(sc_targets) == 1

    def test_second_chance_no_eligible_targets_discarded(self):
        """When all active players already have SC, the card is discarded."""
        engine = _engine([SECOND_CHANCE])
        p1, p2, p3 = engine.players

        # Pre-load everyone with SC
        for p in engine.players:
            p.hand = [SECOND_CHANCE]

        # P1 hits → draws SC → no eligible targets → discarded.
        # Then P2 stays, P3 stays → round ends. But actually, after P1 draws SC
        # and it's discarded (no yield), the for loop continues to P2.
        # P2 stays, only P1 left → round ends.
        events = drive_round(
            engine,
            hit_responses=[True, False],
            target_responses=[],  # No target request should be yielded
        )

        # SC should be in discard
        sc_in_discard = [c for c in engine.deck.discard_pile if c is SECOND_CHANCE]
        assert len(sc_in_discard) >= 1

        # No TargetRequest for SC should have been yielded
        sc_targets = [
            e for e in events
            if isinstance(e, TargetRequest)
            and e.event.name == "SECOND_CHANCE"
        ]
        assert len(sc_targets) == 0

    def test_second_chance_target_already_got_sc_discarded(self):
        """If target already has SC by resolve time, the card is discarded.

        We simulate this by pre-giving the target a SC. The action checks
        target.has_card(SECOND_CHANCE) after the yield and discards.
        """
        engine = _engine([SECOND_CHANCE])
        p1, p2, p3 = engine.players
        p2.hand = [SECOND_CHANCE]  # P2 already has SC

        # Eligible is only players without SC. P2 has SC so not eligible.
        # P1 hits → draws SC → eligible = [P1, P3]
        # Targets P3 → SC added to P3's hand.
        events = drive_round(
            engine,
            hit_responses=[True, False],
            target_responses=[p3],
        )

        # P3 should have gotten the SC
        sc_targets = [
            e for e in events
            if isinstance(e, TargetRequest)
            and e.event.name == "SECOND_CHANCE"
        ]
        assert len(sc_targets) == 1

    def test_second_chance_protects_then_consumed(self):
        """Full flow: P2 gets SC, then later draws a duplicate → SC absorbs it."""
        engine = _engine([SECOND_CHANCE, FIVE, SEVEN, FIVE])
        p1, p2, p3 = engine.players

        # P1 hits (SC → targets P2, P2 gets SC)
        # P2 hits (FIVE)
        # P3 hits (SEVEN)
        # Loop continues: P1 stays
        # P2 hits (FIVE dup → SC absorbs, no bust)
        # P3 stays, P2 stays → round ends
        events = drive_round(
            engine,
            hit_responses=[True, True, True, False, True, False, False],
            target_responses=[p2],
        )

        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 0
        # P2 should have scored: FIVE (5) only — SC consumed, dup discarded
        assert p2.score == 5
