from typing import TYPE_CHECKING

from flop7.core.classes.cards import FLIP_THREE, FREEZE, SECOND_CHANCE
from flop7.core.engine.requests import TargetRequest
from flop7.core.enum.decisions import TargetEvent

if TYPE_CHECKING:
    from flop7.core.classes.cards import Card
    from flop7.core.classes.player import Player
    from flop7.core.engine.engine import GameEngine


def flip_three(game: GameEngine, player: Player, card: Card):
    """
    Flip Three action: Target any active player — they must accept the next
    3 cards from the deck, flipped one at a time.

    - Stop early if the target busts or achieves Flip 7.
    - Second Chance cards resolve in real time.
    - Flip Three / Freeze cards are deferred until after all 3 cards are drawn,
      then resolved in order (only if the target hasn't busted).
    """
    eligible = list(game.active_players)
    target = yield TargetRequest(
        event=TargetEvent.FLIP_THREE, source=player, eligible=eligible,
    )

    deferred: list[Card] = []
    for _ in range(3):
        if not target.is_active:
            break

        drawn = yield from game._draw(target)
        if drawn.special_action is not None:
            if drawn.name == SECOND_CHANCE.name:
                yield from game._hit(target, drawn)
            else:
                deferred.append(drawn)
        else:
            yield from game._hit(target, drawn)

    for d in deferred:
        if target.is_active:
            yield from game._hit(target, d)
        else:
            game.deck.discard([d])

    game.deck.discard([card])


def freeze(game: GameEngine, player: Player, card: Card):
    """
    Freeze action: Target a player — they are frozen for the rest of the
    round but still score points from their current hand.
    """
    eligible = list(game.active_players)
    target = yield TargetRequest(
        event=TargetEvent.FREEZE, source=player, eligible=eligible,
    )
    target.hand.append(card)
    target.is_active = False


def second_chance(game: GameEngine, player: Player, card: Card):
    """
    Second Chance action: The drawing player keeps the shield unless they
    already have one, in which case they pass it to another active player.
    """
    if not player.has_card(SECOND_CHANCE):
        player.hand.append(card)
        return

    eligible = [
        p for p in game.active_players
        if p is not player and not p.has_card(SECOND_CHANCE)
    ]
    if not eligible:
        game.deck.discard([card])
        return

    target = yield TargetRequest(
        event=TargetEvent.SECOND_CHANCE, source=player, eligible=eligible,
    )
    if target not in eligible or not target.is_active or target.has_card(SECOND_CHANCE):
        game.deck.discard([card])
        return

    target.hand.append(card)


# --- Register generators on the card objects ---
FLIP_THREE.special_action = flip_three
FREEZE.special_action = freeze
SECOND_CHANCE.special_action = second_chance
