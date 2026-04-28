"""Smoke tests for flop7.core.engine.requests — dataclass instantiation."""

import pytest

from flop7.core.classes.cards import FIVE
from flop7.core.classes.player import Player
from flop7.core.engine.requests import (
    CardDrawnEvent,
    CardDrawRequest,
    Flip7Event,
    FlipThreeResolvedEvent,
    FlipThreeStartEvent,
    FreezeEvent,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
    SecondChanceEvent,
    TargetRequest,
)
from flop7.core.enum.decisions import TargetEvent


@pytest.fixture
def player():
    return Player("Test")


class TestRequestDataclasses:

    def test_hit_stay_request(self, player):
        r = HitStayRequest(player=player)
        assert r.player is player

    def test_card_draw_request(self, player):
        r = CardDrawRequest(player=player)
        assert r.player is player

    def test_target_request(self, player):
        r = TargetRequest(
            event=TargetEvent.FLIP_THREE,
            source=player,
            eligible=[player],
        )
        assert r.event is TargetEvent.FLIP_THREE
        assert r.source is player
        assert r.eligible == [player]

    def test_card_drawn_event(self, player):
        e = CardDrawnEvent(player=player, card=FIVE)
        assert e.player is player
        assert e.card is FIVE

    def test_player_busted_event(self, player):
        e = PlayerBustedEvent(player=player, card=FIVE)
        assert e.player is player
        assert e.card is FIVE

    def test_round_over_event(self):
        e = RoundOverEvent(round_number=3)
        assert e.round_number == 3

    def test_flip7_event(self, player):
        e = Flip7Event(player=player)
        assert e.player is player

    def test_freeze_event(self, player):
        other = Player("Other")
        e = FreezeEvent(source=player, target=other)
        assert e.source is player
        assert e.target is other

    def test_second_chance_event(self, player):
        other = Player("Other")
        e = SecondChanceEvent(source=player, target=other)
        assert e.source is player
        assert e.target is other

    def test_flip_three_start_event(self, player):
        other = Player("Other")
        e = FlipThreeStartEvent(source=player, target=other)
        assert e.source is player
        assert e.target is other

    def test_flip_three_resolved_event(self, player):
        e = FlipThreeResolvedEvent(target=player)
        assert e.target is player
