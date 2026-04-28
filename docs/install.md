# Installing Flop 7

Flop 7 ships through several channels. Pick whichever fits your environment.

## Homebrew (recommended for macOS / Linux)

```bash
brew install benhalladay08/tap/flop7
```

This pulls from the `benhalladay08/tap` Homebrew tap and keeps the `flop7` CLI on your system PATH. Updates flow through `brew upgrade`.

## pipx

```bash
pipx install flop7
```

`pipx` installs Flop 7 into an isolated Python environment and exposes the `flop7` command globally. Recommended if you already use pipx for Python CLIs.

## pip

```bash
pip install flop7
```

Standard install into the current Python environment. Requires Python 3.10 or newer.

## install.sh (release binary)

```bash
curl -fsSL https://raw.githubusercontent.com/benhalladay08/flop7/main/install.sh | sh
```

The shell script downloads the latest pre-built binary from the project's GitHub releases and installs it to `/usr/local/bin` (using `sudo` if needed) or `~/.local/bin` as a fallback.

Supported platforms:

| OS    | Architectures |
| ----- | ------------- |
| macOS | arm64, x86_64 |
| Linux | arm64, x86_64 |

## From source (local development)

If you're contributing to Flop 7, clone the repo and install in editable mode:

```bash
git clone https://github.com/benhalladay08/flop7.git
cd flop7
python -m pip install -e .
```

See [guides/development.md](guides/development.md) for the full development workflow.

## Verify

```bash
flop7 --help
```
