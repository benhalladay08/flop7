"""Shared fixtures and helpers for core module tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flop7.core.classes.cards import Card
from flop7.core.classes.deck import Deck
from flop7.core.classes.player import Player
from flop7.core.engine.engine import GameEngine
from flop7.core.engine.requests import (
    CardDrawRequest,
    HitStayRequest,
    TargetRequest,
)

# ---------------------------------------------------------------------------
# Opening-round filler cards
# ---------------------------------------------------------------------------

OPENING_CARDS = [
    Card(name="Opening A", abbrv="OA", num_in_deck=0, points=0, bustable=False),
    Card(name="Opening B", abbrv="OB", num_in_deck=0, points=0, bustable=False),
    Card(name="Opening C", abbrv="OC", num_in_deck=0, points=0, bustable=False),
]


def opening_cards(*player_indexes: int) -> list[Card]:
    """Return zero-point filler cards for the given player indexes."""
    return [OPENING_CARDS[i] for i in player_indexes]


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def make_deck(cards: list[Card]) -> Deck:
    """Build a Deck whose deal() returns *cards* in order."""
    return Deck(cards=cards)


def make_players(n: int) -> list[Player]:
    """Create *n* players named P1 … Pn."""
    return [Player(name=f"P{i+1}") for i in range(n)]


def make_engine(
    cards: list[Card],
    n_players: int = 3,
    hit_responses: list[bool] | None = None,
    target_responses: list[Player] | None = None,
    card_provider: Callable[[GameEngine, Player], Card] | None = None,
    real_mode: bool = False,
    dealer_index: int = 0,
) -> GameEngine:
    """Build a GameEngine with deterministic deck and stub callables."""
    deck = make_deck(cards)
    players = make_players(n_players)

    hit_iter = iter(hit_responses or [])
    target_iter = iter(target_responses or [])

    def hit_stay(game: GameEngine, player: Player) -> bool:
        return next(hit_iter)

    def target_selector(
        game: GameEngine,
        event,
        source: Player,
        eligible: list[Player],
    ) -> Player:
        return next(target_iter)

    def default_card_provider(game: GameEngine, player: Player) -> Card:
        return game.deck.deal()

    engine = GameEngine(
        deck=deck,
        players=players,
        card_provider=card_provider or default_card_provider,
        hit_stay_decider=hit_stay,
        target_selector=target_selector,
        real_mode=real_mode,
        dealer_index=dealer_index,
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
    - ``CardDrawRequest`` → next from *card_inputs* in real mode,
      or ``engine.deck.deal()`` in virtual mode
    - Everything else (events) → ``None``
    """
    auto_deal = card_inputs is None and not engine.real_mode
    hit_iter = iter(hit_responses or [])
    target_iter = iter(target_responses or [])
    card_iter = iter(card_inputs or [])

    gen = engine.round()
    events: list[Any] = []

    def next_response(iterator, label: str):
        try:
            return next(iterator)
        except StopIteration as exc:
            raise AssertionError(f"Missing {label} response while driving round") from exc

    try:
        req = next(gen)
    except StopIteration:
        return events

    while True:
        events.append(req)
        try:
            if isinstance(req, HitStayRequest):
                req = gen.send(next_response(hit_iter, "hit/stay"))
            elif isinstance(req, TargetRequest):
                req = gen.send(next_response(target_iter, "target"))
            elif isinstance(req, CardDrawRequest):
                card = (
                    engine.deck.deal()
                    if auto_deal
                    else next_response(
                        card_iter,
                        "card draw",
                    )
                )
                req = gen.send(card)
            else:
                req = gen.send(None)
        except StopIteration:
            break

    return events
