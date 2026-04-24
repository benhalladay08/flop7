import flop7.core.engine.actions  # Need to import this to register the card actions
from flop7.core.classes.cards import Card, SECOND_CHANCE
from flop7.core.classes.deck import Deck
from flop7.core.classes.player import Player
from flop7.core.engine.requests import (
    CardDrawnEvent,
    CardInputRequest,
    Flip7Event,
    HitStayRequest,
    PlayerBustedEvent,
    RoundOverEvent,
    TargetRequest,
)
from flop7.core.protocols.decisions import HitStay, TargetSelector
from flop7.core.protocols.actions import CardAction
from flop7.core.protocols.modifier import ScoreModifier


class GameEngine:
    """
    Base game engine. Owns the player list, handles scoring, round lifecycle,
    dealer rotation, and win-condition checking. Subclasses provide the card
    source (virtual deck vs. external input).
    """

    WIN_SCORE = 200
    FLIP_7_BONUS = 15
    FLIP_7_COUNT = 7

    def __init__(
        self,
        deck: Deck,
        players: list[Player],
        hit_stay_decider: HitStay,
        target_selector: TargetSelector,
        real_mode: bool = False,
    ):
        if len(players) < 3:
            raise ValueError("Flip 7 requires at least 3 players.")

        self.deck = deck
        self.players = players
        self.hit_stay_decider = hit_stay_decider
        self.target_selector = target_selector
        self.real_mode = real_mode
        self.round_number: int = 0

        # --- Endgame state ---
        self.game_over: bool = False
        self.winner: Player | None = None

        # --- Flip 7 tracking (reset each round) ---
        self._flip7_player: Player | None = None

    @property
    def active_players(self) -> list[Player]:
        """Players still in the current round (haven't stayed or frozen)."""
        return [p for p in self.players if p.is_active]
    
    def play(self) -> None:
        """Main game loop. Auto-drives the round generator using the
        engine's callables. Continues until a player reaches WIN_SCORE."""
        while not self.game_over:
            gen = self.round()
            req = next(gen)
            while True:
                try:
                    if isinstance(req, HitStayRequest):
                        req = gen.send(self.hit_stay_decider(self, req.player))
                    elif isinstance(req, TargetRequest):
                        req = gen.send(self.target_selector(self, req.event, req.source))
                    elif isinstance(req, CardInputRequest):
                        req = gen.send(self.deck.deal())
                    else:
                        req = gen.send(None)
                except StopIteration:
                    break
    
    def round(self):
        """Generator for one round of play.

        Each round begins with an opening deal: every player is dealt exactly
        one card in seat order, and action cards resolve immediately as they
        are dealt. This opening pass does not replace action cards that do not
        remain in front of the player. After that, active players choose
        whether to hit or stay; players with an empty hand are forced to draw
        instead of receiving a hit/stay choice.

        Yields decision requests (``HitStayRequest``, ``CardInputRequest``,
        ``TargetRequest``) and notification events (``CardDrawnEvent``,
        ``PlayerBustedEvent``, ``RoundOverEvent``).

        Callers advance the generator with ``.send(response)`` where
        *response* is the answer to the most-recently yielded request.
        Notification events expect ``None`` back.

        For automated / bot play, use ``play()`` which auto-drives this
        generator using the engine's callables.
        """
        if not self.real_mode:
            self.deck.reshuffle()

        self._flip7_player = None

        # --- Opening deal: one mandatory card per player ---
        for player in self.players:
            card = yield from self._draw(player)
            yield from self._hit(player, card)
            if self._flip7_player is not None:
                break

        while self._flip7_player is None and len(self.active_players) > 0:
            for player in list(self.active_players):
                if not player.is_active:
                    continue

                if player.hand:
                    hit = yield HitStayRequest(player=player)
                    if not hit:
                        player.is_active = False
                        continue

                card = yield from self._draw(player)
                yield from self._hit(player, card)

                if self._flip7_player is not None:
                    break
            if self._flip7_player is not None:
                break

        # --- End-of-round scoring and cleanup ---
        for player in self.players:
            if not player.busted:
                player.score += player.active_score
                if player is self._flip7_player:
                    player.score += self.FLIP_7_BONUS
            self.deck.discard(player.hand)
            player.hand.clear()
            player.is_active = True
            player.busted = False

        self.round_number += 1

        if any(p.score >= self.WIN_SCORE for p in self.players):
            self.game_over = True
            self.winner = max(self.players, key=lambda p: p.score)

        yield RoundOverEvent(round_number=self.round_number)

    # --- round generator helpers --------------------------------------

    def _draw(self, player: Player):
        """Yield a draw request (real) or auto-deal and notify (virtual)."""
        if self.real_mode:
            card = yield CardInputRequest(player=player)
        else:
            card = self.deck.deal()
        yield CardDrawnEvent(player=player, card=card)
        return card

    def _hit(self, player: Player, card: Card):
        """Process a card through bust / special-action / flip-7 logic."""
        if self._pre_hit(player, card):
            return

        if card.special_action is not None:
            yield from card.special_action(self, player, card)
            return

        if card.bustable and player.has_card(card):
            player.hand.append(card)
            player.busted = True
            player.is_active = False
            yield PlayerBustedEvent(player=player, card=card)
        else:
            player.hand.append(card)
            if self._has_flip7(player):
                self._flip7_player = player
                for p in self.players:
                    p.is_active = False
                yield Flip7Event(player=player)

    def _has_flip7(self, player: Player) -> bool:
        """Check if a player has 7 unique number (bustable) cards."""
        return sum(1 for c in player.hand if c.bustable) >= self.FLIP_7_COUNT

    def _pre_hit(self, player: Player, card: Card) -> bool:
        """Second Chance absorption check."""
        if player.has_card(SECOND_CHANCE) and card.bustable and player.has_card(card):
            sc = next(c for c in player.hand if c.name == SECOND_CHANCE.name)
            player.hand.remove(sc)
            self.deck.discard([sc, card])
            return True
        return False
