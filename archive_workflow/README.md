# Archive Workflow

[中文文档](README.zh-CN.md)

Two scripts that turn a folder of downloaded 7k7k news pages into clean MDX
articles:

- `organize.py` sorts downloaded files into a `raw/contents` + `raw/images`
  archive tree.
- `convert.py` parses each archived article and writes an `.mdx` file with
  localized image paths and YAML front matter.

## Overview

The workflow has two steps that must be run in order:

1. **Organize** the raw files you archived from the web with `organize.py`.
2. **Convert** the organized content into MDX files with `convert.py`.

```bash
python organize.py --dry-run   # preview the file moves
python organize.py             # organize the raw archived files
python convert.py --root raw   # convert the content into MDX
```

## Requirements

- Python 3.10+
- Dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Workflow

Run both scripts from the directory that contains your downloaded files.

### 1. Organize downloads

Place all downloaded `.html`/`.txt` pages and images in the working directory
(subdirectories are fine), then run:

```bash
python organize.py --dry-run   # preview
python organize.py             # move files
```

Files are moved by extension while keeping their relative paths:

- `.html`, `.txt` → `raw/contents/<relative path>`
- image files → `raw/images/<relative path>`

Existing destinations are never overwritten. The `raw`, `contents`, `images`,
`mdx`, `node_modules` directories, dot-directories, and `requirements.txt` are
skipped.

### 2. Convert to MDX

```bash
python convert.py --root raw
```

This reads every `raw/contents/<date>/<article-id>/index.html` and writes:

- `raw/mdx/<date>/<article-id>.mdx`
- `raw/mdx/news.css` (only when styles are generated)

## Source layout

```text
raw/
├── contents/
│   └── 20240101/
│       └── 123456/
│           ├── index.html
│           ├── source-url.txt     # optional
│           └── archive-url.txt    # optional
├── images/
│   └── 20240101/
│       └── 123456/
│           ├── 1.jpg
│           └── 2.jpg
└── mdx/
    └── 20240101/
        └── 123456.mdx
```

Each article directory may contain two optional sidecar files:

| File              | Purpose |
| ----------------- | ------- |
| `source-url.txt`  | Value written to `originURL`. Defaults to `https://news.7k7k.com/content/<date>/<article-id>.html`. |
| `archive-url.txt` | Value written to `archiveURL`. Can be overridden with `--archive-url`. |

## convert.py options

| Option | Description |
| ------ | ----------- |
| `--root PATH` | Archive root containing `contents` and `images` (default: current directory). |
| `--out PATH` | Output folder relative to `--root` (default: `mdx`). |
| `--clean` | Remove the output folder before writing. |
| `--styled`, `--keep-styles` | Preserve the original markup and inline CSS as generated classes. |
| `--rich` | Keep only bold text and text colors on top of the plain output. |
| `--date YYYYMMDD` | Only write articles from this date folder. |
| `--id ID` | Only write this article id. |
| `--relative-images` | Emit `../../../../../assets/...` instead of the default `/assets/...`. |
| `--force` | Overwrite existing `.mdx` files (otherwise they are skipped). |
| `--archive-url URL` | Fill `archiveURL` for the selected article(s). |
| `--line-ending {crlf,lf}` | Output line ending (default: `crlf`). |
| `--dry-run` | Print what would be written without writing anything. |

`--styled` and `--rich` cannot be used together.

### Output modes

- **plain** (default): keep text, links, images, and paragraph structure.
- **`--rich`**: additionally keep bold text and text colors.
- **`--styled`**: keep the original HTML structure, converting inline styles
  into reusable `news-*` classes in `news.css`.

### Front matter

Each generated file starts with:

```yaml
---
title: "..."
category: "..."
publishDate: "..."
editor: "..."
prev: "..."
prevTitle: "..."
next: "..."
nextTitle: "..."
originURL: "..."
archiveURL: "..."
---
```

## Notes

- `convert.py` only rewrites image references; it does not copy images into the
  public `assets/` folder. Serve or copy `raw/images` there yourself.
- Links are rewritten from `href` to `data-original-url` so they stay inert.
- MDX braces (`{` and `}`) in content are escaped automatically.
- Run with `--dry-run` first to preview any changes.
