"""Smoke tests for flop7.core.engine.requests — dataclass instantiation."""
import pytest

from flop7.core.classes.cards import FIVE
from flop7.core.classes.player import Player
from flop7.core.enum.decisions import TargetEvent
from flop7.core.engine.requests import (
    CardDrawnEvent,
    CardInputRequest,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
    TargetRequest,
)


@pytest.fixture
def player():
    return Player("Test")


class TestRequestDataclasses:

    def test_hit_stay_request(self, player):
        r = HitStayRequest(player=player)
        assert r.player is player

    def test_card_input_request(self, player):
        r = CardInputRequest(player=player)
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
