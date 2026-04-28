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
    CardDrawRequest,
    CardDrawnEvent,
    FlipThreeResolvedEvent,
    FlipThreeStartEvent,
    FreezeEvent,
    HitStayRequest,
    PlayerBustedEvent,
    SecondChanceEvent,
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
    """Build a GameEngine with P1 first in turn order for action tests."""
    deck = make_deck(cards)
    players = make_players(n_players)

    def hit_stay(g, p):
        raise RuntimeError("hit_stay should not be called; use drive_round")

    def target(g, e, s, eligible):
        raise RuntimeError("target should not be called; use drive_round")

    def card_provider(game, player):
        return game.deck.deal()

    return GameEngine(
        deck,
        players,
        card_provider,
        hit_stay,
        target,
        dealer_index=n_players - 1,
    )


def _advance_to_target_request(engine):
    """Drive a round to its first action target request."""
    gen = engine.round()
    req = next(gen)
    while not isinstance(req, TargetRequest):
        if isinstance(req, CardDrawRequest):
            req = gen.send(engine.deck.deal())
        elif isinstance(req, HitStayRequest):
            req = gen.send(True)
        else:
            req = gen.send(None)
    return gen, req


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

    def test_flip_three_invalid_target_raises_without_forced_draws(self):
        cards = opening_cards(0, 1, 2)
        engine = _engine(cards + [FLIP_THREE, FIVE, THREE, SEVEN])
        outsider = make_players(1)[0]
        gen, req = _advance_to_target_request(engine)

        assert outsider not in req.eligible
        with pytest.raises(ValueError, match="FLIP_THREE target"):
            gen.send(outsider)

        assert outsider.hand == []
        assert engine.deck.draw_pile == [FIVE, THREE, SEVEN]
        assert FLIP_THREE not in engine.deck.discard_pile

    def test_flip_three_target_revalidated_after_request(self):
        cards = opening_cards(0, 1, 2)
        engine = _engine(cards + [FLIP_THREE, FIVE, THREE, SEVEN])
        _, p2, _ = engine.players
        gen, req = _advance_to_target_request(engine)

        assert p2 in req.eligible
        p2.is_active = False
        with pytest.raises(ValueError, match="no longer active"):
            gen.send(p2)

        assert p2.hand == [cards[1]]
        assert engine.deck.draw_pile == [FIVE, THREE, SEVEN]
        assert FLIP_THREE not in engine.deck.discard_pile


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

    def test_freeze_yields_freeze_event_with_correct_players(self):
        engine = _engine(opening_cards(0, 1, 2) + [FREEZE])
        p1, p2, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )

        freeze_events = [e for e in events if isinstance(e, FreezeEvent)]
        assert len(freeze_events) == 1
        assert freeze_events[0].source is p1
        assert freeze_events[0].target is p2

    def test_freeze_event_emitted_after_target_deactivated(self):
        engine = _engine(opening_cards(0, 1, 2) + [FREEZE])
        _, p2, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )

        # FreezeEvent must come after the TargetRequest that selected p2
        target_idx = next(i for i, e in enumerate(events) if isinstance(e, TargetRequest))
        freeze_idx = next(i for i, e in enumerate(events) if isinstance(e, FreezeEvent))
        assert freeze_idx > target_idx

    def test_freeze_invalid_target_raises_without_mutating_target(self):
        cards = opening_cards(0, 1, 2)
        engine = _engine(cards + [FREEZE])
        outsider = make_players(1)[0]
        gen, req = _advance_to_target_request(engine)

        assert outsider not in req.eligible
        with pytest.raises(ValueError, match="FREEZE target"):
            gen.send(outsider)

        assert outsider.hand == []
        assert outsider.is_active is True
        assert FREEZE not in engine.deck.discard_pile

    def test_freeze_target_revalidated_after_request(self):
        cards = opening_cards(0, 1, 2)
        engine = _engine(cards + [FREEZE])
        _, p2, _ = engine.players
        gen, req = _advance_to_target_request(engine)

        assert p2 in req.eligible
        p2.is_active = False
        with pytest.raises(ValueError, match="no longer active"):
            gen.send(p2)

        assert p2.hand == [cards[1]]
        assert FREEZE not in p2.hand
        assert FREEZE not in engine.deck.discard_pile


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

    def test_second_chance_self_assign_yields_event(self):
        engine = _engine(opening_cards(0, 1, 2) + [SECOND_CHANCE])
        p1, _, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
        )

        sc_events = [e for e in events if isinstance(e, SecondChanceEvent)]
        assert len(sc_events) == 1
        assert sc_events[0].source is p1
        assert sc_events[0].target is p1

    def test_second_chance_pass_yields_event_with_correct_target(self):
        engine = _engine(opening_cards(0, 1, 2) + [SECOND_CHANCE])
        p1, p2, _ = engine.players
        p1.hand = [SECOND_CHANCE]

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )

        sc_events = [e for e in events if isinstance(e, SecondChanceEvent)]
        assert len(sc_events) == 1
        assert sc_events[0].source is p1
        assert sc_events[0].target is p2

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

        gen, req = _advance_to_target_request(engine)
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


class TestFlipThreeEvents:

    def test_flip_three_start_event_yielded(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, THREE, SEVEN])
        p1, p2, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )

        start_events = [e for e in events if isinstance(e, FlipThreeStartEvent)]
        assert len(start_events) == 1
        assert start_events[0].source is p1
        assert start_events[0].target is p2

    def test_flip_three_resolved_event_yielded(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, THREE, SEVEN])
        _, p2, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )

        resolved_events = [e for e in events if isinstance(e, FlipThreeResolvedEvent)]
        assert len(resolved_events) == 1
        assert resolved_events[0].target is p2

    def test_flip_three_start_before_draws_resolved_after(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, THREE, SEVEN])
        _, p2, _ = engine.players

        events = drive_round(
            engine,
            hit_responses=[True, False, False, False],
            target_responses=[p2],
        )

        start_idx = next(i for i, e in enumerate(events) if isinstance(e, FlipThreeStartEvent))
        resolved_idx = next(
            i for i, e in enumerate(events)
            if isinstance(e, FlipThreeResolvedEvent)
        )
        # The 3 forced draws all happen between FlipThreeStartEvent and FlipThreeResolvedEvent
        forced_draw_idxs = [
            i for i, e in enumerate(events)
            if isinstance(e, CardDrawnEvent) and e.player is p2 and start_idx < i < resolved_idx
        ]
        assert len(forced_draw_idxs) == 3
        assert start_idx < forced_draw_idxs[0]
        assert resolved_idx > forced_draw_idxs[-1]

    def test_flip_three_resolved_still_emitted_when_target_busts(self):
        engine = _engine(opening_cards(0, 1, 2) + [FLIP_THREE, FIVE, THREE, SEVEN])
        _, p2, _ = engine.players
        p2.hand = [FIVE]

        events = drive_round(
            engine,
            hit_responses=[True, False, False],
            target_responses=[p2],
        )

        resolved_events = [e for e in events if isinstance(e, FlipThreeResolvedEvent)]
        assert len(resolved_events) == 1
        assert resolved_events[0].target is p2
