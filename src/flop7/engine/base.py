from abc import ABC, abstractmethod

import flop7.engine.actions  # Need to import this to register the card actions
from flop7.classes.cards import Card, SECOND_CHANCE
from flop7.classes.deck import Deck
from flop7.classes.player import Player
from flop7.protocols.decisions import HitStay, TargetSelector
from flop7.protocols.actions import CardAction
from flop7.protocols.modifier import ScoreModifier


class GameEngine(ABC):
    """
    Base game engine. Owns the player list, handles scoring, round lifecycle,
    dealer rotation, and win-condition checking. Subclasses provide the card
    source (virtual deck vs. external input).
    """

    WIN_SCORE = 200

    def __init__(
        self,
        deck: Deck,
        players: list[Player],
        hit_stay_decider: HitStay,
        target_selector: TargetSelector,
    ):
        if len(players) < 3:
            raise ValueError("Flip 7 requires at least 3 players.")

        self.deck = deck
        self.players = players
        self.hit_stay_decider = hit_stay_decider
        self.target_selector = target_selector
        self.round_number: int = 0

        # --- Endgame state ---
        self.game_over: bool = False
        self.winner: Player | None = None

    @property
    def active_players(self) -> list[Player]:
        """Players still in the current round (haven't stayed or frozen)."""
        return [p for p in self.players if p.is_active]
    
    def play(self) -> None:
        """Main game loop. Continues until a player reaches WIN_SCORE."""
        while not self.game_over:
            self.round()
    
    def round(self) -> None:
        """Run a full round: deal, player turns, scoring, end-of-round cleanup."""
        while len(self.active_players) > 1:
            for player in self.active_players:
                if self.hit_stay_decider(player):
                    self.hit(player, self.deck.deal())
                else:
                    player.is_active = False  # Player stays

        # --- Scoring and cleanup ---
        for player in self.players:
            player.score += player.active_score
            self.deck.discard(player.hand)
            player.hand.clear()
            player.is_active = True  # Reset for next round

        self.round_number += 1

        # --- Endgame logic ---
        if any(p.score >= self.WIN_SCORE for p in self.players):
            self.game_over = True
            self.winner = max(self.players, key=lambda p: p.score)

    def hit(self, player: Player, card: Card) -> None:
        if self.pre_hit_hook(player, card):
            return  # Card was consumed by the hook (e.g. Second Chance absorbed a duplicate)

        # --- Handle special action cards (Flip Three, Freeze, Second Chance) ---
        add_to_hand = True
        if card.special_action:
            add_to_hand = card.special_action(self, player, card)

        # --- Handle normal card reception ---
        if card.bustable and player.has_card(card):
            player.hand.append(card)
            player.score = 0
            player.is_active = False
        elif add_to_hand:
            player.hand.append(card)

        self.post_hit_hook(player, card)

    def pre_hit_hook(self, player: Player, card: Card) -> bool:
        """Hook for pre-hit logic. Returns True if the card was consumed and hit() should abort."""
        
        # --- Player can use Second Chance to absorb the duplicate card ---
        if player.has_card(SECOND_CHANCE) and card.bustable and player.has_card(card):
            second_chance_card = next(c for c in player.hand if c.name == SECOND_CHANCE)
            player.hand.remove(second_chance_card)
            self.deck.discard([second_chance_card, card])
            return True

        return False

    def post_hit_hook(self, player: Player, card: Card) -> None:
        """Hook for any special logic that needs to run after a card is added to the player's hand."""
        
        # --- Special handling for 7 unique number cards ---
        if len(set(c.name for c in player.hand if c.bustable)) >= 7:
            pass