"""youtube_podcast.py — Cree un podcast YouTube via automatisation Playwright.

Automatise la creation d'un podcast YouTube dans YouTube Studio.
Necessite une session YouTube connectee.

Usage:
    python pipeline/youtube_podcast.py --create    # Creer le podcast
    python pipeline/youtube_podcast.py --add-videos  # Ajouter les videos longues
    python pipeline/youtube_podcast.py --all       # Tout
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
log = logging.getLogger("yt_podcast")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SESSION_FILE = ROOT / "output" / "youtube_studio_session.json"


def create_podcast():
    """Cree un podcast YouTube dans YouTube Studio."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright non installe. pip install playwright && playwright install chromium")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Aller sur YouTube Studio
            page.goto("https://studio.youtube.com", timeout=30000)
            time.sleep(5)

            print("\n" + "=" * 60)
            print("CONNECTE-TOI A YOUTUBE STUDIO DANS LE NAVIGATEUR")
            print("Tu as 300 secondes pour te connecter")
            print("=" * 60)

            # Attendre la connexion
            for i in range(300):
                time.sleep(1)
                try:
                    current_url = page.url
                    if "studio.youtube.com" in current_url and "login" not in current_url and "accounts." not in current_url and "signin" not in current_url:
                        if "channel" in current_url or "dashboard" in current_url or "content" in current_url:
                            log.info("Connexion detectee !")
                            time.sleep(5)
                            break
                except Exception:
                    pass

            # Naviguer vers Podcasts
            page.goto("https://studio.youtube.com/channel/UC/videos/podcasts", timeout=30000)
            time.sleep(5)

            # Cliquer sur "Create new podcast"
            create_btn = page.query_selector("button:has-text('Create new podcast'), button:has-text('Créer un podcast'), button:has-text('Create podcast')")
            if create_btn:
                create_btn.click()
                time.sleep(3)
                log.info("Bouton 'Create new podcast' clique")

            # Remplir le titre
            title_input = page.query_selector("input[placeholder*='title'], input[placeholder*='Title'], input[placeholder*='titre'], input[placeholder*='Titre'], input[name='title']")
            if title_input:
                title_input.fill("PlyChan Économie")
                time.sleep(1)

            # Remplir la description
            desc_input = page.query_selector("textarea[placeholder*='description'], textarea[placeholder*='Description'], textarea[name='description']")
            if desc_input:
                desc_input.fill("Analyses économiques quotidiennes en 3 langues (FR/EN/ES). Chaque jour, un sujet d'actualité économique expliqué simplement.")
                time.sleep(1)

            # Categorie
            category_select = page.query_selector("select[name='category'], select[aria-label*='category'], select[aria-label*='Category']")
            if category_select:
                category_select.select_option("News & Politics")
                time.sleep(1)

            # Langue
            lang_select = page.query_selector("select[name='language'], select[aria-label*='language'], select[aria-label*='Language']")
            if lang_select:
                lang_select.select_option("English")
                time.sleep(1)

            # Cliquer sur Create
            submit_btn = page.query_selector("button:has-text('Create'), button:has-text('Créer'), button[type='submit']")
            if submit_btn:
                submit_btn.click()
                time.sleep(5)
                log.info("Podcast cree !")
                # Sauvegarder la session
                context.storage_state(path=str(SESSION_FILE))
                log.info(f"Session sauvegardee: {SESSION_FILE}")
                browser.close()
                return True
            else:
                log.warning("Bouton Create non trouve")
                page.screenshot(path=str(ROOT / "output" / "yt_podcast_debug.png"))
                log.info("Screenshot sauvegarde: output/yt_podcast_debug.png")
                time.sleep(30)
                browser.close()
                return False

        except Exception as e:
            log.error(f"Creation podcast echouee: {e}")
            browser.close()
            return False


def add_videos_to_podcast():
    """Ajoute les videos longues existantes au podcast."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright non installe.")
        return False

    if not SESSION_FILE.exists():
        log.error("Session YouTube Studio non trouvee. Lance --create d'abord.")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=str(SESSION_FILE))
        page = context.new_page()

        try:
            # Aller sur la page des videos
            page.goto("https://studio.youtube.com/channel/videos", timeout=30000)
            time.sleep(5)

            # Chercher les videos longues (avec "long" dans le nom)
            # Selectionner les videos longues
            video_rows = page.query_selector_all("ytcp-video-row")
            log.info(f"Videos trouvees: {len(video_rows)}")

            long_videos = []
            for row in video_rows:
                title = row.query_selector("div#video-title")
                if title and "long" in title.text_content().lower():
                    long_videos.append(row)

            log.info(f"Videos longues: {len(long_videos)}")

            # Pour chaque video longue, l'ajouter au podcast
            for video in long_videos[:10]:  # Max 10 par run
                try:
                    # Cliquer sur le menu (3 points)
                    menu = video.query_selector("button[aria-label*='More'], button[aria-label*='more'], button[aria-label*='Plus']")
                    if menu:
                        menu.click()
                        time.sleep(1)
                        # Cliquer sur "Add to podcast"
                        add_podcast = page.query_selector("tp-yt-paper-item:has-text('Add to podcast'), tp-yt-paper-item:has-text('Ajouter au podcast')")
                        if add_podcast:
                            add_podcast.click()
                            time.sleep(2)
                            log.info("Video ajoutee au podcast")
                except Exception as e:
                    log.warning(f"Video skip: {e}")

            browser.close()
            return True

        except Exception as e:
            log.error(f"Ajout videos echoue: {e}")
            browser.close()
            return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true", help="Creer le podcast")
    parser.add_argument("--add-videos", action="store_true", help="Ajouter les videos longues")
    parser.add_argument("--all", action="store_true", help="Tout")
    args = parser.parse_args()

    if args.create or args.all:
        create_podcast()
    if args.add_videos or args.all:
        add_videos_to_podcast()
    if not (args.create or args.add_videos or args.all):
        print("Usage: python youtube_podcast.py --create | --add-videos | --all")