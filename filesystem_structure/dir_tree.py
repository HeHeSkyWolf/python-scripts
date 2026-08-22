#!/usr/bin/env python3
"""Print the directory tree of a given path to the terminal or a file."""

import argparse
import os
import re
import sys
from pathlib import Path


# Directories whose structure is managed by tools, not the user, so they are
# skipped by default (e.g. version control, dependencies, caches).
IGNORED_DIRS = frozenset(
    {
        ".git", ".hg", ".svn",  # version control
        ".venv", "venv", ".env",  # virtual environments
        "node_modules",  # package dependencies
        "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",  # caches
    }
)


def to_wsl_path(path: str) -> Path:
    """
    Convert a Windows-style path (e.g. ``C:\\Users\\foo``) to a WSL path (``/mnt/c/Users/foo``).
    
    @param path: The Windows-style path to convert.
    @return: The WSL path corresponding to the given Windows-style path.
    """
    path = path.strip()
    drive = re.match(r"^([A-Za-z]):[\\/]?(.*)$", path)
    if drive and os.name != "nt":
        letter, rest = drive.groups()
        return Path(f"/mnt/{letter.lower()}/{rest.replace(chr(92), '/')}")
    return Path(path)


def build_tree(root: Path, show_ignored: bool = False) -> list[str]:
    """
    Return a list of lines representing the tree of `root`.

    @param root: The root path to build the tree from.
    @param show_ignored: Whether to include ignored files and directories in the tree.
    @return: A list of lines representing the tree of the given directory. Each line is a string \
        with the format ``<path> [<type>]`` where `<path>`` is the path to the file or directory \
        and ``<type>`` is either ``file`` or ``dir``.
    """
    root = Path(root).resolve()
    if not root.exists():
        sys.exit(f"Error: path does not exist: {root}")
    if not root.is_dir():
        sys.exit(f"Error: not a directory: {root}")

    lines = [f"{root.name}/"]
    children = _children(root, show_ignored)
    for i, entry in enumerate(children):
        lines.extend(_walk(entry, "", is_last=i == len(children) - 1, show_ignored=show_ignored))
    return lines


def _children(path: Path, show_ignored: bool = False) -> list[Path]:
    """
    Return a sorted list of children paths for the given directory.
    If `show_ignored` is True, include ignored directories; otherwise, exclude them.

    @param path: Path object representing the directory to be processed.
    @param show_ignored: Boolean indicating whether to include ignored directories.
    @return: List of Path objects representing the children paths.
    """
    return [
        p
        for p in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        if show_ignored or not (p.is_dir() and p.name in IGNORED_DIRS)
    ]


def _walk(path: Path, prefix: str, is_last: bool = True, show_ignored: bool = False) -> list[str]:
    """
    Recursively walk through the directory tree starting from `path`, building a list of lines 
    representing the tree structure.
    The `prefix` parameter helps in maintaining the visual hierarchy of the tree.
    If `is_last` is True, use '└──' to indicate the last child; otherwise, use '├──'.
    
    @param path: Path object representing the current directory.
    @param prefix: String representing the current level of the tree.
    @param is_last: Boolean indicating whether the current directory is the last child \
        in its parent.
    @param show_ignored: Boolean indicating whether to include ignored directories.
    @return: List of strings representing the lines of the tree structure.
    """
    connector = "└── " if is_last else "├── "
    lines = [f"{prefix}{connector}{path.name}{'/' if path.is_dir() else ''}"]
    if path.is_dir():
        children = _children(path, show_ignored)
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(children):
            lines.extend(_walk(child, child_prefix, i == len(children) - 1, show_ignored))
    return lines


def main() -> None:
    """
    Main function to parse command-line arguments and print or save the directory tree structure.
    """
    parser = argparse.ArgumentParser(
        description="Print the directory structure of a given path."
    )
    parser.add_argument("directory", nargs="?", default=".", \
                        help="Directory to scan (default: current directory)")
    parser.add_argument(
        "-o", "--output", metavar="FILE", \
            help="Write the structure to a text file instead of the terminal"
    )
    parser.add_argument(
        "--show-ignored", action="store_true",
        help="Also include ignored directories such as .git, node_modules, and caches",
    )
    args = parser.parse_args()

    lines = build_tree(to_wsl_path(args.directory), show_ignored=args.show_ignored)

    if args.output:
        Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Structure saved to {args.output}")
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
