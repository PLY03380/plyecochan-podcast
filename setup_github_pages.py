#!/usr/bin/env python3
"""setup_github_pages.py — Prepare les fichiers pour GitHub Pages (podcast).

Cree la structure de fichiers necessaire pour heberger le podcast sur GitHub Pages.
Les fichiers seront dans le dossier 'docs/' qui sera pousse sur GitHub.

Usage:
    python setup_github_pages.py
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("github_pages")

ROOT = Path(__file__).resolve().parent
PODCAST_DIR = ROOT / "output" / "podcast"
GITHUB_PAGES_DIR = ROOT / "docs"

# Base URL for GitHub Pages (to be updated after repo creation)
BASE_URL = "https://PLY03380.github.io/plyecochan-podcast"


def setup():
    """Prepare la structure GitHub Pages."""
    GITHUB_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    (GITHUB_PAGES_DIR / "episodes").mkdir(parents=True, exist_ok=True)

    # Copier les fichiers MP3
    mp3_files = list(PODCAST_DIR.glob("*.mp3"))
    for mp3 in mp3_files:
        dest = GITHUB_PAGES_DIR / "episodes" / mp3.name
        import shutil
        shutil.copy2(mp3, dest)
        log.info(f"Copie: {mp3.name} -> docs/episodes/")

    # Generer le flux RSS avec les bonnes URLs
    from pipeline.podcast import generate_rss
    rss_path = generate_rss(audio_base_url=f"{BASE_URL}/episodes")
    if rss_path:
        import shutil
        shutil.copy2(rss_path, GITHUB_PAGES_DIR / "feed.xml")
        log.info(f"RSS copie: feed.xml")

    # Creer un index.html simple
    index_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>PlyChan Podcast</title>
    <meta charset="UTF-8">
</head>
<body>
    <h1>PlyChan Podcast</h1>
    <p>Analyses economiques quotidiennes en 3 langues (FR/EN/ES).</p>
    <p><a href="feed.xml">Flux RSS</a></p>
    <p><a href="https://youtube.com/@PlyChan">Chaine YouTube</a></p>
</body>
</html>"""
    (GITHUB_PAGES_DIR / "index.html").write_text(index_html, encoding="utf-8")

    # Creer .nojekyll pour desactiver Jekyll
    (GITHUB_PAGES_DIR / ".nojekyll").write_text("", encoding="utf-8")

    log.info("=== STRUCTURE GITHUB PAGES PRETE ===")
    log.info(f"Dossier: {GITHUB_PAGES_DIR}")
    log.info(f"MP3: {len(mp3_files)} fichiers")
    log.info(f"RSS: {GITHUB_PAGES_DIR / 'feed.xml'}")
    log.info("")
    log.info("Prochaines etapes:")
    log.info("1. git add docs/")
    log.info("2. git commit -m 'Add podcast files for GitHub Pages'")
    log.info("3. git push origin master")
    log.info("4. Aller sur GitHub → Settings → Pages → Source: Deploy from branch → master → /docs")
    log.info("5. Soumettre le RSS a Spotify, Apple, Google, etc.")
    log.info(f"   URL RSS: {BASE_URL}/feed.xml")

    return str(GITHUB_PAGES_DIR)


if __name__ == "__main__":
    setup()