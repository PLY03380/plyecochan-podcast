"""indexing_bing.py — Indexation Bing/DuckDuckGo/Yahoo/Ecosia via IndexNow."""
import json
import logging
import os
from pathlib import Path
from typing import List

log = logging.getLogger("indexing_bing")

try:
    import config
    INDEXNOW_KEY = getattr(config, "INDEXNOW_KEY", "0e70077c2c29424ead5983b9a07cc3f9")
except Exception:
    INDEXNOW_KEY = "0e70077c2c29424ead5983b9a07cc3f9"
BLOG_HOST = "plychaneconomie.blogspot.com"
INDEXNOW_URL = "https://api.indexnow.org/indexnow"


def indexer_bing(url: str) -> bool:
    """Soumet une URL à Bing/DuckDuckGo/Yahoo/Ecosia via IndexNow."""
    import requests
    payload = {
        "host": BLOG_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{BLOG_HOST}/{INDEXNOW_KEY}.txt",
        "urlList": [url],
    }
    try:
        response = requests.post(
            INDEXNOW_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if response.status_code in (200, 202):
            log.info(f"Indexe Bing/DuckDuckGo: {url}")
            return True
        else:
            log.warning(f"Erreur IndexNow {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        log.error(f"Erreur IndexNow: {e}")
        return False


def indexer_bing_plusieurs(urls: List[str]) -> int:
    """Soumet plusieurs URLs en un seul appel (plus efficace)."""
    import requests
    payload = {
        "host": BLOG_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{BLOG_HOST}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    try:
        response = requests.post(
            INDEXNOW_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if response.status_code in (200, 202):
            log.info(f"{len(urls)} URLs indexees sur Bing/DuckDuckGo")
            return len(urls)
        else:
            log.warning(f"Erreur IndexNow {response.status_code}: {response.text[:100]}")
            return 0
    except Exception as e:
        log.error(f"Erreur IndexNow: {e}")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Test
    indexer_bing(f"https://{BLOG_HOST}/")