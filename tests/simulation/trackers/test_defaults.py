"""Tests for default simulation trackers."""

from flop7.simulation.trackers import SimTracker, default_trackers


class TestDefaultTrackers:

    def test_all_satisfy_protocol(self):
        for tracker in default_trackers():
            assert isinstance(tracker, SimTracker)

    def test_each_has_unique_label(self):
        labels = [tracker.label for tracker in default_trackers()]

        assert len(labels) == len(set(labels))
