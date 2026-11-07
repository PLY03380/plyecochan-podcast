#!/usr/bin/env python3
"""watchdog.py — Relance le bot si les videos du jour ne sont pas uploadees."""
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("watchdog")

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
BOT = ROOT / "bot.py"
MAX_RETRIES = 5
RETRY_DELAY = 1800  # 30 minutes


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def videos_exist(date_str):
    """Verifie si les 3 videos du jour existent."""
    vdir = ROOT / "output" / "videos" / date_str
    if not vdir.exists():
        return False
    for lang in ("fr", "en", "es"):
        candidates = list(vdir.glob(f"*short_{lang}.mp4"))
        if not candidates:
            return False
    return True


def videos_uploaded(date_str):
    """Verifie si les videos du jour sont uploadees sur YouTube."""
    try:
        import pickle
        creds = pickle.load(open(Path.home() / ".youtube_token.pickle", "rb"))
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", credentials=creds)
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        uploads_playlist = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        page_token = None
        while True:
            pl = yt.playlistItems().list(part="snippet", playlistId=uploads_playlist,
                                         maxResults=50, pageToken=page_token).execute()
            for item in pl.get("items", []):
                title = item["snippet"]["title"].lower()
                # Verifier si le titre contient la date du jour
                date_parts = date_str.split("-")
                # Format: DD-MM-YYYY
                date_formatted = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                if date_formatted in title or date_str in title:
                    return True
            page_token = pl.get("nextPageToken")
            if not page_token:
                break
        return False
    except Exception as e:
        log.warning(f"Impossible de verifier les uploads: {e}")
        return False


def run_bot():
    """Lance le bot et retourne True si succes."""
    log.info("Lancement du bot...")
    try:
        result = subprocess.run(
            [str(PYTHON), str(BOT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min max
        )
        if result.returncode == 0:
            log.info("Bot termine avec succes")
            return True
        else:
            log.error(f"Bot echoue (code {result.returncode})")
            log.error(result.stderr[-500:] if result.stderr else "no stderr")
            return False
    except subprocess.TimeoutExpired:
        log.error("Bot timeout (30 min)")
        return False
    except Exception as e:
        log.error(f"Erreur lancement bot: {e}")
        return False


def main():
    date_str = today_str()
    log.info(f"=== WATCHDOG — date: {date_str} ===")

    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"Tentative {attempt}/{MAX_RETRIES}")

        # Verifier si les videos existent
        if not videos_exist(date_str):
            log.info("Videos manquantes, lancement du bot...")
            if not run_bot():
                log.warning(f"Bot echoue, retry dans {RETRY_DELAY}s")
                time.sleep(RETRY_DELAY)
                continue
        else:
            log.info("Videos presentes")

        # Verifier si les videos sont uploadees
        if videos_uploaded(date_str):
            log.info("Toutes les videos sont uploadees. Termine.")
            return

        # Videos presentes mais pas uploadees -> lancer sync_uploads
        log.info("Videos presentes mais pas uploadees, lancement sync_uploads...")
        try:
            subprocess.run(
                [str(PYTHON), str(ROOT / "sync_uploads.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=600,
            )
        except Exception as e:
            log.warning(f"sync_uploads echoue: {e}")

        if videos_uploaded(date_str):
            log.info("Toutes les videos sont uploadees. Termine.")
            return

        log.warning(f"Pas toutes les videos uploadees, retry dans {RETRY_DELAY}s")
        time.sleep(RETRY_DELAY)

    log.error("Nombre max de tentatives atteint. Abandon.")


if __name__ == "__main__":
    main()