"""Tests for flop7.core.engine.engine — round lifecycle, scoring, and win conditions."""

from unittest.mock import MagicMock

import pytest

from flop7.core.classes.cards import (
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
    SECOND_CHANCE,
    FLIP_THREE,
    FREEZE,
)
from flop7.core.engine.engine import GameEngine
from flop7.core.engine.requests import (
    CardDrawRequest,
    CardDrawnEvent,
    Flip7Event,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
)

from tests.conftest import OPENING_CARDS, drive_round, make_deck, make_engine, make_players, opening_cards


class TestConstructor:

    def test_fewer_than_3_players_raises(self):
        deck = make_deck([])
        with pytest.raises(ValueError, match="at least 3"):
            GameEngine(
                deck,
                make_players(2),
                lambda g, p: g.deck.deal(),
                lambda g, p: True,
                lambda g, e, s, el: s,
            )

    def test_exactly_3_players_ok(self):
        deck = make_deck([FIVE])
        engine = GameEngine(
            deck,
            make_players(3),
            lambda g, p: g.deck.deal(),
            lambda g, p: True,
            lambda g, e, s, el: s,
        )
        assert len(engine.players) == 3

    def test_initial_state(self):
        deck = make_deck([])
        engine = GameEngine(
            deck,
            make_players(3),
            lambda g, p: g.deck.deal(),
            lambda g, p: True,
            lambda g, e, s, el: s,
        )
        assert engine.round_number == 0
        assert engine.game_over is False
        assert engine.winner is None
        assert engine.dealer_index == 0
        assert engine.dealer is engine.players[0]

    def test_invalid_dealer_index_raises(self):
        with pytest.raises(ValueError, match="dealer_index"):
            make_engine([], n_players=3, dealer_index=3)

    def test_custom_dealer_changes_turn_order(self):
        engine = make_engine(opening_cards(0, 1, 2), n_players=3, dealer_index=2)
        gen = engine.round()

        req = next(gen)

        assert isinstance(req, CardDrawRequest)
        assert req.player is engine.players[0]


class TestActivePlayers:

    def test_all_active_initially(self):
        engine = make_engine([], n_players=3)
        assert len(engine.active_players) == 3

    def test_excludes_inactive(self):
        engine = make_engine([], n_players=3)
        engine.players[0].is_active = False
        assert len(engine.active_players) == 2
        assert engine.players[0] not in engine.active_players


class TestRoundBasicFlow:

    def test_round_starts_with_opening_draw_requests(self):
        """Each opening card is requested before being processed."""
        engine = make_engine(opening_cards(0, 1, 2), n_players=3)
        gen = engine.round()

        req = next(gen)
        assert isinstance(req, CardDrawRequest)
        assert req.player is engine.players[1]

        req = gen.send(engine.deck.deal())
        assert isinstance(req, CardDrawnEvent)
        assert req.player is engine.players[1]

        req = gen.send(None)
        assert isinstance(req, CardDrawRequest)
        assert req.player is engine.players[2]

        req = gen.send(engine.deck.deal())
        assert isinstance(req, CardDrawnEvent)
        assert req.player is engine.players[2]

        req = gen.send(None)
        assert isinstance(req, CardDrawRequest)
        assert req.player is engine.players[0]

        req = gen.send(engine.deck.deal())
        assert isinstance(req, CardDrawnEvent)
        assert req.player is engine.players[0]

        req = gen.send(None)
        assert isinstance(req, HitStayRequest)
        assert req.player is engine.players[1]

    def test_stay_makes_player_inactive(self):
        engine = make_engine(opening_cards(0, 1, 2), n_players=3)
        events = drive_round(engine, hit_responses=[False, False, False])
        hit_stay_events = [e for e in events if isinstance(e, HitStayRequest)]
        assert len(hit_stay_events) == 3
        assert any(isinstance(e, RoundOverEvent) for e in events)

    def test_hit_yields_card_drawn_event(self):
        engine = make_engine(opening_cards(0, 1, 2) + [FIVE], n_players=3)
        events = drive_round(engine, hit_responses=[True, False, False, False])
        drawn_events = [e for e in events if isinstance(e, CardDrawnEvent)]
        assert len(drawn_events) == 4
        assert drawn_events[-1].card is FIVE
        assert drawn_events[-1].player is engine.players[1]

    def test_opening_deal_still_ends_after_one_card_per_player(self):
        """An opening action card does not grant a replacement opening card."""
        cards = [FLIP_THREE, FIVE, THREE, SEVEN, NINE, TEN, ELEVEN]
        engine = make_engine(cards, n_players=3)
        p1, p2, p3 = engine.players

        events = drive_round(
            engine,
            hit_responses=[False, False, False],
            target_responses=[p2],
        )

        drawn_events = [
            (event.player, event.card)
            for event in events
            if isinstance(event, CardDrawnEvent)
        ]
        assert drawn_events == [
            (p2, FLIP_THREE),
            (p2, FIVE),
            (p2, THREE),
            (p2, SEVEN),
            (p3, NINE),
            (p1, TEN),
        ]


