# Architecture

Flop 7 is split into five main layers:

- `core` owns game state, card resolution, scoring, round lifecycle, and
  request/event objects. It has no terminal UI or bot strategy dependencies.
- `bot` adapts read-only game views into bot decisions. Bots receive immutable
  snapshots and return hit/stay or target choices through `BotController`.
- `app` owns orchestration. It turns engine requests/events into prompt-driven
  nodes and coordinates screen transitions.
- `simulation` runs all-bot game batches and aggregates simulation statistics.
- `tui` owns urwid widgets and rendering. It consumes prompts and renders the
  current game or simulation state.

The engine is generator-driven. It yields requests such as `CardDrawRequest`,
`HitStayRequest`, and `TargetRequest`, then expects the app layer to send the
chosen response back. Notification events such as `CardDrawnEvent`,
`FreezeEvent`, and `RoundOverEvent` let the app update the display without
mixing UI concerns into game logic.

For detailed class diagrams and rules-specific behavior, see
[design.md](design.md) and [rules.md](rules.md).
