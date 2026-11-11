# Archive Workflow

[English](README.md)

两个脚本，用于将下载的 7k7k 新闻页面整理为干净的 MDX 文章：

- `organize.py`：将下载的文件整理到 `raw/contents` 与 `raw/images` 归档目录。
- `convert.py`：解析每个归档文章，并生成带有本地化图片路径和 YAML front
  matter 的 `.mdx` 文件。

## 流程概览

整个工作流程包含两个步骤，必须按顺序执行：

1. **整理**：使用 `organize.py` 整理从网上下载归档的原始文件。
2. **转换**：使用 `convert.py` 将整理后的内容转换为 MDX 文件。

```bash
python organize.py --dry-run   # 预览文件移动
python organize.py             # 整理归档的原始文件
python convert.py --root raw   # 将内容转换为 MDX
```

## 环境要求

- Python 3.10+
- `requirements.txt` 中的依赖：

```bash
pip install -r requirements.txt
```

## 工作流程

请在存放下载文件的目录中运行这两个脚本。

### 1. 整理下载文件

将下载的 `.html`/`.txt` 页面和图片放在当前工作目录中（可以位于子目录），然后运行：

```bash
python organize.py --dry-run   # 预览
python organize.py             # 实际移动
```

脚本按扩展名移动文件，并保留其相对路径：

- `.html`、`.txt` → `raw/contents/<相对路径>`
- 图片文件 → `raw/images/<相对路径>`

目标位置已存在时不会覆盖。脚本会跳过 `raw`、`contents`、`images`、`mdx`、
`node_modules` 目录、以点开头的目录以及 `requirements.txt`。

### 2. 转换为 MDX

```bash
python convert.py --root raw
```

脚本会读取每个 `raw/contents/<日期>/<文章 ID>/index.html`，并生成：

- `raw/mdx/<日期>/<文章 ID>.mdx`
- `raw/mdx/news.css`（仅在生成样式时创建）

## 源目录结构

```text
raw/
├── contents/
│   └── 20240101/
│       └── 123456/
│           ├── index.html
│           ├── source-url.txt     # 可选
│           └── archive-url.txt    # 可选
├── images/
│   └── 20240101/
│       └── 123456/
│           ├── 1.jpg
│           └── 2.jpg
└── mdx/
    └── 20240101/
        └── 123456.mdx
```

每个文章目录可以包含两个可选的附属文件：

| 文件              | 用途 |
| ----------------- | ---- |
| `source-url.txt`  | 写入 `originURL` 的值。默认为 `https://news.7k7k.com/content/<日期>/<文章 ID>.html`。 |
| `archive-url.txt` | 写入 `archiveURL` 的值。可通过 `--archive-url` 覆盖。 |

## convert.py 选项

| 选项 | 说明 |
| ---- | ---- |
| `--root PATH` | 包含 `contents` 和 `images` 的归档根目录（默认：当前目录）。 |
| `--out PATH` | 相对于 `--root` 的输出目录（默认：`mdx`）。 |
| `--clean` | 写入前删除输出目录。 |
| `--styled`、`--keep-styles` | 保留原始标记，并将内联 CSS 转换为生成的 class。 |
| `--rich` | 在纯文本输出的基础上仅保留粗体和文字颜色。 |
| `--date YYYYMMDD` | 仅写入该日期目录下的文章。 |
| `--id ID` | 仅写入指定文章 ID。 |
| `--relative-images` | 输出 `../../../../../assets/...`，而非默认的 `/assets/...`。 |
| `--force` | 覆盖已存在的 `.mdx` 文件（默认跳过）。 |
| `--archive-url URL` | 为选中的文章填入 `archiveURL`。 |
| `--line-ending {crlf,lf}` | 输出换行符（默认：`crlf`）。 |
| `--dry-run` | 仅显示将要写入的内容，不实际写入。 |

`--styled` 与 `--rich` 不能同时使用。

### 输出模式

- **plain**（默认）：保留文本、链接、图片和段落结构。
- **`--rich`**：在默认基础上额外保留粗体和文字颜色。
- **`--styled`**：保留原始 HTML 结构，并将内联样式转换为 `news.css` 中可复用的
  `news-*` class。

### Front matter

每个生成的文件都以以下内容开头：

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

## 说明

- `convert.py` 只重写图片引用，不会将图片复制到公开的 `assets/` 目录。请自行将
  `raw/images` 提供或复制到该位置。
- 链接会从 `href` 重写为 `data-original-url`，使其保持非活动状态。
- 内容中的 MDX 花括号（`{` 和 `}`）会自动转义。
- 建议先使用 `--dry-run` 预览所有更改。