class TestOpeningDealFreeze:

    def test_frozen_player_skipped_during_opening_deal(self):
        """A player frozen by a Freeze drawn during the opening deal
        should NOT receive their own opening card."""
        # P2 draws Freeze targeting P3 → P3 frozen before their turn.
        # P1 gets dealt normally. P3 never draws.
        # After opening: P2 has empty hand (force-draw), P1 has FIVE.
        cards = [FREEZE, FIVE, THREE]
        engine = make_engine(cards, n_players=3)
        p1, p2, p3 = engine.players

        events = drive_round(
            engine,
            hit_responses=[False, False],
            target_responses=[p3],
        )

        drawn_events = [
            (e.player, e.card) for e in events if isinstance(e, CardDrawnEvent)
        ]
        # Opening: P2→FREEZE, P1→FIVE. Main loop: P2 force-draws THREE.
        assert drawn_events == [(p2, FREEZE), (p1, FIVE), (p2, THREE)]
        assert not any(e.player is p3 for e in events if isinstance(e, CardDrawnEvent))

    def test_frozen_player_still_scores_existing_hand(self):
        """A player frozen during the opening deal keeps their hand score."""
        # P2 gets opening card, P3 draws Freeze targeting P2.
        # P2 is frozen with opening card. P1 gets dealt.
        # Main loop: P3 force-draws THREE, then stays. P1 stays.
        cards = [OPENING_CARDS[0], FREEZE, OPENING_CARDS[2], THREE]
        engine = make_engine(cards, n_players=3)
        p1, p2, p3 = engine.players

        drive_round(
            engine,
            hit_responses=[False, False],
            target_responses=[p2],
        )
        assert p2.score == 0


class TestBust:

    def test_duplicate_number_causes_bust(self):
        engine = make_engine([FIVE] + opening_cards(1, 2) + [FIVE], n_players=3)
        p2 = engine.players[1]

        events = drive_round(engine, hit_responses=[True, False, False])
        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 1
        assert bust_events[0].player is p2

    def test_bust_preserves_cumulative_score(self):
        engine = make_engine([FIVE] + opening_cards(1, 2) + [FIVE], n_players=3)
        p2 = engine.players[1]
        p2.score = 50

        drive_round(engine, hit_responses=[True, False, False])
        assert p2.score == 50

    def test_non_bustable_card_no_bust(self):
        engine = make_engine([PLUS_FOUR] + opening_cards(1, 2) + [PLUS_FOUR], n_players=3)
        events = drive_round(engine, hit_responses=[True, False, False, False])
        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 0


class TestSecondChanceAbsorption:

    def test_second_chance_absorbs_duplicate(self):
        engine = make_engine(opening_cards(0, 1, 2) + [FIVE], n_players=3)
        p2 = engine.players[1]
        p2.hand = [FIVE, SECOND_CHANCE]

        events = drive_round(engine, hit_responses=[True, False, False, False])

        assert p2.score == 5
        assert not p2.has_card(SECOND_CHANCE)
        assert not any(
            isinstance(e, PlayerBustedEvent) and e.player is p2 for e in events
        )

    def test_second_chance_discards_both_cards(self):
        engine = make_engine(opening_cards(0, 1, 2) + [FIVE], n_players=3)
        p2 = engine.players[1]
        p2.hand = [FIVE, SECOND_CHANCE]

        drive_round(engine, hit_responses=[True, False, False, False])

        assert SECOND_CHANCE in engine.deck.discard_pile
        assert engine.deck.discard_pile.count(FIVE) >= 1


class TestEndOfRoundScoring:

    def test_scores_accumulate(self):
        engine = make_engine(opening_cards(0, 1, 2) + [FIVE, THREE, SEVEN], n_players=3)
        drive_round(engine, hit_responses=[True, True, True, False, False, False])
        assert engine.players[0].score == 7
        assert engine.players[1].score == 5
        assert engine.players[2].score == 3

    def test_hands_cleared_after_round(self):
        engine = make_engine(opening_cards(0, 1, 2) + [FIVE, THREE, SEVEN], n_players=3)
        drive_round(engine, hit_responses=[True, True, True, False, False, False])
        for player in engine.players:
            assert player.hand == []

    def test_players_reactivated_after_round(self):
        engine = make_engine(opening_cards(0, 1, 2) + [FIVE, THREE, SEVEN], n_players=3)
        drive_round(engine, hit_responses=[True, True, True, False, False, False])
        for player in engine.players:
            assert player.is_active is True

    def test_round_number_incremented(self):
        engine = make_engine(opening_cards(0, 1, 2), n_players=3)
        drive_round(engine, hit_responses=[False, False, False])
        assert engine.round_number == 1

    def test_dealer_rotates_after_round(self):
        engine = make_engine(opening_cards(0, 1, 2), n_players=3)

        drive_round(engine, hit_responses=[False, False, False])

        assert engine.dealer_index == 1
        assert engine.dealer is engine.players[1]

    def test_round_over_event_yielded(self):
        engine = make_engine(opening_cards(0, 1, 2), n_players=3)
        events = drive_round(engine, hit_responses=[False, False, False])
        roe = [e for e in events if isinstance(e, RoundOverEvent)]
        assert len(roe) == 1
        assert roe[0].round_number == 1


