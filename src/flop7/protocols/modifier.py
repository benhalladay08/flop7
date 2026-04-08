from typing import Protocol

class ScoreModifier(Protocol):
    def __call__(self, current_score: int) -> int:
        """
        Modify the player's score based on the current score and the card drawn.
        This is where the logic for special cards that modify the score will be implemented.
        """