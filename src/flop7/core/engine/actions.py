from typing import TYPE_CHECKING

from flop7.core.classes.cards import FLIP_THREE, FREEZE, SECOND_CHANCE
from flop7.core.enum.decisions import TargetEvent

if TYPE_CHECKING:
    from flop7.core.classes.cards import Card
    from flop7.core.classes.player import Player
    from flop7.core.engine.engine import GameEngine

def flip_three(game: GameEngine, player: Player, card: Card) -> bool:
    """
    Flip Three action: Target any active player — they must accept the next
    3 cards from the deck, flipped one at a time.

    - Stop early if the target busts or achieves Flip 7.
    - Second Chance cards resolve in real time.
    - Flip Three / Freeze cards are deferred until after all 3 cards are drawn,
      then resolved in order (only if the target hasn't busted).
    """
    target = game.target_selector(game, TargetEvent.FLIP_THREE, player)

    deferred_actions: list[Card] = []

    for _ in range(3):
        if not target.is_active:
            break  # Target busted or hit Flip 7 — stop drawing

        drawn = game.deck.deal()

        if drawn.special_action is not None:
            if drawn is SECOND_CHANCE:
                # Second Chance resolve as if drawn normally
                game.hit(target, drawn)
            else:
                # Flip Three / Freeze — defer until after all 3 cards
                deferred_actions.append(drawn)
            continue

        # Number or modifier card — process through normal hit logic
        game.hit(target, drawn)

    # Resolve deferred action cards in the order they were drawn
    for deferred in deferred_actions:
        if target.is_active:
            game.hit(target, deferred)
        else:
            game.deck.discard([deferred])

    game.deck.discard([card])  # Discard the original Flip Three card
    return False
    

def freeze(game: GameEngine, player: Player, card: Card) -> bool:
    """
    Freeze action: The player is frozen and cannot take any more actions
    for the rest of the round. They will still score points from their hand
    at the end of the round, but they cannot hit or stay.
    """
    # --- Select target (can target self or another player) ---
    target = game.target_selector(game, TargetEvent.FREEZE, player)
    target.hand.append(card)  # Give the target the Freeze card
    target.is_active = False  # Target is now frozen
    return False

def second_chance(game: GameEngine, player: Player, card: Card) -> bool:
    """
    Second Chance action: The player can use this card to absorb the next
    duplicate number card they receive without busting. This card is consumed
    after one use.
    """
    # --- This card's effect is handled in the pre_hit_hook of the GameEngine ---
    possible_players = [p for p in game.active_players if not p.has_card(SECOND_CHANCE)]
    if not possible_players:
        game.deck.discard([card])  # No valid targets, so discard the Second Chance card
        return False

    target = game.target_selector(game, TargetEvent.SECOND_CHANCE, player)

    # Safety check: selector should return only active players without Second Chance.
    if (not target.is_active) or target.has_card(SECOND_CHANCE):
        game.deck.discard([card])
        return False

    target.hand.append(card)  # Give the target the Second Chance card
    return False

# --- Add the special action functions to the corresponding cards ---
# TODO: This is a bit inelegant — we have to define the cards first, then assign the functions after. 
# We could refactor to allow defining the special_action inline when we create the Card objects.
FLIP_THREE.special_action = flip_three
FREEZE.special_action = freeze
SECOND_CHANCE.special_action = second_chance