# Flop 7

Welcome to Flop 7, the unofficial terminal emulator for Flip 7. You can play virtual games, keep score for live games at the table, or run batched all-bot simulations to benchmark your own strategies.

Really, this repo is made to **build and test different bot strategies.** See the [bot guide](docs/guides/bots.md) for more info.

## Install

```bash
# Homebrew (macOS / Linux)
brew install benhalladay08/tap/flop7

# pipx
pipx install flop7

# pip
pip install flop7

# install.sh (downloads the latest release binary)
curl -fsSL https://raw.githubusercontent.com/benhalladay08/flop7/main/install.sh | sh
```

For full options including local development installs, see [docs/install.md](docs/install.md).

## Run

```bash
flop7
```

## Documentation

- [Install](docs/install.md) — distribution channels and platform notes
- [Rules](docs/rules.md) — Flip 7 game rules
- [Architecture](docs/architecture.md) — comprehensive layer-by-layer reference
- [Roadmap](docs/roadmap.md) — planned features

### Guides

- [Local development](docs/guides/development.md) — clone, run, and test the repo
- [Building bots](docs/guides/bots.md) — write a new bot, register it, and benchmark it
- [Building trackers](docs/guides/trackers.md) — collect custom statistics across simulation batches

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

Created by Ben Halladay
