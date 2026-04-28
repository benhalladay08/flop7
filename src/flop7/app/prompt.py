from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Prompt:
    """Data contract between the orchestrator and the TUI command bar.

    The orchestrator constructs a Prompt for each step in the flow.
    The TUI renders it and uses the validator for inline error display.

    If ``auto_advance_ms`` is set, the TUI starts a timer when the prompt
    is shown; on expiry it submits an empty string as input. The timer is
    cancelled if the user submits manually first.
    """

    instruction: str
    validator: Callable[[str], str | None] = field(default=lambda _: None)
    placeholder: str = ""
    auto_advance_ms: int | None = None
