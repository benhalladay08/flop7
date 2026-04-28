# Contributing to Flop 7

Flop 7 exists primarily as a sandbox for **designing and benchmarking Flip 7 bots**, so most contributions land in the `bot/` and `simulation/` modules — but architecture, TUI, and core-engine improvements are equally welcome.

## Quick links

- [Roadmap of future features](docs/roadmap.md)
- [Local development setup](docs/guides/development.md)
- [Building a new bot](docs/guides/bots.md)
- [Building a new simulation tracker](docs/guides/trackers.md)
- [Architecture overview](docs/architecture.md)

## Workflow

1. Fork the repo and create a feature branch off `main`.
2. Install in editable mode: `python -m pip install -e .`
3. Make your change. Add tests under `tests/` mirroring the source layout.
4. Run the full test suite: `pytest`
5. Open a pull request against `main`.

## Commit conventions

Flop 7 uses [Conventional Commits](https://www.conventionalcommits.org/) so that [release-please](https://github.com/googleapis/release-please) can automate version bumps from commit history.

| Prefix      | Use for                                       | Version bump |
| ----------- | --------------------------------------------- | ------------ |
| `feat:`     | New user-facing feature                       | minor        |
| `fix:`      | Bug fix                                       | patch        |
| `chore:`    | Tooling, CI, dependencies                     | none         |
| `docs:`     | Documentation only                            | none         |
| `refactor:` | Internal change with no behavior change       | none         |
| `test:`     | Tests only                                    | none         |

Add `!` after the type (e.g. `feat!: ...`) or include a `BREAKING CHANGE:` footer for breaking changes — these trigger a major bump.

Examples:

```
feat: add aggressive bot model with deeper EV search
fix: correct Second Chance discard ordering on duplicate Flip Three
docs: clarify tracker registration in default_trackers
```

## Code style

Style is enforced by [pre-commit](https://pre-commit.com/) hooks: `ruff` (lint + autofix + import sorting) and `black` (formatting). Set them up once after cloning:

```bash
pip install -e ".[dev]"
pre-commit install
```

After that, `ruff` and `black` run automatically on every commit. To run them manually:

```bash
pre-commit run --all-files
```

Configuration lives in `pyproject.toml` (`[tool.ruff]`, `[tool.black]`) and `.pre-commit-config.yaml`.

A few stylistic conventions that aren't enforced by the linter but match the rest of the codebase:

- Type hints on public functions and dataclass fields
- `from __future__ import annotations` at the top of files using forward references
- Use `Protocol` for engine-side dependency contracts; use `ABC` for `AbstractBot`

## Tests

Run the suite with:

```bash
pytest
```

Test layout mirrors `src/flop7/`. Fixtures live in [`tests/conftest.py`](tests/conftest.py) — `make_engine`, `make_deck`, `make_players`, and `drive_round` are the building blocks for almost every engine-level test.

Every behavior change should ship with a test. If you're adding a new bot or tracker, mirror the patterns in `tests/bot/models/test_basic.py` and `tests/simulation/test_runner.py`.

## Reporting bugs and proposing features

Open a GitHub issue with:

- What you expected to happen
- What actually happened
- A minimal reproduction (a bot config, a simulation seed, or a card sequence)

For larger features, sketch the idea on the [ideas board discussion](https://github.com/benhalladay08/flop7/discussions/1) or open an issue first — it saves rework.

## Project rule: extend, don't reimplement

The core engine yields requests and events through a generator. **Do not duplicate engine logic** in bots, trackers, or app nodes — extend it through the existing hook points (`hit_stay`, `target_selector`, tracker `on_event`, engine listeners). If you need a new hook, add it to the engine and document it.
