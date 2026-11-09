"""podcast_zeno.py — Upload automatique sur Zeno.FM (distribution podcast).

Utilise l'API Zeno.FM pour uploader et publier des episodes de podcast.
Distribution automatique sur Apple Podcasts, Spotify, etc.

Usage:
    python pipeline/podcast_zeno.py --test               # Tester la connexion
    python pipeline/podcast_zeno.py --upload 2026-11-09  # Upload les episodes
    python pipeline/podcast_zeno.py --upload-all        # Upload pour aujourd'hui
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("podcast_zeno")

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
    key = getattr(cfg, "ZENO_API_KEY", "") if cfg else os.getenv("ZENO_API_KEY", "")
    return key


def test_connection() -> bool:
    """Teste la connexion a l'API Zeno.FM."""
    api_key = _get_api_key()
    if not api_key:
        log.warning("Zeno.FM: pas de cle API (ZENO_API_KEY requise)")
        return False
    try:
        import requests
        resp = requests.get(
            "https://api.zeno.fm/api/v2/podcasts",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            podcasts = data if isinstance(data, list) else data.get("podcasts", [])
            log.info(f"Zeno.FM: connexion OK, {len(podcasts)} podcast(s)")
            for p in podcasts:
                print(f"  - {p.get('name', p.get('title', '?'))} (Key: {p.get('key', p.get('id', '?'))})")
            return True
        else:
            log.error(f"Zeno.FM: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        log.error(f"Zeno.FM connexion echouee: {e}")
        return False


def get_podcast_key() -> Optional[str]:
    """Recupere la cle du podcast PlyChan."""
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        import requests
        resp = requests.get(
            "https://api.zeno.fm/api/v2/podcasts",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            podcasts = data if isinstance(data, list) else data.get("podcasts", [])
            for p in podcasts:
                name = p.get("name", p.get("title", "")).lower()
                if "plychan" in name or "economie" in name or "economy" in name:
                    return p.get("key", p.get("id"))
            if podcasts:
                return podcasts[0].get("key", podcasts[0].get("id"))
    except Exception as e:
        log.error(f"Zeno.FM get_podcast_key echoue: {e}")
    return None


def create_podcast(name: str, description: str) -> Optional[str]:
    """Cree un nouveau podcast sur Zeno.FM."""
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        import requests
        resp = requests.post(
            "https://api.zeno.fm/api/v2/podcasts/create",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"name": name, "description": description},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            key = data.get("key", data.get("id"))
            log.info(f"Zeno.FM: podcast cree ({name}) -> {key}")
            return key
        else:
            log.error(f"Zeno.FM create podcast: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log.error(f"Zeno.FM create podcast echoue: {e}")
    return None


def create_episode(podcast_key: str, title: str, description: str) -> Optional[str]:
    """Cree un episode sur Zeno.FM."""
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        import requests
        resp = requests.post(
            f"https://api.zeno.fm/api/v2/podcasts/{podcast_key}/episodes/create",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"title": title, "description": description},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            episode_key = data.get("key", data.get("id"))
            log.info(f"Zeno.FM: episode cree ({title[:40]})")
            return episode_key
        else:
            log.error(f"Zeno.FM create episode: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log.error(f"Zeno.FM create episode echoue: {e}")
    return None


def upload_audio(podcast_key: str, episode_key: str, audio_path: str) -> bool:
    """Upload un fichier audio sur Zeno.FM."""
    api_key = _get_api_key()
    if not api_key:
        return False
    try:
        import requests
        with open(audio_path, "rb") as f:
            resp = requests.put(
                f"https://api.zeno.fm/api/v2/podcasts/{podcast_key}/episodes/{episode_key}/upload",
                headers={"Authorization": f"Bearer {api_key}"},
                data=f,
                timeout=300,
            )
        if resp.status_code in (200, 201, 204):
            log.info(f"Zeno.FM: audio uploade ({Path(audio_path).name})")
            return True
        else:
            log.error(f"Zeno.FM upload: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log.error(f"Zeno.FM upload echoue: {e}")
    return False


def publish_episode(podcast_key: str, episode_key: str) -> bool:
    """Publie un episode sur Zeno.FM."""
    api_key = _get_api_key()
    if not api_key:
        return False
    try:
        import requests
        resp = requests.put(
            f"https://api.zeno.fm/api/v2/podcasts/{podcast_key}/episodes/{episode_key}/publish",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if resp.status_code in (200, 201, 204):
            log.info(f"Zeno.FM: episode publie ({episode_key})")
            return True
        else:
            log.error(f"Zeno.FM publish: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log.error(f"Zeno.FM publish echoue: {e}")
    return False


def upload_episode(date_str: str, lang: str, title: str = None, description: str = None) -> bool:
    """Upload un episode complet (audio + creation + publication)."""
    podcast_key = get_podcast_key()
    if not podcast_key:
        log.error("Zeno.FM: pas de podcast key. Cree un podcast d'abord.")
        return False

    audio_path = PODCAST_DIR / f"{date_str}_long_{lang}.mp3"
    if not audio_path.exists():
        log.error(f"Zeno.FM: fichier audio introuvable: {audio_path}")
        return False

    if title is None:
        title = f"Analyse economique {date_str} ({lang.upper()})"
    if description is None:
        description = f"Analyse economique quotidienne en {lang.upper()}."

    # 1. Creer l'episode
    episode_key = create_episode(podcast_key, title, description)
    if not episode_key:
        return False

    # 2. Upload l'audio
    if not upload_audio(podcast_key, episode_key, str(audio_path)):
        return False

    # 3. Publier
    return publish_episode(podcast_key, episode_key)


def upload_all_episodes(date_str: str = None) -> Dict[str, bool]:
    """Upload tous les episodes (FR/EN/ES) pour une date."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    log.info(f"=== UPLOAD PODCAST Zeno.FM - {date_str} ===")
    results = {}

    for lang in ("fr", "en", "es"):
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
    parser.add_argument("--create-podcast", action="store_true", help="Creer le podcast PlyChan")
    parser.add_argument("--upload", type=str, help="Uploader les episodes pour une date")
    parser.add_argument("--upload-all", action="store_true", help="Uploader pour aujourd'hui")
    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.create_podcast:
        key = create_podcast("PlyChan Economie", "Analyses economiques quotidiennes en 3 langues (FR/EN/ES)")
        if key:
            print(f"Podcast cree avec la cle: {key}")
            print("Ajoute ZENO_PODCAST_KEY=" + key + " dans config.py")
    elif args.upload:
        results = upload_all_episodes(args.upload)
        print(json.dumps(results, indent=2))
    elif args.upload_all:
        results = upload_all_episodes()
        print(json.dumps(results, indent=2))
    else:
        print("Usage: python podcast_zeno.py --test | --create-podcast | --upload DATE | --upload-all")