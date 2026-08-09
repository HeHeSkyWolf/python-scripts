#!/usr/bin/env python3
"""Print the directory tree of a given path to the terminal or a file."""

import argparse
import sys
from pathlib import Path


def build_tree(root: Path) -> list[str]:
    """Return a list of lines representing the tree of ``root``."""
    root = Path(root).resolve()
    if not root.exists():
        sys.exit(f"Error: path does not exist: {root}")
    if not root.is_dir():
        sys.exit(f"Error: not a directory: {root}")

    lines = [f"{root.name}/"]
    for entry in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        lines.extend(_walk(entry, ""))
    return lines


def _walk(path: Path, prefix: str, is_last: bool = True) -> list[str]:
    connector = "└── " if is_last else "├── "
    lines = [f"{prefix}{connector}{path.name}{'/' if path.is_dir() else ''}"]
    if path.is_dir():
        children = sorted(
            path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
        )
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(children):
            lines.extend(_walk(child, child_prefix, i == len(children) - 1))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print the directory structure of a given path."
    )
    parser.add_argument("directory", nargs="?", default=".", help="Directory to scan (default: current directory)")
    parser.add_argument(
        "-o", "--output", metavar="FILE", help="Write the structure to a text file instead of the terminal"
    )
    args = parser.parse_args()

    lines = build_tree(Path(args.directory))

    if args.output:
        Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Structure saved to {args.output}")
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