class TestWinCondition:

    def test_game_over_when_player_reaches_200(self):
        engine = make_engine(opening_cards(0, 1, 2) + [TWELVE], n_players=3)
        p2 = engine.players[1]
        p2.score = 195

        drive_round(engine, hit_responses=[True, False, False, False])
        assert engine.game_over is True
        assert engine.winner is p2

    def test_no_game_over_below_200(self):
        engine = make_engine(opening_cards(0, 1, 2) + [FIVE], n_players=3)
        drive_round(engine, hit_responses=[True, False, False, False])
        assert engine.game_over is False
        assert engine.winner is None

    def test_tiebreak_highest_total_wins(self):
        engine = make_engine(opening_cards(0, 1, 2) + [TWELVE, ELEVEN], n_players=3)
        p1, p2, _ = engine.players
        p1.score = 195
        p2.score = 195

        drive_round(engine, hit_responses=[True, True, False, False, False])
        assert engine.game_over is True
        assert engine.winner is p2


class TestRoundExitCondition:

    def test_round_ends_when_no_player_left(self):
        engine = make_engine(opening_cards(0, 1, 2) + [FIVE], n_players=3)
        events = drive_round(engine, hit_responses=[True, False, False, False])
        assert any(isinstance(e, RoundOverEvent) for e in events)


class TestPlay:

    def test_play_terminates_when_players_hit_once_after_the_opener(self):
        cards = [TWELVE, TEN, EIGHT, ELEVEN, NINE, SEVEN] * 100
        deck = make_deck(cards)
        players = make_players(3)

        def hit_stay(game, player):
            return len(player.hand) == 1

        def target_selector(game, event, source, eligible):
            return game.active_players[0]

        engine = GameEngine(
            deck=deck,
            players=players,
            card_provider=lambda game, player: game.deck.deal(),
            hit_stay_decider=hit_stay,
            target_selector=target_selector,
        )

        engine.play()
        assert engine.game_over is True
        assert engine.winner is not None
        assert engine.winner.score >= 200


class TestRealMode:

    def test_virtual_mode_yields_card_draw_request_for_opening_deal(self):
        engine = make_engine(opening_cards(0, 1, 2), n_players=3)
        gen = engine.round()
        req = next(gen)
        assert isinstance(req, CardDrawRequest)
        assert req.player is engine.players[1]

    def test_real_mode_yields_card_draw_request_for_opening_deal(self):
        engine = make_engine([], n_players=3, real_mode=True)
        gen = engine.round()
        req = next(gen)
        assert isinstance(req, CardDrawRequest)
        assert req.player is engine.players[1]

    def test_real_mode_play_uses_card_provider(self):
        cards = iter([FIVE, THREE, SEVEN])
        provided = []

        def provider(game, player):
            card = next(cards)
            provided.append((player, card))
            return card

        engine = make_engine(
            [],
            n_players=3,
            hit_responses=[False, False, False],
            card_provider=provider,
            real_mode=True,
        )
        for player in engine.players:
            player.score = 199

        engine.play()

        assert engine.game_over is True
        assert provided == [
            (engine.players[1], FIVE),
            (engine.players[2], THREE),
            (engine.players[0], SEVEN),
        ]


class TestReshuffle:

    def test_virtual_mode_does_not_reshuffle_at_round_start(self):
        engine = make_engine(opening_cards(0, 1, 2) + [FIVE], n_players=3)
        engine.deck.reshuffle = MagicMock()

        drive_round(engine, hit_responses=[False, False, False])
        engine.deck.reshuffle.assert_not_called()

    def test_virtual_mode_reshuffles_after_last_card_is_drawn(self):
        engine = make_engine(opening_cards(0, 1, 2), n_players=3)
        engine.deck.discard([FIVE])

        drive_round(engine, hit_responses=[False, False, False])

        assert engine.deck.draw_pile == [FIVE]

    def test_real_mode_does_not_reshuffle(self):
        engine = make_engine([], n_players=3, real_mode=True)
        engine.deck.reshuffle = MagicMock()

        drive_round(
            engine,
            hit_responses=[False, False, False],
            card_inputs=opening_cards(0, 1, 2),
        )
        engine.deck.reshuffle.assert_not_called()


