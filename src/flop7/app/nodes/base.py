from __future__ import annotations

from abc import ABC, abstractmethod

from flop7.app.prompt import Prompt


class Node(ABC):
    """Base class for a single step in the orchestrator's decision tree.

    Each node knows its prompt and how to compute the next node from
    validated user input.
    """

    @property
    @abstractmethod
    def prompt(self) -> Prompt:
        """The prompt to display while this node is active."""

    @abstractmethod
    def on_input(self, value: str, context: dict) -> Node | None:
        """Process validated input. Return the next node, or ``None`` to stay."""
