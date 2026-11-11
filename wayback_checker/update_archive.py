import os
import time
import random
import re
from pathlib import Path
import requests

# 根目录设置
NEWS_DIR = Path("news")
API_URL = "https://archive.org/wayback/available"

# 推荐：使用 SOCKS5 代理（需要先在 Xray 里配置一个 protocol 为 socks 的入站，例如端口 23005）
# 如果您改回了支持 HTTP 代理的通用端口，可将 socks5:// 改回 http://
PROXIES = {
    'http': 'http://127.0.0.1:23004',
    'https': 'http://127.0.0.1:23004',
}

# 如果不需要代理，请取消下面这行的注释并注释掉上面的 PROXIES
# PROXIES = None

def check_wayback(url):
    """请求 Wayback Machine API 获取最近的可用归档链接"""
    try:
        params = {'url': url}
        response = requests.get(API_URL, params=params, proxies=PROXIES, timeout=15)
        if response.status_code == 200:
            data = response.json()
            closest = data.get("archived_snapshots", {}).get("closest")
            if closest and closest.get("available"):
                return closest.get("url")
    except Exception as e:
        print(f"  -> 请求 Wayback API 发生异常 ({url}): {e}")
    return None

def process_mdx_files():
    if not NEWS_DIR.exists():
        print(f"错误: 找不到目录 '{NEWS_DIR}'。")
        return

    # 递归查找所有 .mdx 文件
    mdx_files = list(NEWS_DIR.glob("**/*.mdx"))
    print(f"共找到 {len(mdx_files)} 个 .mdx 文件。\n")

    for i, file_path in enumerate(mdx_files):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"读取文件错误 {file_path}: {e}")
            continue

        # 使用正则匹配 frontmatter 中的 archiveURL 和 originURL
        archive_match = re.search(r'^archiveURL:\s*"(.*?)"', content, re.MULTILINE)
        origin_match = re.search(r'^originURL:\s*"(.*?)"', content, re.MULTILINE)

        if not archive_match or not origin_match:
            continue

        current_archive = archive_match.group(1)
        origin_url = origin_match.group(1)

        # 仅当 archiveURL 为空且 origin_url 存在时进行处理
        if not current_archive and origin_url:
            print(f"[{i+1}/{len(mdx_files)}] 正在检查: {origin_url}")
            
            archive_url = check_wayback(origin_url)
            if archive_url:
                print(f"  -> 找到归档链接: {archive_url}")
                # 替换文件中的空 archiveURL
                new_content = content.replace(f'archiveURL: "{current_archive}"', f'archiveURL: "{archive_url}"', 1)
                file_path.write_text(new_content, encoding="utf-8")
                print(f"  -> 已成功更新文件: {file_path}")
            else:
                print("  -> 未找到可用的历史归档快照。")

            # 在请求之间加入 3.5 到 6.5 秒的随机延迟，礼貌访问 API
            if i < len(mdx_files) - 1:
                delay = random.uniform(3.5, 6.5)
                print(f"等待 {delay:.2f} 秒后继续...\n")
                time.sleep(delay)

if __name__ == "__main__":
    process_mdx_files()
    print("\n所有文件处理完毕！")