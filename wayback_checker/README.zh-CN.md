# Wayback Checker

一个小工具，用于扫描 `.mdx` 文件目录并补全缺失的 Wayback Machine 归档链接。

对于 frontmatter 中 `archiveURL` 为空但 `originURL` 非空的 `.mdx` 文件，脚本会查询
[Wayback Machine 可用性 API](https://archive.org/wayback/available)，
并将最近的可用快照 URL 写回文件。

## 功能

- 递归查找指定目录下的所有 `.mdx` 文件。
- 读取并更新 frontmatter 中的 `archiveURL` / `originURL` 字段。
- 仅处理 `archiveURL` 为空且已设置 `originURL` 的文件。
- 支持 HTTP、HTTPS 和 SOCKS5 代理。
- 每次 API 请求之间加入 3.5–6.5 秒的随机延迟，礼貌访问。

## 环境要求

- Python 3.8+
- `requirements.txt` 中的依赖：
  - `requests`
  - `pysocks`（用于 SOCKS 代理）
  - `python-dotenv`

安装依赖：

```bash
pip install -r requirements.txt
```

## 配置

复制示例环境文件并按需修改：

```bash
cp .env.example .env
```

### 配置项

| 变量          | 默认值   | 说明 |
| ------------- | -------- | ---- |
| `CONTENT_DIR` | `news`   | 待扫描的 `.mdx` 文件所在目录。 |
| `PROXIES`     | *(空)*   | 同时用于 HTTP 和 HTTPS 请求的代理 URL。支持 `http://`、`https://` 和 `socks5://`。留空则禁用代理。 |

`.env` 示例：

```dotenv
CONTENT_DIR=news
PROXIES=http://127.0.0.1:23004
```

## 使用

在任意位置运行脚本即可；路径相对于当前工作目录解析：

```bash
python update_archive.py
```

脚本会为每个检查、更新的文件打印进度。没有可用快照的文件将保持不变。

## 工作原理

1. 从 `.env` 加载配置。
2. 递归匹配 `CONTENT_DIR/**/*.mdx`。
3. 从每个文件的 frontmatter 中提取 `archiveURL` 和 `originURL`。
4. 如果 `archiveURL` 为空且存在 `originURL`，则调用 Wayback API。
5. 用返回的快照 URL 替换空的 `archiveURL`。

## 说明

- Wayback API 有速率限制，内置延迟有助于避免被限流。
- 如果文件缺少 `archiveURL` 或 `originURL` 字段，将被跳过。
- 如果你的网络无法直接访问该 API，请使用代理。
