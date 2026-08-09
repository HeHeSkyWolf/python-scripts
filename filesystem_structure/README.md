# Directory Structure Printer

A lightweight Python script that prints the tree structure of any directory to the terminal, or saves it to a text file.

## Features

- Prints directories and files as a tree with branch connectors (`├──`, `└──`, `│`)
- Sorts entries alphabetically (directories first)
- Save output to a `.txt` file with `-o`/`--output`
- Uses only the Python standard library — no third-party dependencies

## Requirements

- Python 3.8+

## Setup

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 3. Install dependencies (none required, but keeps env consistent)
pip install -r requirements.txt
```

## Usage

```bash
# Print the current directory structure
python directory_structure.py

# Print a specific directory
python directory_structure.py /path/to/folder

# Save to a text file
python directory_structure.py /path/to/folder -o structure.txt
```

## Example Output

```text
project/
├── src/
│   ├── main.py
│   └── utils.py
├── tests/
│   └── test_main.py
└── README.md
```

## Key Facts

| Item | Detail |
| ------ | -------- |
| Language | Python 3.8+ (stdlib only) |
| Dependencies | None (`requirements.txt` is empty) |
| Default target | Current directory (`.` ) |
| CLI flags | `directory` (positional), `-o`/`--output` |
| Output | Terminal or UTF-8 text file |
