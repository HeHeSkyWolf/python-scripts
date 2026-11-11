# Wayback Checker

[中文文档](README.zh-CN.md)

A small utility that scans a directory of `.mdx` files and fills in missing
Wayback Machine archive links.

For every `.mdx` file whose frontmatter has an empty `archiveURL` but a
non-empty `originURL`, the script queries the
[Wayback Machine availability API](https://archive.org/wayback/available)
and writes the closest available snapshot URL back into the file.

## Features

- Recursively finds all `.mdx` files under a configurable directory.
- Reads and updates `archiveURL` / `originURL` frontmatter fields.
- Only touches files where `archiveURL` is empty and `originURL` is set.
- Supports HTTP, HTTPS, and SOCKS5 proxies.
- Adds a random 3.5–6.5 second delay between API requests to be polite.

## Requirements

- Python 3.8+
- Dependencies from `requirements.txt`:
  - `requests`
  - `pysocks` (for SOCKS proxies)
  - `python-dotenv`

Install them with:

```bash
pip install -r requirements.txt
```

## Setup

Copy the example environment file and adjust it as needed:

```bash
cp .env.example .env
```

### Configuration

| Variable      | Default | Description |
| ------------- | ------- | ----------- |
| `CONTENT_DIR` | `news`  | Directory containing the `.mdx` files to scan. |
| `PROXIES`     | *(empty)* | Proxy URL applied to both HTTP and HTTPS requests. Supports `http://`, `https://`, and `socks5://`. Leave empty to disable the proxy. |

Example `.env`:

```dotenv
CONTENT_DIR=news
PROXIES=http://127.0.0.1:23004
```

## Usage

Run the script from anywhere; paths are resolved relative to the current
working directory:

```bash
python update_archive.py
```

The script prints progress for each file it checks and updates. Files with no
available snapshot are left unchanged.

## How It Works

1. Loads configuration from `.env`.
2. Recursively globs `CONTENT_DIR/**/*.mdx`.
3. Extracts `archiveURL` and `originURL` from each file's frontmatter.
4. If `archiveURL` is empty and `originURL` is present, calls the Wayback API.
5. Replaces the empty `archiveURL` with the returned snapshot URL.

## Notes

- The Wayback API is rate-limited; the built-in delay helps avoid throttling.
- If a file has no `archiveURL` or `originURL` field, it is skipped.
- Use a proxy if the API is not directly reachable from your network.
