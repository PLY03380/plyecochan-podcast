"""podcast_spotify.py — Upload automatique sur Spotify for Creators via Playwright.

Utilise l'automatisation navigateur pour uploader des episodes sur Spotify.
Base sur le principe de sfrbuilds/agentic-podcast.

Prerequis:
    - pip install playwright && playwright install chromium
    - Session Spotify sauvegardee (voir save_spotify_session)

Usage:
    python pipeline/podcast_spotify.py --save-session   # Sauvegarder la session (1 fois)
    python pipeline/podcast_spotify.py --upload 2026-11-09  # Upload les episodes
    python pipeline/podcast_spotify.py --upload-all       # Upload pour aujourd'hui
"""
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("podcast_spotify")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PODCAST_DIR = ROOT / "output" / "podcast"
SESSION_FILE = ROOT / "output" / "spotify_session.json"
SPOTIFY_SHOW_ID = os.getenv("SPOTIFY_SHOW_ID", "")


def save_spotify_session():
    """Sauvegarde la session Spotify (a faire 1 fois, manuellement)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright non installe. pip install playwright && playwright install chromium")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Aller sur Spotify for Creators
        page.goto("https://creators.spotify.com", timeout=30000)
        time.sleep(3)

        print("\n" + "=" * 60)
        print("CONNECTE-TOI A SPOTIFY DANS LE NAVIGATEUR")
        print("Une fois connecte, appuie sur Entree ici")
        print("=" * 60)
        input("Appuie sur Entree apres connexion...")

        # Sauvegarder la session
        context.storage_state(path=str(SESSION_FILE))
        log.info(f"Session sauvegardee: {SESSION_FILE}")
        browser.close()
        return True


def upload_episode(audio_path: str, title: str, description: str) -> bool:
    """Upload un episode sur Spotify for Creators via Playwright."""
    if not SESSION_FILE.exists():
        log.error("Session Spotify non trouvee. Lance --save-session d'abord.")
        return False

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright non installe.")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(SESSION_FILE))
        page = context.new_page()

        try:
            # Aller sur la page d'upload
            if SPOTIFY_SHOW_ID:
                page.goto(f"https://creators.spotify.com/pod/show/{SPOTIFY_SHOW_ID}/home", timeout=30000)
            else:
                page.goto("https://creators.spotify.com", timeout=30000)
            time.sleep(5)

            # Cliquer sur "New Episode" ou "Upload"
            new_episode_btn = page.query_selector("button:has-text('New episode'), a:has-text('New episode'), button:has-text('Upload')")
            if new_episode_btn:
                new_episode_btn.click()
                time.sleep(3)

            # Upload le fichier audio
            file_input = page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(audio_path)
                time.sleep(5)
                log.info(f"Audio uploade: {Path(audio_path).name}")

            # Remplir le titre
            title_input = page.query_selector("input[name='title'], input[placeholder*='title'], input[placeholder*='Title']")
            if title_input:
                title_input.fill(title)
                time.sleep(1)

            # Remplir la description
            desc_input = page.query_selector("textarea[name='description'], div[contenteditable='true']")
            if desc_input:
                desc_input.click()
                time.sleep(0.5)
                page.keyboard.type(description, delay=20)
                time.sleep(1)

            # Publier
            publish_btn = page.query_selector("button:has-text('Publish'), button:has-text('Save')")
            if publish_btn:
                publish_btn.click()
                time.sleep(5)
                log.info(f"Episode publie: {title[:40]}")
                browser.close()
                return True
            else:
                log.warning("Bouton Publish non trouve")
                browser.close()
                return False

        except Exception as e:
            log.error(f"Upload Spotify echoue: {e}")
            browser.close()
            return False


def upload_all_episodes(date_str: str = None) -> Dict[str, bool]:
    """Upload tous les episodes (FR/EN/ES) sur Spotify."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    log.info(f"=== UPLOAD PODCAST SPOTIFY - {date_str} ===")
    results = {}

    # Generer les titres depuis le script
    script_path = ROOT / "output" / "scripts" / date_str / "script.json"
    script = {}
    if script_path.exists():
        try:
            script = json.loads(script_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    for lang in ("fr", "en", "es"):
        audio_path = PODCAST_DIR / f"{date_str}_long_{lang}.mp3"
        if not audio_path.exists():
            log.warning(f"Audio introuvable: {audio_path.name}")
            results[lang] = False
            continue

        titre = script.get(lang, {}).get("titre", f"Analyse economique {date_str} ({lang.upper()})")
        titre = titre.replace("#shorts", "").replace("#short", "").strip()[:100]
        description = f"Analyse economique quotidienne en {lang.upper()}. Sujet du jour: {titre}."

        ok = upload_episode(str(audio_path), titre, description)
        results[lang] = ok
        log.info(f"  {lang}: {'OK' if ok else 'ECHEC'}")
        time.sleep(5)  # Rate limit entre les uploads

    log.info(f"=== UPLOAD TERMINE: {sum(results.values())}/{len(results)} ===")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-session", action="store_true", help="Sauvegarder la session Spotify (1 fois)")
    parser.add_argument("--upload", type=str, help="Uploader les episodes pour une date")
    parser.add_argument("--upload-all", action="store_true", help="Uploader pour aujourd'hui")
    args = parser.parse_args()

    if args.save_session:
        save_spotify_session()
    elif args.upload:
        results = upload_all_episodes(args.upload)
        print(json.dumps(results, indent=2))
    elif args.upload_all:
        results = upload_all_episodes()
        print(json.dumps(results, indent=2))
    else:
        print("Usage: python podcast_spotify.py --save-session | --upload DATE | --upload-all")