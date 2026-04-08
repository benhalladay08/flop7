from enum import Enum, auto

class TargetEvent(Enum):
    """Type of event that a TargetSelector can be looking for."""
    FLIP_THREE = auto()
    FREEZE = auto()
    SECOND_CHANCE = auto()