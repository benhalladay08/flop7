from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flop7.core.classes.cards import Card
    from flop7.core.classes.player import Player
    from flop7.core.enum.decisions import TargetEvent


@dataclass
class HitStayRequest:
    """Yield to ask whether a player should hit or stay."""
    player: Player


@dataclass
class CardInputRequest:
    """Yield to ask what card was drawn (real mode)."""
    player: Player


@dataclass
class TargetRequest:
    """Yield to ask who should be targeted by an action card."""
    event: TargetEvent
    source: Player
    eligible: list[Player]


@dataclass
class CardDrawnEvent:
    """Yield to notify that a card was drawn."""
    player: Player
    card: Card


@dataclass
class PlayerBustedEvent:
    """Yield to notify that a player busted."""
    player: Player
    card: Card


@dataclass
class RoundOverEvent:
    """Yield to notify that the round is complete."""
    round_number: int


@dataclass
class Flip7Event:
    """Yield to notify that a player achieved Flip 7 (7 unique number cards)."""
    player: Player


@dataclass
class FreezeEvent:
    """Yield to notify that a player has been frozen by a Freeze action."""
    source: Player
    target: Player


@dataclass
class SecondChanceEvent:
    """Yield to notify that a Second Chance card was assigned to a player."""
    source: Player
    target: Player


@dataclass
class FlipThreeStartEvent:
    """Yield to notify that a Flip Three sequence is beginning."""
    source: Player
    target: Player


@dataclass
class FlipThreeResolvedEvent:
    """Yield to notify that a Flip Three sequence has finished resolving."""
    target: Player
