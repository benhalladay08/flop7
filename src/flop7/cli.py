import argparse

from flop7 import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="flop7",
        description=(
            "Flop 7 — an unofficial terminal Flip 7 emulator. "
            "Run `flop7` with no arguments to launch the terminal UI. "
            "See https://github.com/benhalladay08/flop7 for docs."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"flop7 {__version__}",
    )
    parser.parse_args()

    from flop7.app.orchestrator import App

    App().run()
