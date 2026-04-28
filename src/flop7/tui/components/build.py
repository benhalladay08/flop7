"""
Reads a .txt file containing ASCII art numbers with # comments.
Wraps each art piece in a box-drawing border, centered, and exports
to individual .txt files named after the comment.
"""

import sys
from pathlib import Path

# Border dimensions (inner width between the ║ characters)
INNER_WIDTH = 15
INNER_HEIGHT = 10  # rows between top and bottom border
ART_HEIGHT = 5

DEFAULT_INPUT = Path(__file__).with_name("numbers.txt")
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("cards")


def parse_entries(filepath: str | Path) -> list[tuple[str, list[str]]]:
    """Parse the input file into (name, lines) pairs."""
    entries = []
    current_name = None
    current_lines = []

    for line in Path(filepath).read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            if current_name is not None:
                entries.append((current_name, current_lines))
            current_name = line[1:].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        entries.append((current_name, current_lines))

    return entries


def wrap_in_border(name: str, art_lines: list[str]) -> str:
    """Center the art inside the box-drawing border."""
    art_lines = list(art_lines)
    while art_lines and art_lines[-1].strip() == "":
        art_lines.pop()

    if len(art_lines) != ART_HEIGHT:
        raise ValueError(
            f"Entry '{name}': expected {ART_HEIGHT} lines of art, got {len(art_lines)}"
        )

    max_width = max(len(line) for line in art_lines)

    if max_width > INNER_WIDTH:
        raise ValueError(
            f"Entry '{name}': art width ({max_width}) exceeds "
            f"border inner width ({INNER_WIDTH})"
        )

    pad_top = (INNER_HEIGHT - ART_HEIGHT) // 2
    pad_bottom = INNER_HEIGHT - ART_HEIGHT - pad_top

    rows = []
    rows.append("╔" + "═" * INNER_WIDTH + "╗")

    for _ in range(pad_top):
        rows.append("║" + " " * INNER_WIDTH + "║")

    for line in art_lines:
        total_pad = INNER_WIDTH - len(line)
        left = total_pad // 2
        right = total_pad - left
        rows.append("║" + " " * left + line + " " * right + "║")

    for _ in range(pad_bottom):
        rows.append("║" + " " * INNER_WIDTH + "║")

    rows.append("╚" + "═" * INNER_WIDTH + "╝")

    return "\n".join(rows)


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    entries = parse_entries(input_path)

    if not entries:
        print("No entries found in the input file.")
        sys.exit(1)

    for name, lines in entries:
        bordered = wrap_in_border(name, lines)
        out_path = output_dir / f"{name}.txt"
        out_path.write_text(bordered + "\n", encoding="utf-8")
        print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
