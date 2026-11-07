#!/usr/bin/env python3
"""sync_uploads.py — Vérifie et upload les vidéos manquantes sur YouTube."""
import json
import logging
import os
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("sync_uploads")

ROOT = Path(__file__).resolve().parent
VIDEOS_DIR = ROOT / "output" / "videos"
AUDIO_DIR = ROOT / "output" / "audio"
SCRIPTS_DIR = ROOT / "output" / "scripts"


def get_uploaded_video_ids() -> set:
    """Retourne l'ensemble des video_id deja uploades sur la chaine."""
    try:
        from pipeline.upload import get_authenticated_service
        yt = get_authenticated_service()
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        uploads_playlist = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        ids = set()
        page_token = None
        while True:
            pl = yt.playlistItems().list(part="snippet", playlistId=uploads_playlist,
                                         maxResults=50, pageToken=page_token).execute()
            for item in pl.get("items", []):
                ids.add(item["snippet"]["resourceId"]["videoId"])
            page_token = pl.get("nextPageToken")
            if not page_token:
                break
        return ids
    except Exception as e:
        log.error(f"Impossible de lister les videos: {e}")
        return set()


def get_video_title(video_id: str) -> str:
    """Recupere le titre d'une video YouTube."""
    try:
        from pipeline.upload import get_authenticated_service
        yt = get_authenticated_service()
        r = yt.videos().list(part="snippet", id=video_id).execute()
        if r.get("items"):
            return r["items"][0]["snippet"]["title"]
    except Exception:
        pass
    return ""


def find_script(date_str: str) -> dict:
    """Cherche le script JSON pour une date."""
    # Chercher dans output/scripts/
    script_path = SCRIPTS_DIR / date_str / "script.json"
    if script_path.exists():
        try:
            return json.loads(script_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Pas de fallback — eviter les faux positifs
    return {}


def sync():
    """Verifie et upload les videos manquantes."""
    uploaded_ids = get_uploaded_video_ids()
    log.info(f"Videos deja uploadees: {len(uploaded_ids)}")

    # Recuperer les titres des videos uploadees pour comparaison
    uploaded_titles = set()
    try:
        from pipeline.upload import get_authenticated_service
        yt = get_authenticated_service()
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        uploads_playlist = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        page_token = None
        while True:
            pl = yt.playlistItems().list(part="snippet", playlistId=uploads_playlist,
                                         maxResults=50, pageToken=page_token).execute()
            for item in pl.get("items", []):
                uploaded_titles.add(item["snippet"]["title"].lower().strip())
            page_token = pl.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        log.warning(f"Impossible de recuperer les titres: {e}")

    from pipeline.upload import upload_all

    # Parcourir les dossiers de videos (seulement les 3 derniers jours)
    if not VIDEOS_DIR.exists():
        log.warning("Pas de dossier videos")
        return

    from datetime import timedelta
    today = datetime.now()
    # Ne traiter que le jour en cours (pas les anciens)
    recent_dates = {today.strftime("%Y-%m-%d")}

    # Charger le suivi des videos longues uploadees
    long_tracker = ROOT / "output" / "long_uploaded.json"
    long_uploaded = set()
    if long_tracker.exists():
        try:
            long_uploaded = set(json.loads(long_tracker.read_text(encoding="utf-8")))
        except Exception:
            pass

    for date_dir in sorted(VIDEOS_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        date_str = date_dir.name
        if date_str not in recent_dates:
            continue
        script = find_script(date_str)

        for lang in ("fr", "en", "es"):
            video_file = date_dir / f"{date_str.replace('-', '-')}_short_{lang}.mp4"  # placeholder
            # Chercher le fichier video (format: DD-MM-YYYY_short_lang.mp4)
            # Ignorer les fichiers de test (test_*, short_ sans date)
            candidates = [c for c in date_dir.glob(f"*short_{lang}.mp4")
                          if not c.name.startswith("test_") and not c.name.startswith("short_")]
            if not candidates:
                continue
            video_path = candidates[0]

            # Verifier si deja uploade (par titre ou par nom de fichier)
            # On ne peut pas matcher par nom de fichier, donc on upload et YouTube deduplique
            # Mais pour eviter les doublons, on verifie le titre
            titre = ""
            if script:
                titre = script.get(lang, {}).get("titre", "")
            # Ignorer les videos de test (titre generique ou vide)
            if not titre or titre.lower().strip() in ("", "video fr", "video en", "video es", "test"):
                log.info(f"Ignore (pas de titre valide): {video_path.name}")
                continue
            if titre.lower().strip() in uploaded_titles:
                log.info(f"Deja uploade ({lang}): {titre[:50]}")
                continue

            log.info(f"Upload manquant: {video_path.name} ({lang})")
            try:
                videos = {lang: str(video_path)}
                ids = upload_all(videos, script if script else {})
                if ids.get(lang):
                    log.info(f"  -> uploade: https://youtu.be/{ids[lang]}")
                    if titre:
                        uploaded_titles.add(titre.lower().strip())
            except Exception as e:
                err_str = str(e)
                log.error(f"  -> echec: {err_str[:80]}")
                if "uploadLimitExceeded" in err_str:
                    log.warning("Limite d'upload YouTube atteinte. Arret.")
                    return  # stop all uploads

    # Upload des videos longues (seulement les 3 derniers jours)
    for date_dir in sorted(VIDEOS_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        date_str = date_dir.name
        if date_str not in recent_dates:
            continue
        for lang in ("fr", "en", "es"):
            candidates = [c for c in date_dir.glob(f"*long_{lang}.mp4")
                          if not c.name.startswith("test_")]
            if not candidates:
                continue
            video_path = candidates[0]
            tracker_key = f"{date_str}_{lang}"
            if tracker_key in long_uploaded:
                log.info(f"Deja uploade (long {lang}): {video_path.name}")
                continue

            log.info(f"Upload manquant (long): {video_path.name} ({lang})")
            try:
                from pipeline.upload import upload_all
                # Utiliser un titre generique pour les longues
                script = find_script(date_str)
                titre = ""
                if script:
                    titre = script.get(lang, {}).get("titre", "")
                if not titre:
                    titre = f"Analyse economique {date_str} ({lang})"
                # Creer un script minimal pour upload_all
                minimal_script = {lang: {"titre": titre, "blocs": {}}}
                ids = upload_all({lang: str(video_path)}, minimal_script)
                if ids.get(lang):
                    log.info(f"  -> uploade (long): https://youtu.be/{ids[lang]}")
                    long_uploaded.add(tracker_key)
                    long_tracker.write_text(json.dumps(list(long_uploaded)), encoding="utf-8")
            except Exception as e:
                err_str = str(e)
                log.error(f"  -> echec (long): {err_str[:80]}")
                if "uploadLimitExceeded" in err_str:
                    log.warning("Limite d'upload YouTube atteinte. Arret.")
                    return


if __name__ == "__main__":
    sync()