"""Tests for flop7.core.engine.actions via the engine's round() generator."""

import pytest

from flop7.core.classes.cards import (
    ALL_CARDS,
    FIVE,
    THREE,
    SEVEN,
    FLIP_THREE,
    FREEZE,
    SECOND_CHANCE,
)
from flop7.core.engine.actions import get_action, flip_three, freeze, second_chance
from flop7.core.engine.engine import GameEngine
from flop7.core.engine.requests import (
    CardDrawnEvent,
    HitStayRequest,
    PlayerBustedEvent,
    TargetRequest,
)

from tests.conftest import drive_round, make_deck, make_players, opening_cards

ACTION_HANDLERS = [
    (FLIP_THREE, flip_three),
    (FREEZE, freeze),
    (SECOND_CHANCE, second_chance),
]
ACTION_ABBRVS = {card.abbrv for card, _ in ACTION_HANDLERS}
NON_ACTION_CARDS = [card for card in ALL_CARDS if card.abbrv not in ACTION_ABBRVS]


def _engine(cards, n_players=3):
    """Build a GameEngine with a deterministic deck for action tests."""
    deck = make_deck(cards)
    players = make_players(n_players)

    def hit_stay(g, p):
        raise RuntimeError("hit_stay should not be called; use drive_round")

    def target(g, e, s, eligible):
        raise RuntimeError("target should not be called; use drive_round")

    return GameEngine(deck, players, hit_stay, target)


class TestActionRegistry:

    @pytest.mark.parametrize("card,handler", ACTION_HANDLERS)
    def test_action_cards_resolve_to_handlers(self, card, handler):
        assert get_action(card) is handler

    @pytest.mark.parametrize("card", NON_ACTION_CARDS)
    def test_non_action_cards_resolve_to_none(self, card):
        assert get_action(card) is None


class TestFlipThree:

    def test_normal_flow_three_cards_drawn(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, THREE, SEVEN])
        _, p2, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )

        drawn_for_p2 = [
            event.card for event in events
            if isinstance(event, CardDrawnEvent) and event.player is p2
        ]
        assert drawn_for_p2[-3:] == [FIVE, THREE, SEVEN]

    def test_flip_three_target_gets_cards_in_hand(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, THREE, SEVEN])
        _, p2, _ = engine.players

        drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )
        assert p2.score == 15

    def test_flip_three_card_itself_discarded(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, THREE, SEVEN])
        _, p2, _ = engine.players

        drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )
        assert FLIP_THREE in engine.deck.discard_pile

    def test_flip_three_target_busts_stops_early(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, THREE, SEVEN])
        _, p2, _ = engine.players
        p2.hand = [FIVE]

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )

        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 1
        assert bust_events[0].player is p2

        forced_drawn_for_p2 = [
            event.card for event in events
            if isinstance(event, CardDrawnEvent) and event.player is p2
            and event.card in (FIVE, THREE, SEVEN)
        ]
        assert forced_drawn_for_p2 == [FIVE]

    def test_flip_three_deferred_action_resolves_after(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, FREEZE, THREE])
        _, p2, p3 = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2, p3],
        )

        target_reqs = [e for e in events if isinstance(e, TargetRequest)]
        assert len(target_reqs) == 2

    def test_flip_three_second_chance_resolves_immediately(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, SECOND_CHANCE, THREE])
        _, p2, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )

        drawn_for_p2 = [
            event.card for event in events
            if isinstance(event, CardDrawnEvent) and event.player is p2
        ]
        assert drawn_for_p2[-3:] == [FIVE, SECOND_CHANCE, THREE]
        sc_targets = [
            event for event in events
            if isinstance(event, TargetRequest) and event.event.name == "SECOND_CHANCE"
        ]
        assert sc_targets == []

    def test_flip_three_duplicate_second_chance_is_regifted_by_target(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, SECOND_CHANCE, THREE])
        p1, p2, p3 = engine.players
        p2.hand = [SECOND_CHANCE]

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2, p3],
        )

        sc_targets = [
            event for event in events
            if isinstance(event, TargetRequest) and event.event.name == "SECOND_CHANCE"
        ]
        assert len(sc_targets) == 1
        assert sc_targets[0].source is p2
        assert set(sc_targets[0].eligible) == {p1, p3}
        assert SECOND_CHANCE in engine.deck.discard_pile

    def test_flip_three_deferred_discarded_if_target_busted(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FREEZE, FIVE])
        _, p2, _ = engine.players
        p2.hand = [FIVE]

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )

        bust_events = [e for e in events if isinstance(e, PlayerBustedEvent)]
        assert len(bust_events) == 1
        assert bust_events[0].player is p2
        assert FREEZE in engine.deck.discard_pile

    def test_flip_three_self_target(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, THREE, SEVEN])
        p1, _, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p1],
        )

        drawn_for_p1 = [
            event.card for event in events
            if isinstance(event, CardDrawnEvent) and event.player is p1
        ]
        assert drawn_for_p1[1:] == [FLIP_THREE, FIVE, THREE, SEVEN]


