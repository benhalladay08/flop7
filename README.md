# Flop 7

An unofficial terminal implementation of the Flip 7 card game. The app can run
virtual games, act as a scorekeeper for real games, and simulate batches of
bot-only games.

## Requirements

- Python 3.10+
- `urwid`

## Install

```bash
pip install .
```

For local development:

```bash
python -m pip install -e .
```

## Run

```bash
flop7
```

or:

```bash
python -m flop7
```

## Test

```bash
pytest
```

## Docs

- [Rules](docs/rules.md)
- [Design](docs/design.md)
- [Architecture](docs/architecture.md)
