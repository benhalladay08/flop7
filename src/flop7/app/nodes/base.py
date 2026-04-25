from __future__ import annotations

from abc import ABC, abstractmethod

from flop7.app.prompt import Prompt


class Node(ABC):
    """Base class for a single step in the orchestrator's decision tree.

    Each node knows its prompt and how to compute the next node from
    validated user input.

    Dispatcher nodes (``is_dispatcher = True``) have no prompt of their
    own; the orchestrator calls ``dispatch()`` to resolve them to a real
    child node before showing a prompt.
    """

    is_dispatcher: bool = False

    @property
    @abstractmethod
    def prompt(self) -> Prompt:
        """The prompt to display while this node is active."""

    @abstractmethod
    def on_input(self, value: str, context: dict) -> Node | None:
        """Process validated input. Return the next node, or ``None`` to stay."""
