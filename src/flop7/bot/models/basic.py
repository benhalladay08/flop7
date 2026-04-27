"""
BasicBot – a simple heuristic-driven Flip 7 bot.

Decision Logic
==============

Hit / Stay
----------
The bot uses a conservative point threshold to decide whether to draw
another card:

1. **Second Chance override** – If the bot currently holds a Second Chance
   card it will *always* hit, regardless of its hand score.  The safety
   net makes the extra draw essentially risk-free.
2. **Threshold check** – If the bot's current hand score (``active_score``)
   exceeds 25 it stays; otherwise it hits.  The boundary is inclusive:
   a score of exactly 25 still hits.

Target Selection
----------------
When an action card requires the bot to choose a target, the strategy
depends on the event type:

**Flip Three** (``TargetEvent.FLIP_THREE``)
  * If the bot has 0 or 1 cards in hand it targets *itself* – more cards
    early on are almost always beneficial.
  * Otherwise it targets the eligible player with the **highest overall
    score** (cumulative ``score`` + current ``active_score``).  Ties are
    broken randomly.

**Freeze** (``TargetEvent.FREEZE``)
  * Targets the eligible player (other than itself) with the **highest
    overall score** to knock the leader out of the round.  Ties are
    broken randomly.

**Second Chance** (``TargetEvent.SECOND_CHANCE``)
  * This event only occurs when the bot has drawn a duplicate Second Chance.
    It gives the duplicate to the eligible opponent with the **fewest overall
    points**.  Ties are broken randomly.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from flop7.bot.base import AbstractBot
from flop7.bot.utils import overall_score
from flop7.core.classes.cards import SECOND_CHANCE
from flop7.core.enum.decisions import TargetEvent

if TYPE_CHECKING:
    from flop7.bot.knowledge import GameView, PlayerView


class BasicBot(AbstractBot):
    """Simple threshold-based bot.  See module docstring for full logic."""

    # ----- HitStay --------------------------------------------------------

    def hit_stay(self, view: GameView, player: PlayerView) -> bool:
        if player.has_card(SECOND_CHANCE):
            return True
        return player.active_score <= 25

    # ----- TargetSelector -------------------------------------------------

    def target_selector(
        self,
        view: GameView,
        event: TargetEvent,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        if event is TargetEvent.FLIP_THREE:
            return self._flip_three_target(player, eligible)
        if event is TargetEvent.FREEZE:
            return self._freeze_target(player, eligible)
        if event is TargetEvent.SECOND_CHANCE:
            return self._second_chance_target(player, eligible)
        raise ValueError(f"Unknown target event: {event}")

    # ----- private helpers ------------------------------------------------

    def _flip_three_target(
        self,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        if len(player.hand) <= 1 and player in eligible:
            return player
        candidates = eligible
        best_score = max(overall_score(p) for p in candidates)
        top = [p for p in candidates if overall_score(p) == best_score]
        return random.choice(top)

    def _freeze_target(
        self,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        others = [p for p in eligible if p.index != player.index]
        if not others:
            if player in eligible:
                return player
            return random.choice(eligible)
        best_score = max(overall_score(p) for p in others)
        top = [p for p in others if overall_score(p) == best_score]
        return random.choice(top)

    def _second_chance_target(
        self,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        if not eligible:
            raise ValueError(
                "Second Chance target selection requires at least one eligible player."
            )
        lowest_score = min(overall_score(p) for p in eligible)
        bottom = [p for p in eligible if overall_score(p) == lowest_score]
        return random.choice(bottom)
