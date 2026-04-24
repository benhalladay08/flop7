"""Shared fixtures and helpers for core module tests."""
from __future__ import annotations

from typing import Any

import pytest

from flop7.core.classes.cards import Card
from flop7.core.classes.deck import Deck
from flop7.core.classes.player import Player
from flop7.core.engine.engine import GameEngine
from flop7.core.engine.requests import (
    CardDrawnEvent,
    CardInputRequest,
    Flip7Event,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
    TargetRequest,
)


# ---------------------------------------------------------------------------
# Deterministic draw callable
# ---------------------------------------------------------------------------

def deterministic_draw(cards: list[Card]):
    """Return a DrawProtocol-compatible callable that pops cards in order.

    The callable ignores the ``draw_pile`` argument and returns cards from
    the pre-set list in FIFO order.  The card must still be present in the
    draw_pile (Deck.deal removes it), so callers must ensure the draw_pile
    actually contains these cards.
    """
    it = iter(cards)

    def _draw(draw_pile: list[Card]) -> Card:
        return next(it)

    return _draw


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_deck(cards: list[Card]) -> Deck:
    """Build a Deck whose deal() returns *cards* in order.

    The deck's internal draw_pile is replaced with *cards* so that the
    deterministic draw callable and the pile stay in sync.
    """
    deck = Deck(draw=deterministic_draw(cards))
    # Replace the auto-built 94-card pile with our controlled list
    deck.draw_pile = list(cards)
    return deck


def make_players(n: int) -> list[Player]:
    """Create *n* players named P1 … Pn."""
    return [Player(name=f"P{i+1}") for i in range(n)]


def make_engine(
    cards: list[Card],
    n_players: int = 3,
    hit_responses: list[bool] | None = None,
    target_responses: list[Player] | None = None,
    real_mode: bool = False,
) -> GameEngine:
    """Build a GameEngine with deterministic deck and stub callables."""
    deck = make_deck(cards)
    players = make_players(n_players)

    hit_iter = iter(hit_responses or [])
    target_iter = iter(target_responses or [])

    def hit_stay(game: GameEngine, player: Player) -> bool:
        return next(hit_iter)

    def target_selector(game: GameEngine, event, source: Player) -> Player:
        return next(target_iter)

    engine = GameEngine(
        deck=deck,
        players=players,
        hit_stay_decider=hit_stay,
        target_selector=target_selector,
        real_mode=real_mode,
    )
    return engine


# ---------------------------------------------------------------------------
# Generator driver
# ---------------------------------------------------------------------------

def drive_round(
    engine: GameEngine,
    hit_responses: list[bool] | None = None,
    target_responses: list[Player] | None = None,
    card_inputs: list[Card] | None = None,
) -> list[Any]:
    """Drive one call to ``engine.round()`` and return all yielded objects.

    Sends the appropriate response for each yielded request:
    - ``HitStayRequest`` → next from *hit_responses*
    - ``TargetRequest``  → next from *target_responses*
    - ``CardInputRequest`` → next from *card_inputs*
    - Everything else (events) → ``None``
    """
    hit_iter = iter(hit_responses or [])
    target_iter = iter(target_responses or [])
    card_iter = iter(card_inputs or [])

    gen = engine.round()
    events: list[Any] = []

    try:
        req = next(gen)
        while True:
            events.append(req)
            if isinstance(req, HitStayRequest):
                req = gen.send(next(hit_iter))
            elif isinstance(req, TargetRequest):
                req = gen.send(next(target_iter))
            elif isinstance(req, CardInputRequest):
                req = gen.send(next(card_iter))
            else:
                req = gen.send(None)
    except StopIteration:
        pass

    return events
