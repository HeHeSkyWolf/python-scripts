import os
import time
import random
import re
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

# Root directory setting
CONTENT_DIR = Path(os.getenv("CONTENT_DIR", "news"))
API_URL = "https://archive.org/wayback/available"

# Recommended: use a SOCKS5 proxy (configure an inbound with protocol socks in Xray first, e.g. port 23005)
# If you switch back to a general port that supports HTTP proxies, change socks5:// back to http://
# Set PROXIES in .env; leave it empty to disable the proxy
PROXY_URL = os.getenv("PROXIES", "").strip()
PROXIES = {'http': PROXY_URL, 'https': PROXY_URL} if PROXY_URL else None

def check_wayback(url):
    """Query the Wayback Machine API for the most recent available archive link.

    Args:
        url: The original URL to look up an archived snapshot for.

    Returns:
        The URL of the most recent available archived snapshot, or None if not
        found or the request fails.
    """
    try:
        params = {'url': url}
        response = requests.get(API_URL, params=params, proxies=PROXIES, timeout=15)
        if response.status_code == 200:
            data = response.json()
            closest = data.get("archived_snapshots", {}).get("closest")
            if closest and closest.get("available"):
                return closest.get("url")
    except Exception as e:
        print(f"  -> Error while requesting Wayback API ({url}): {e}")
    return None

def process_mdx_files():
    """Recursively scan .mdx files under CONTENT_DIR and fill in empty archiveURL.

    Only processes files whose frontmatter has an empty archiveURL but a
    non-empty originURL, querying the Wayback Machine API for the most recent
    archived snapshot and writing it back to the file.
    """
    if not CONTENT_DIR.exists():
        print(f"Error: directory '{CONTENT_DIR}' not found.")
        return

    # Recursively find all .mdx files
    mdx_files = list(CONTENT_DIR.glob("**/*.mdx"))
    print(f"Found {len(mdx_files)} .mdx files in total.\n")

    for i, file_path in enumerate(mdx_files):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            continue

        # Match archiveURL and originURL in frontmatter using regex
        archive_match = re.search(r'^archiveURL:\s*"(.*?)"', content, re.MULTILINE)
        origin_match = re.search(r'^originURL:\s*"(.*?)"', content, re.MULTILINE)

        if not archive_match or not origin_match:
            continue

        current_archive = archive_match.group(1)
        origin_url = origin_match.group(1)

        # Only process when archiveURL is empty and origin_url exists
        if not current_archive and origin_url:
            print(f"[{i+1}/{len(mdx_files)}] Checking: {origin_url}")
            
            archive_url = check_wayback(origin_url)
            if archive_url:
                print(f"  -> Found archive link: {archive_url}")
                # Replace the empty archiveURL in the file
                new_content = content.replace(f'archiveURL: "{current_archive}"', f'archiveURL: "{archive_url}"', 1)
                file_path.write_text(new_content, encoding="utf-8")
                print(f"  -> Successfully updated file: {file_path}")
            else:
                print("  -> No available historical archive snapshot found.")

            # Add a random 3.5 to 6.5 second delay between requests to be polite to the API
            if i < len(mdx_files) - 1:
                delay = random.uniform(3.5, 6.5)
                print(f"Waiting {delay:.2f} seconds before continuing...\n")
                time.sleep(delay)

if __name__ == "__main__":
    process_mdx_files()
    print("\nAll files processed!")
