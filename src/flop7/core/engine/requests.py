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
