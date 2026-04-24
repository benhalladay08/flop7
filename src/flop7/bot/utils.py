"""Bot utility functions shared across bot implementations."""

from flop7.core.classes.player import Player


def overall_score(player: Player) -> int:
    """Return a player's overall score: cumulative score + current hand total.
    
    This combines the player's banked score from previous rounds with
    their active_score from the current hand to give the total standing.
    """
    return player.score + player.active_score
