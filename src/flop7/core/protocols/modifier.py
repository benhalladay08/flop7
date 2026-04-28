from __future__ import annotations

from typing import Protocol


class ScoreModifier(Protocol):
    def __call__(self, current_score: int) -> int:
        """
        Modify the player's score based on the current score.
        """
