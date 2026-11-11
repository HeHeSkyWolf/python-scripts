# Image Renamer

[English](README.md)

单文件 Python 脚本，按 EXIF 日期重命名图片文件（支持 WSL）。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用

```bash
python image_renamer.py /path/to/images
python image_renamer.py /mnt/c/Users/John/Pictures -r -p "vacation_" --dry-run
python image_renamer.py . --extensions .jpg,.png --no-exif -s "_backup"
```

## 参数说明

| 参数 | 说明 |
| ---- | ---- |
| `directory` | 包含待重命名图片的目录（必填）。 |
| `-r`, `--recursive` | 递归处理子目录。 |
| `--no-exif` | 使用文件修改时间而不是 EXIF 日期。 |
| `-p`, `--prefix` | 新文件名的前缀。 |
| `-s`, `--suffix` | 新文件名的后缀。 |
| `--dry-run` | 仅预览重命名结果，不做实际修改。 |
| `--extensions` | 逗号分隔的扩展名，例如 `.jpg,.png`。 |

## 要点

- **依赖**：仅 `pillow>=12.3.0`
- **EXIF 优先级**：`DateTimeOriginal` → `DateTimeDigitized` → `DateTime` → 文件修改时间
- **WSL 检测**：以 `/mnt/` 或 `//wsl/` 开头的路径会显示对应的 Windows 路径
- **安全重命名**：使用 `os.rename`；会捕获跨设备错误，但不会回退到复制/`shutil`
- **试运行**：随时可用 `--dry-run` 预览；不带 `--dry-run` 才会真正重命名
- **Windows 安全文件名**：移除 `<>:"/\\|?*` 以及首尾空格和点
- **重名处理**：目标文件已存在时追加 `_2`、`_3` 等后缀
- **无测试、无 lint、无 CI** —— 直接运行脚本即可
