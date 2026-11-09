"""podcast_upload.py — Upload automatique sur RSS.com (20+ plateformes).

Utilise l'API RSS.com pour uploader les episodes de podcast.
Necessite un compte RSS.com Max plan + API key.

Usage:
    python pipeline/podcast_upload.py --upload 2026-11-09  # Upload les episodes
    python pipeline/podcast_upload.py --test               # Tester la connexion
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("podcast_upload")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PODCAST_DIR = ROOT / "output" / "podcast"


def _get_config():
    try:
        import config
        return config
    except Exception:
        return None


def _get_api_key() -> str:
    cfg = _get_config()
    key = getattr(cfg, "RSS_COM_API_KEY", "") if cfg else os.getenv("RSS_COM_API_KEY", "")
    if not key:
        # Try env
        key = os.getenv("RSS_API_KEY", "")
    return key


def test_connection() -> bool:
    """Teste la connexion a l'API RSS.com."""
    api_key = _get_api_key()
    if not api_key:
        log.warning("RSS.com: pas de cle API (RSS_COM_API_KEY requise)")
        return False
    try:
        import requests
        resp = requests.get(
            "https://api.rss.com/v4/podcasts",
            headers={"X-Api-Key": api_key},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            podcasts = data.get("podcasts", data.get("data", []))
            log.info(f"RSS.com: connexion OK, {len(podcasts)} podcast(s)")
            for p in podcasts:
                print(f"  - {p.get('title', p.get('name', '?'))} (ID: {p.get('id', '?')})")
            return True
        else:
            log.error(f"RSS.com: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        log.error(f"RSS.com connexion echouee: {e}")
        return False


def get_podcast_id() -> Optional[str]:
    """Recupere l'ID du podcast PlyChan."""
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        import requests
        resp = requests.get(
            "https://api.rss.com/v4/podcasts",
            headers={"X-Api-Key": api_key},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            podcasts = data.get("podcasts", data.get("data", []))
            for p in podcasts:
                title = p.get("title", p.get("name", "")).lower()
                if "plychan" in title or "economie" in title:
                    return p.get("id")
            if podcasts:
                return podcasts[0].get("id")
    except Exception as e:
        log.error(f"RSS.com get_podcast_id echoue: {e}")
    return None


def create_presigned_upload(audio_path: str) -> Optional[Dict]:
    """Cree une URL d'upload presignee pour un fichier audio."""
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        import requests
        resp = requests.post(
            "https://api.rss.com/v4/assets/presigned-uploads",
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            json={"expected_mime": "audio/mpeg"},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return data
        else:
            log.error(f"RSS.com presigned upload: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log.error(f"RSS.com presigned upload echoue: {e}")
    return None


def upload_audio(audio_path: str) -> Optional[str]:
    """Upload un fichier audio sur RSS.com. Retourne l'upload ID."""
    api_key = _get_api_key()
    if not api_key:
        return None

    # 1. Creer l'URL presignee
    upload_info = create_presigned_upload(audio_path)
    if not upload_info:
        return None

    upload_url = upload_info.get("url") or upload_info.get("upload_url")
    upload_id = upload_info.get("id") or upload_info.get("upload_id")

    if not upload_url:
        log.error("RSS.com: pas d'URL d'upload retournee")
        return None

    # 2. Upload le fichier
    try:
        import requests
        with open(audio_path, "rb") as f:
            resp = requests.put(
                upload_url,
                data=f,
                headers={"Content-Type": "audio/mpeg"},
                timeout=300,
            )
            if resp.status_code in (200, 201, 204):
                log.info(f"RSS.com: audio uploade ({Path(audio_path).name})")
                return upload_id
            else:
                log.error(f"RSS.com upload: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log.error(f"RSS.com upload echoue: {e}")
    return None


def create_episode(podcast_id: str, title: str, description: str,
                   audio_upload_id: str, language: str = "fr") -> Optional[str]:
    """Cree un episode sur RSS.com."""
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        import requests
        resp = requests.post(
            f"https://api.rss.com/v4/podcasts/{podcast_id}/episodes",
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            json={
                "title": title,
                "description": description,
                "audio_upload_id": audio_upload_id,
                "language": language,
            },
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            episode_id = data.get("id") or data.get("episode_id")
            log.info(f"RSS.com: episode cree ({title[:40]})")
            return episode_id
        else:
            log.error(f"RSS.com create episode: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log.error(f"RSS.com create episode echoue: {e}")
    return None


def publish_episode(podcast_id: str, episode_id: str) -> bool:
    """Publie un episode (le met en ligne)."""
    api_key = _get_api_key()
    if not api_key:
        return False
    try:
        import requests
        resp = requests.patch(
            f"https://api.rss.com/v4/podcasts/{podcast_id}/episodes/{episode_id}",
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            json={"schedule_datetime": None},  # None = publier immediatement
            timeout=30,
        )
        if resp.status_code in (200, 201, 204):
            log.info(f"RSS.com: episode publie ({episode_id})")
            return True
        else:
            log.error(f"RSS.com publish: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log.error(f"RSS.com publish echoue: {e}")
    return False


def upload_episode(date_str: str, lang: str, title: str = None, description: str = None) -> bool:
    """Upload un episode complet (audio + creation + publication)."""
    podcast_id = get_podcast_id()
    if not podcast_id:
        log.error("RSS.com: pas de podcast ID")
        return False

    audio_path = PODCAST_DIR / f"{date_str}_long_{lang}.mp3"
    if not audio_path.exists():
        log.error(f"RSS.com: fichier audio introuvable: {audio_path}")
        return False

    if title is None:
        title = f"Analyse economique {date_str} ({lang.upper()})"
    if description is None:
        description = f"Analyse economique quotidienne en {lang.upper()}. Sujet du jour disponible sur PlyChan."

    # 1. Upload audio
    audio_id = upload_audio(str(audio_path))
    if not audio_id:
        return False

    # 2. Creer l'episode
    episode_id = create_episode(podcast_id, title, description, audio_id, lang)
    if not episode_id:
        return False

    # 3. Publier
    return publish_episode(podcast_id, episode_id)


def upload_all_episodes(date_str: str = None) -> Dict[str, bool]:
    """Upload tous les episodes (FR/EN/ES) pour une date."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    log.info(f"=== UPLOAD PODCAST RSS.com - {date_str} ===")
    results = {}

    for lang in ("fr", "en", "es"):
        audio_path = PODCAST_DIR / f"{date_str}_long_{lang}.mp3"
        if not audio_path.exists():
            log.warning(f"Audio introuvable: {audio_path.name}")
            results[lang] = False
            continue

        # Generer le titre depuis le script
        title = f"Analyse economique {date_str} ({lang.upper()})"
        script_path = ROOT / "output" / "scripts" / date_str / "script.json"
        if script_path.exists():
            try:
                script = json.loads(script_path.read_text(encoding="utf-8"))
                titre = script.get(lang, {}).get("titre", "")
                if titre:
                    title = titre.replace("#shorts", "").replace("#short", "").strip()[:100]
            except Exception:
                pass

        ok = upload_episode(date_str, lang, title)
        results[lang] = ok
        log.info(f"  {lang}: {'OK' if ok else 'ECHEC'}")

    log.info(f"=== UPLOAD TERMINE: {sum(results.values())}/{len(results)} ===")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Tester la connexion")
    parser.add_argument("--upload", type=str, help="Uploader les episodes pour une date")
    parser.add_argument("--upload-all", action="store_true", help="Uploader pour aujourd'hui")
    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.upload:
        results = upload_all_episodes(args.upload)
        print(json.dumps(results, indent=2))
    elif args.upload_all:
        results = upload_all_episodes()
        print(json.dumps(results, indent=2))
    else:
        print("Usage: python podcast_upload.py --test | --upload DATE | --upload-all")