class TestFreeze:

    def test_freeze_deactivates_target(self):
        engine = _engine(opening_cards(0, 1, 2) + [FIVE, THREE, FREEZE])
        p1, _, _ = engine.players

        drive_round(
            engine,
            hit_responses=[True, True, True, False, False],
            target_responses=[p1],
        )
        assert p1.score == 5

    def test_freeze_card_added_to_target_hand(self):
        engine = _engine(opening_cards(0, 1, 2) + [FREEZE])
        _, p2, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )

        assert any(isinstance(event, TargetRequest) for event in events)

    def test_freeze_target_score_preserved(self):
        engine = _engine(opening_cards(0, 1, 2) + [FIVE, THREE, SEVEN, FREEZE])
        _, p2, _ = engine.players

        drive_round(
            engine,
            hit_responses=[True, True, True, True, False, False],
            target_responses=[p2],
        )
        assert p2.score == 3


class TestSecondChance:

    def test_second_chance_added_to_drawing_player_without_target(self):
        engine = _engine(opening_cards(0, 1, 2) + [SECOND_CHANCE, FIVE])
        p1, _, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
        )

        assert p1.score == 0
        sc_targets = [
            event for event in events
            if isinstance(event, TargetRequest) and event.event.name == "SECOND_CHANCE"
        ]
        assert sc_targets == []

    def test_duplicate_second_chance_added_to_selected_eligible_player(self):
        engine = _engine(opening_cards(0, 1, 2) + [SECOND_CHANCE])
        p1, p2, p3 = engine.players
        p1.hand = [SECOND_CHANCE]

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p3],
        )

        sc_targets = [
            event for event in events
            if isinstance(event, TargetRequest) and event.event.name == "SECOND_CHANCE"
        ]
        assert len(sc_targets) == 1
        assert sc_targets[0].source is p1
        assert set(sc_targets[0].eligible) == {p2, p3}
        assert SECOND_CHANCE in engine.deck.discard_pile

    def test_second_chance_no_eligible_targets_discarded(self):
        engine = _engine(opening_cards(0, 1, 2) + [SECOND_CHANCE])

        for player in engine.players:
            player.hand = [SECOND_CHANCE]

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[],
        )

        sc_in_discard = [card for card in engine.deck.discard_pile if card is SECOND_CHANCE]
        assert len(sc_in_discard) >= 1

        sc_targets = [
            event for event in events
            if isinstance(event, TargetRequest) and event.event.name == "SECOND_CHANCE"
        ]
        assert len(sc_targets) == 0

    def test_second_chance_invalid_selected_target_discarded(self):
        engine = _engine(opening_cards(0, 1, 2) + [SECOND_CHANCE])
        p1, p2, _ = engine.players
        p1.hand = [SECOND_CHANCE]

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p1],
        )

        sc_targets = [
            event for event in events
            if isinstance(event, TargetRequest) and event.event.name == "SECOND_CHANCE"
        ]
        assert len(sc_targets) == 1
        assert p2.score == 0
        assert engine.deck.discard_pile.count(SECOND_CHANCE) >= 1

    def test_second_chance_target_revalidated_after_request(self):
        engine = _engine(opening_cards(0, 1, 2) + [SECOND_CHANCE])
        p1, p2, _ = engine.players
        p1.hand = [SECOND_CHANCE]

        gen = engine.round()
        req = next(gen)
        req = gen.send(None)
        req = gen.send(None)
        req = gen.send(None)
        assert isinstance(req, HitStayRequest)
        assert req.player is p1

        req = gen.send(True)
        assert isinstance(req, CardDrawnEvent)
        assert req.card is SECOND_CHANCE

        req = gen.send(None)
        assert isinstance(req, TargetRequest)
        assert p2 in req.eligible

        p2.hand.append(SECOND_CHANCE)
        gen.send(p2)

        assert engine.deck.discard_pile.count(SECOND_CHANCE) == 1

    def test_second_chance_protects_then_consumed(self):
        engine = _engine([FIVE] + opening_cards(1, 2) + [SECOND_CHANCE, FIVE])
        p1, _, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False, True, False],
        )

        bust_events = [event for event in events if isinstance(event, PlayerBustedEvent)]
        assert len(bust_events) == 0
        assert p1.score == 5
