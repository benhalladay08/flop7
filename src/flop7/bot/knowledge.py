from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from flop7.core.classes.cards import Card

if TYPE_CHECKING:
    from flop7.core.classes.deck import Deck
    from flop7.core.classes.player import Player
    from flop7.core.engine.engine import GameEngine


@dataclass(frozen=True)
class PlayerView:
    """Read-only snapshot of one player's public state."""

    index: int
    name: str
    hand: tuple[Card, ...]
    score: int
    active_score: int
    is_active: bool
    busted: bool

    @property
    def overall_score(self) -> int:
        return self.score + self.active_score

    def has_card(self, card: Card) -> bool:
        return any(c.name == card.name for c in self.hand)


@dataclass(frozen=True)
class DeckView:
    """Read-only snapshot of known deck state."""

    draw_order: tuple[Card, ...]
    remaining_count: int | None
    discard_pile: tuple[Card, ...]

    @property
    def discard_count(self) -> int:
        return len(self.discard_pile)

    @property
    def next_card(self) -> Card | None:
        if not self.draw_order:
            return None
        return self.draw_order[0]


@dataclass(frozen=True)
class GameView:
    """Read-only snapshot of the game state available to bot models."""

    players: tuple[PlayerView, ...]
    active_player_indexes: tuple[int, ...]
    round_number: int
    dealer_index: int
    real_mode: bool
    game_over: bool
    winner_index: int | None
    win_score: int
    flip_7_bonus: int
    flip_7_count: int
    deck: DeckView

    @property
    def active_players(self) -> tuple[PlayerView, ...]:
        return tuple(self.players[i] for i in self.active_player_indexes)

    @property
    def winner(self) -> PlayerView | None:
        if self.winner_index is None:
            return None
        return self.players[self.winner_index]

    @property
    def dealer(self) -> PlayerView:
        return self.players[self.dealer_index]


def build_player_view(index: int, player: Player) -> PlayerView:
    return PlayerView(
        index=index,
        name=player.name,
        hand=tuple(player.hand),
        score=player.score,
        active_score=player.active_score,
        is_active=player.is_active,
        busted=player.busted,
    )


def build_deck_view(deck: Deck, reveal_draw_order: bool) -> DeckView:
    draw_order = tuple(deck.draw_pile) if reveal_draw_order else ()
    return DeckView(
        draw_order=draw_order,
        remaining_count=len(draw_order) if reveal_draw_order else None,
        discard_pile=tuple(deck.discard_pile),
    )


def build_game_view(game: GameEngine) -> GameView:
    players = tuple(build_player_view(index, player) for index, player in enumerate(game.players))
    active_player_indexes = tuple(player.index for player in players if player.is_active)
    winner_index = game.players.index(game.winner) if game.winner in game.players else None
    return GameView(
        players=players,
        active_player_indexes=active_player_indexes,
        round_number=game.round_number,
        dealer_index=game.dealer_index,
        real_mode=game.real_mode,
        game_over=game.game_over,
        winner_index=winner_index,
        win_score=game.WIN_SCORE,
        flip_7_bonus=game.FLIP_7_BONUS,
        flip_7_count=game.FLIP_7_COUNT,
        deck=build_deck_view(game.deck, reveal_draw_order=not game.real_mode),
    )
