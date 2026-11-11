# Directory Structure Printer

[English](README.md)

一个轻量级 Python 脚本，可将任意目录的树状结构打印到终端，或保存为文本文件。

## 功能

- 以树状形式打印目录和文件，并带有分支连接符（`├──`、`└──`、`│`）
- 条目按字母顺序排序（目录优先）
- 忽略由工具管理的目录（无法自行更改其结构），如 `.git`、`node_modules`、虚拟环境和缓存 —— 可通过 `--show-ignored` 显示
- 使用 `-o`/`--output` 将输出保存为 `.txt` 文件
- 在 WSL 中运行时，自动将 Windows 路径（例如 `C:\Users\foo`）转换为 WSL 路径（例如 `/mnt/c/Users/foo`）
- 仅使用 Python 标准库 —— 无第三方依赖

## 环境要求

- Python 3.8+

## 安装

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 3. 安装依赖（无需任何依赖，仅为保持环境一致）
pip install -r requirements.txt
```

## 使用

```bash
# 打印当前目录结构
python dir_tree.py

# 打印指定目录
python dir_tree.py /path/to/folder

# 从 WSL 传入 Windows 路径会自动转换为 /mnt/c/...
python dir_tree.py "C:\Users\brian\Desktop"

# 保存到文本文件
python dir_tree.py /path/to/folder -o structure.txt

# 同时包含由工具管理的目录（例如 .git、node_modules）
python dir_tree.py --show-ignored
```

## 输出示例

```text
project/
├── src/
│   ├── main.py
│   └── utils.py
├── tests/
│   └── test_main.py
└── README.md
```

## 要点

| 项目 | 说明 |
| ---- | ---- |
| 语言 | Python 3.8+（仅标准库） |
| 依赖 | 无（`requirements.txt` 为空） |
| 默认目标 | 当前目录（`.`） |
| 命令行参数 | `directory`（位置参数）、`-o`/`--output`、`--show-ignored` |
| 输出 | 终端或 UTF-8 文本文件 |
| Windows 路径 | 在 WSL 中运行时自动转换为 WSL 路径 |
