"""
OmniscientBot – a perfect-information Flip 7 bot.

Takes full advantage of knowing the exact draw pile order (virtual mode
only).  Designed to be extremely difficult to beat.

Hit / Stay
----------
Looks at the next card in the draw pile:

- If it would bust (duplicate bustable), stay — unless holding Second
  Chance, which absorbs the bust.
- Otherwise, hit.

Target Selection
----------------
**Flip Three** (``TargetEvent.FLIP_THREE``)
  Simulates the next 3 draws against every eligible player's hand:

  1. If any opponent would bust from the 3 cards, target the one with the
     highest hand score (maximum damage).
  2. If no opponent busts but the cards are safe for the bot, self-target
     (free points).
  3. Otherwise target the leader (saddle them with risky cards).

**Freeze** (``TargetEvent.FREEZE``)
  Targets the biggest threat among opponents, but avoids freezing someone
  who would likely bust on their own (> 50 % of remaining bustable cards
  are duplicates of theirs).  Freezing a self-destructing player *saves*
  their hand score — better to let them bust.

**Second Chance** (``TargetEvent.SECOND_CHANCE``)
  Passes the duplicate shield to the opponent most likely to bust,
  effectively wasting it on a bust that was going to happen anyway.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flop7.bot.base import AbstractBot
from flop7.core.classes.cards import FLIP_THREE, FREEZE, SECOND_CHANCE
from flop7.core.enum.decisions import TargetEvent

if TYPE_CHECKING:
    from flop7.bot.knowledge import DeckView, GameView, PlayerView
    from flop7.core.classes.cards import Card


class OmniscientBot(AbstractBot):
    """Perfect-information bot.  See module docstring for full logic."""

    virtual_only = True

    # ── Hit / Stay ───────────────────────────────────────────────────

    def hit_stay(self, view: GameView, player: PlayerView) -> bool:
        next_card = view.deck.next_card
        if next_card is None:
            return False
        if next_card.bustable and player.has_card(next_card):
            return player.has_card(SECOND_CHANCE)
        return True

    # ── Target Selection ─────────────────────────────────────────────

    def target_selector(
        self,
        view: GameView,
        event: TargetEvent,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        if event is TargetEvent.FLIP_THREE:
            return self._flip_three_target(view, player, eligible)
        if event is TargetEvent.FREEZE:
            return self._freeze_target(view, player, eligible)
        if event is TargetEvent.SECOND_CHANCE:
            return self._second_chance_target(view, player, eligible)
        raise ValueError(f"Unknown target event: {event}")

    # ── Shared helpers ───────────────────────────────────────────────

    @staticmethod
    def _bust_rate(target: PlayerView, deck: DeckView) -> float:
        """Fraction of remaining bustable cards that would bust *target*."""
        remaining = [c for c in deck.draw_order if c.bustable]
        if not remaining:
            return 0.0
        return sum(1 for c in remaining if target.has_card(c)) / len(remaining)

    @staticmethod
    def _would_bust_from_cards(
        target: PlayerView,
        cards: tuple[Card, ...],
    ) -> bool:
        """Simulate whether *target* busts from receiving *cards*.

        Mirrors the Flip Three resolution rules: Flip Three and Freeze
        are deferred (ignored for bust purposes), Second Chance grants
        protection if the target doesn't already have it, and a duplicate
        bustable card triggers a bust (unless absorbed by Second Chance).
        """
        bustable_names: set[str] = {c.name for c in target.hand if c.bustable}
        has_sc = target.has_card(SECOND_CHANCE)

        for card in cards:
            if card.abbrv in (FLIP_THREE.abbrv, FREEZE.abbrv):
                continue
            if card.abbrv == SECOND_CHANCE.abbrv:
                if not has_sc:
                    has_sc = True
                continue
            if card.bustable and card.name in bustable_names:
                if has_sc:
                    has_sc = False
                    continue
                return True
            if card.bustable:
                bustable_names.add(card.name)
        return False

    # ── Targeting strategies ─────────────────────────────────────────

    def _flip_three_target(
        self,
        view: GameView,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        next_3 = view.deck.draw_order[:3]
        opponents = [p for p in eligible if p.index != player.index]

        # 1. Bust the opponent who loses the most hand score
        bust_targets = [p for p in opponents if self._would_bust_from_cards(p, next_3)]
        if bust_targets:
            return max(bust_targets, key=lambda p: p.active_score)

        # 2. Self-target if the cards are safe (free points)
        if player in eligible and not self._would_bust_from_cards(player, next_3):
            return player

        # 3. Saddle the leader with risky cards
        if opponents:
            return max(opponents, key=lambda p: p.overall_score)
        return player

    def _freeze_target(
        self,
        view: GameView,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        others = [p for p in eligible if p.index != player.index]
        if not others:
            return player

        # Skip opponents likely to bust on their own (> 50 % bust rate)
        safe_threats = [p for p in others if self._bust_rate(p, view.deck) <= 0.5]
        pool = safe_threats if safe_threats else others
        return max(pool, key=lambda p: p.overall_score)

    def _second_chance_target(
        self,
        view: GameView,
        player: PlayerView,
        eligible: tuple[PlayerView, ...],
    ) -> PlayerView:
        # Waste the shield on the opponent most likely to bust anyway
        return max(eligible, key=lambda p: self._bust_rate(p, view.deck))
