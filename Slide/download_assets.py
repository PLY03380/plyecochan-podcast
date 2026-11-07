#!/usr/bin/env python3
"""
Download images for YouTube Shorts from CSV keyword files.
Uses Unsplash API (public, no key required for basic usage) with Pixabay fallback.
"""

import csv
import os
import sys
import time
import requests
from pathlib import Path
from tqdm import tqdm
from urllib.parse import quote_plus

# Configuration
CSV_FILES = [
    ("tier1_keywords_complete.csv", "tier1"),
    ("tier2_keywords_complete.csv", "tier2"),
    ("tier3_keywords_complete.csv", "tier3"),
    ("trend2026_keywords_complete.csv", "trend2026"),
    ("emotional_keywords_complete.csv", "emotional"),
]

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
TIMEOUT = 15
UNSPLASH_SEARCH_URL = "https://unsplash.com/napi/search/photos"
PIXABAY_SEARCH_URL = "https://pixabay.com/api/"

# Pixabay API key (optional - get free key at https://pixabay.com/api/docs/)
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "57829882-141429e0875fac4f38ecfdc6b")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def ensure_dirs():
    """Create image directories."""
    for _, folder in CSV_FILES:
        (IMAGES_DIR / folder).mkdir(parents=True, exist_ok=True)
    (IMAGES_DIR / "emotional").mkdir(parents=True, exist_ok=True)


def read_csv(csv_path):
    """Read CSV and return list of dicts for downloadable rows."""
    results = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_type = row.get("Type", "").strip().lower()
            # Accept both "Image Libre" and "Cartoon SVG" (for emotional tier)
            if row_type in ("image libre", "cartoon svg"):
                # For emotional CSV, create a search term from concept
                if not row.get("Terme Recherche"):
                    row["Terme Recherche"] = row.get("Concept EN", "").strip()
                if not row.get("Nom Fichier"):
                    # Generate filename from concept
                    concept = row.get("Concept EN", "").strip().lower().replace(" ", "_")
                    row["Nom Fichier"] = f"emo_{concept}.jpg"
                results.append(row)
    return results


def search_unsplash(query, per_page=5):
    """Search Unsplash for photos matching query."""
    params = {
        "query": query,
        "per_page": per_page,
        "order_by": "relevant",
    }
    try:
        resp = requests.get(UNSPLASH_SEARCH_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("results", [])
    except Exception as e:
        print(f"  [Unsplash] Error for '{query}': {e}")
    return []


def search_pixabay(query, per_page=5):
    """Search Pixabay for images matching query."""
    if not PIXABAY_API_KEY:
        return []
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "image_type": "photo",
        "per_page": per_page,
        "safesearch": "true",
        "order": "popular",
    }
    try:
        resp = requests.get(PIXABAY_SEARCH_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("hits", [])
    except Exception as e:
        print(f"  [Pixabay] Error for '{query}': {e}")
    return []


def download_image(url, dest_path):
    """Download image from URL to destination."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        if resp.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"  Download failed: {e}")
    return False


def get_best_image_url(results, source):
    """Extract best image URL from search results."""
    if source == "unsplash":
        for r in results:
            urls = r.get("urls", {})
            # Prefer regular size, fallback to small
            return urls.get("regular") or urls.get("small") or urls.get("thumb")
    elif source == "pixabay":
        for r in results:
            return r.get("largeImageURL") or r.get("webformatURL") or r.get("previewURL")
    return None


def process_csv(csv_file, folder):
    """Process a single CSV file."""
    csv_path = BASE_DIR / csv_file
    if not csv_path.exists():
        print(f"  [SKIP] {csv_file} not found")
        return 0, 0

    rows = read_csv(csv_path)
    if not rows:
        print(f"  [SKIP] No 'Image Libre' rows in {csv_file}")
        return 0, 0

    print(f"\n[DIR] Processing {csv_file} -> {folder}/ ({len(rows)} images)")
    success = 0
    failed = 0

    for row in tqdm(rows, desc=f"  {folder}", unit="img"):
        filename = row.get("Nom Fichier", "").strip()
        if not filename:
            failed += 1
            continue

        dest = IMAGES_DIR / folder / filename
        if dest.exists():
            success += 1
            continue

        search_term = row.get("Terme Recherche", "").strip()
        if not search_term:
            # Fallback to Concept EN
            search_term = row.get("Concept EN", "").strip()

        if not search_term:
            failed += 1
            continue

        # Try Unsplash first
        results = search_unsplash(search_term)
        img_url = get_best_image_url(results, "unsplash")

        # Fallback to Pixabay
        if not img_url and PIXABAY_API_KEY:
            results = search_pixabay(search_term)
            img_url = get_best_image_url(results, "pixabay")

        if img_url:
            if download_image(img_url, dest):
                success += 1
            else:
                failed += 1
        else:
            print(f"  [MISS] No image found for: {search_term}")
            failed += 1

        time.sleep(0.3)  # Rate limiting

    return success, failed


def main():
    print("=" * 60)
    print("YouTube Shorts Image Downloader")
    print("=" * 60)

    ensure_dirs()

    total_success = 0
    total_failed = 0

    for csv_file, folder in CSV_FILES:
        s, f = process_csv(csv_file, folder)
        total_success += s
        total_failed += f
        print(f"  [OK] {s} downloaded, [FAIL] {f} failed")

    print("\n" + "=" * 60)
    print(f"[DONE] COMPLETE: {total_success} images downloaded, {total_failed} failed")
    print(f"[DIR] Images saved to: {IMAGES_DIR}")
    print("=" * 60)

    # Show structure
    for _, folder in CSV_FILES:
        count = len(list((IMAGES_DIR / folder).glob("*")))
        print(f"  {folder}/: {count} files")


if __name__ == "__main__":
    main()