class TestFlip7:

    def test_flip7_triggers_event(self):
        cards = opening_cards(0, 1, 2) + [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        engine = make_engine(cards, n_players=3)
        hits = [True, False, False] + [True] * 6

        events = drive_round(engine, hit_responses=hits)
        flip7_events = [e for e in events if isinstance(e, Flip7Event)]
        assert len(flip7_events) == 1
        assert flip7_events[0].player is engine.players[1]

    def test_flip7_awards_15_bonus(self):
        cards = opening_cards(0, 1, 2) + [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        engine = make_engine(cards, n_players=3)
        hits = [True, False, False] + [True] * 6

        drive_round(engine, hit_responses=hits)
        assert engine.players[1].score == 36

    def test_flip7_ends_round_immediately(self):
        cards = opening_cards(0, 1, 2) + [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        engine = make_engine(cards, n_players=3)
        hits = [True, False, False] + [True] * 6

        events = drive_round(engine, hit_responses=hits)
        flip7_idx = next(i for i, event in enumerate(events) if isinstance(event, Flip7Event))
        after_flip7 = events[flip7_idx + 1:]
        hit_stay_after = [event for event in after_flip7 if isinstance(event, HitStayRequest)]
        assert hit_stay_after == []

    def test_flip7_other_players_score_normally(self):
        cards = opening_cards(0, 1, 2) + [FIVE, THREE, ZERO, ONE, TWO, FOUR, SIX, SEVEN]
        engine = make_engine(cards, n_players=3)
        hits = [True, True, False, True, False] + [True] * 5

        drive_round(engine, hit_responses=hits)
        assert engine.players[1].score == 40
        assert engine.players[2].score == 3
        assert engine.players[0].score == 0

    def test_flip7_non_bustable_cards_dont_count(self):
        cards = opening_cards(0, 1, 2) + [ZERO, ONE, TWO, THREE, FOUR, FIVE, PLUS_FOUR]
        engine = make_engine(cards, n_players=3)
        hits = [True, False, False] + [True] * 6 + [False]

        events = drive_round(engine, hit_responses=hits)
        flip7_events = [e for e in events if isinstance(e, Flip7Event)]
        assert flip7_events == []

    def test_flip7_with_modifier_cards_in_hand(self):
        cards = opening_cards(0, 1, 2) + [PLUS_FOUR, ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        engine = make_engine(cards, n_players=3)
        hits = [True, False, False] + [True] * 7

        events = drive_round(engine, hit_responses=hits)
        flip7_events = [e for e in events if isinstance(e, Flip7Event)]
        assert len(flip7_events) == 1
        assert engine.players[1].score == 40

    def test_has_flip7_false_with_fewer_than_7(self):
        engine = make_engine([], n_players=3)
        player = engine.players[0]
        player.hand = [ZERO, ONE, TWO, THREE, FOUR, FIVE]
        assert engine._has_flip7(player) is False

    def test_has_flip7_true_with_exactly_7(self):
        engine = make_engine([], n_players=3)
        player = engine.players[0]
        player.hand = [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX]
        assert engine._has_flip7(player) is True


class TestPlayListeners:

    @staticmethod
    def _always_stay_engine():
        """Engine with a full deck where all players always stay."""
        from flop7.core.classes.deck import Deck
        players = make_players(3)
        return GameEngine(
            Deck(), players,
            card_provider=lambda game, player: game.deck.deal(),
            hit_stay_decider=lambda game, player: False,
            target_selector=lambda game, event, player, eligible: eligible[0],
        )

    def test_listeners_receive_all_yielded_events(self):
        engine = self._always_stay_engine()
        log = []
        engine.play(listeners=[log.append])
        assert len(log) > 0
        assert any(isinstance(e, CardDrawRequest) for e in log)
        assert any(isinstance(e, CardDrawnEvent) for e in log)
        assert any(isinstance(e, RoundOverEvent) for e in log)

    def test_listeners_called_before_engine_responds(self):
        """Each listener fires before the engine sends its response."""
        engine = self._always_stay_engine()
        order = []
        engine.play(listeners=[lambda e: order.append(type(e).__name__)])
        # The draw request is observed before the virtual driver provides a card.
        assert order[0] == "CardDrawRequest"
        assert order[1] == "CardDrawnEvent"

    def test_multiple_listeners_all_called(self):
        engine = self._always_stay_engine()
        log_a, log_b = [], []
        engine.play(listeners=[log_a.append, log_b.append])
        assert len(log_a) == len(log_b)
        assert len(log_a) > 0

    def test_no_listeners_is_default(self):
        engine = self._always_stay_engine()
        engine.play()
        assert engine.game_over
