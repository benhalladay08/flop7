"""Built-in simulation event trackers."""

from flop7.simulation.trackers.base import SimTracker
from flop7.simulation.trackers.bust import BustTracker
from flop7.simulation.trackers.flip7 import Flip7Tracker
from flop7.simulation.trackers.opening_freeze import OpeningFreezeTracker

__all__ = [
    "BustTracker",
    "Flip7Tracker",
    "OpeningFreezeTracker",
    "SimTracker",
    "default_trackers",
]


def default_trackers() -> list[SimTracker]:
    """Create a fresh set of default trackers for a simulation run."""
    return [Flip7Tracker(), OpeningFreezeTracker(), BustTracker()]
