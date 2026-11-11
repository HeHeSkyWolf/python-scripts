"""Utilities for organizing downloaded archive files.

This module moves HTML, text, and image files from the current directory into
a raw archive tree. Content files are placed in ``raw/contents`` and image files
in ``raw/images``, preserving their relative paths so that the converter can
associate each article with its images.
"""

import argparse
import shutil
from pathlib import Path

CONTENT_EXTS = {".html", ".txt"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tif", ".tiff"}

SKIP_DIRS = {"raw", "contents", "images", "mdx", "node_modules"}
SKIP_FILES = {"requirements.txt"}


def main():
    """Move downloaded files into the raw archive tree.

    Scans the current directory recursively, moves HTML and text files into
    ``raw/contents`` and image files into ``raw/images``, and reports how many
    files were moved or skipped. Existing destinations are never overwritten,
    and no files are modified when dry-run mode is enabled.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be moved without moving anything",
    )
    args = parser.parse_args()

    root = Path.cwd()
    raw_dir = root / "raw"
    contents_dir = raw_dir / "contents"
    images_dir = raw_dir / "images"

    moved = 0
    skipped = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue

        # Skip our own output directories, version control, virtualenvs, etc.
        if rel.parts[0] in SKIP_DIRS or rel.parts[0].startswith("."):
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        if path.name.lower() in SKIP_FILES:
            skipped += 1
            continue

        ext = path.suffix.lower()
        if ext in CONTENT_EXTS:
            dest_root = contents_dir
        elif ext in IMAGE_EXTS:
            dest_root = images_dir
        else:
            skipped += 1
            continue

        dest = dest_root / rel
        if dest.exists():
            print(f"SKIP (exists): {rel} -> {dest.relative_to(root)}")
            skipped += 1
            continue

        print(f"MOVE: {rel} -> {dest.relative_to(root)}")
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(dest))
        moved += 1

    print(f"\n{'Would move' if args.dry_run else 'Moved'} {moved} file(s), skipped {skipped}.")


if __name__ == "__main__":
    main()
