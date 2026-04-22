from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Prompt:
    """Data contract between the orchestrator and the TUI command bar.

    The orchestrator constructs a Prompt for each step in the flow.
    The TUI renders it and uses the validator for inline error display.
    """

    instruction: str
    validator: Callable[[str], str | None] = field(default=lambda _: None)
    placeholder: str = ""
