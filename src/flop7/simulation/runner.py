"""Run all-bot Flip 7 games for simulations."""

from __future__ import annotations

from flop7.bot.base import AbstractBot
from flop7.bot.controller import BotController
from flop7.bot.registry import Bot
from flop7.core.classes.deck import Deck
from flop7.core.classes.player import Player
from flop7.core.engine.engine import GameEngine
from flop7.simulation.trackers.base import SimTracker


def run_game(
    bot_types: dict[str, int],
    trackers: list[SimTracker] | None = None,
) -> GameEngine:
    """Create and play a single all-bot game, returning the finished engine."""
    players: list[Player] = []
    bots_by_index: dict[int, AbstractBot] = {}

    for bot_type, count in bot_types.items():
        for i in range(count):
            idx = len(players)
            players.append(Player(f"{bot_type} {i + 1}"))
            bots_by_index[idx] = Bot.create(bot_type, virtual=True)

    controller = BotController(bots_by_index)
    deck = Deck()

    engine = GameEngine(
        deck=deck,
        players=players,
        card_provider=lambda game, _player: game.deck.deal(),
        hit_stay_decider=controller.hit_stay,
        target_selector=controller.target_selector,
    )

    _trackers = trackers or ()
    listeners = [tracker.on_event for tracker in _trackers]
    engine.play(listeners=listeners)
    for tracker in _trackers:
        tracker.on_game_over(engine)

    return engine
