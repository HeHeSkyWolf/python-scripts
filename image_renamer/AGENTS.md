# AGENTS.md — image_renamer

Single-file Python script that renames image files by EXIF date (with WSL support).

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python image_renamer.py /path/to/images
python image_renamer.py /mnt/c/Users/John/Pictures -r -p "vacation_" --dry-run
python image_renamer.py . --extensions .jpg,.png --no-exif -s "_backup"
```

## Key facts

- **Dependency**: `pillow>=12.3.0` only
- **EXIF priority**: `DateTimeOriginal` → `DateTimeDigitized` → `DateTime` → file mtime
- **WSL detection**: paths starting with `/mnt/` or `//wsl/` get Windows-path display
- **Safe rename**: uses `os.rename`; catches cross-device errors but does NOT fall back to copy/shutil
- **Dry-run**: always available via `--dry-run`; no `--dry-run` is the only way to actually rename
- **Windows-safe filenames**: strips `<>:"/\\|?*` and trailing/leading spaces/dots
- **Duplicate handling**: appends `_2`, `_3`, etc. when target exists
- **No tests, no lint, no CI** — just run the script
