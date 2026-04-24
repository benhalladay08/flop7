from __future__ import annotations

from collections.abc import Mapping

from flop7.bot.base import AbstractBot
from flop7.bot.knowledge import build_game_view
from flop7.core.classes.player import Player
from flop7.core.enum.decisions import TargetEvent


class BotController:
    """Adapter between engine requests and read-only bot decisions."""

    def __init__(self, bots_by_player_index: Mapping[int, AbstractBot] | None = None):
        self._bots_by_player_index = dict(bots_by_player_index or {})

    def has_bot(self, game, player: Player) -> bool:
        return self._player_index(game, player) in self._bots_by_player_index

    def hit_stay(self, game, player: Player) -> bool:
        index = self._player_index(game, player)
        bot = self._bot_for_index(index)
        view = build_game_view(game)
        return bot.hit_stay(view, view.players[index])

    def target_selector(
        self,
        game,
        event: TargetEvent,
        source: Player,
        eligible: list[Player],
    ) -> Player:
        source_index = self._player_index(game, source)
        bot = self._bot_for_index(source_index)
        view = build_game_view(game)
        eligible_indexes = tuple(
            self._player_index(game, player) for player in eligible
        )
        eligible_views = tuple(view.players[index] for index in eligible_indexes)

        selected = bot.target_selector(
            view,
            event,
            view.players[source_index],
            eligible_views,
        )
        if selected.index not in eligible_indexes:
            raise ValueError(
                f"Bot selected ineligible target index {selected.index} "
                f"for {event.name}."
            )
        return game.players[selected.index]

    def _bot_for_index(self, index: int) -> AbstractBot:
        try:
            return self._bots_by_player_index[index]
        except KeyError as exc:
            raise ValueError(f"No bot registered for player index {index}.") from exc

    @staticmethod
    def _player_index(game, player: Player) -> int:
        return game.players.index(player)
