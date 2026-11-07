"""multi_social.py — Distribution multi-reseaux (Publora / PostLake).

Publie sur 10+ reseaux sociaux en un seul appel.
Supporte Publora et PostLake (choisir celui qui a des credits).

Usage:
    python pipeline/multi_social.py --post "Titre" --url "https://youtube.com/..." --image "thumb.jpg"
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("multi_social")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _get_config():
    try:
        import config
        return config
    except Exception:
        return None


def post_publora(content: str, url: str = None, image_path: str = None,
                 platforms: List[str] = None) -> Optional[Dict]:
    """Publie sur Publora (10 reseaux en un appel)."""
    cfg = _get_config()
    api_key = getattr(cfg, "PUBLORA_API_KEY", "") if cfg else os.getenv("PUBLORA_API_KEY", "")
    if not api_key:
        log.warning("Publora: pas de cle (PUBLORA_API_KEY requise)")
        return None

    if platforms is None:
        platforms = ["twitter", "instagram", "linkedin", "facebook", "tiktok", "pinterest"]

    try:
        import requests
        import base64
        payload = {
            "content": content,
            "platforms": platforms,
        }
        if url:
            payload["url"] = url
        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as f:
                payload["image"] = base64.b64encode(f.read()).decode()

        resp = requests.post(
            "https://api.publora.com/v1/post",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        log.info(f"Publora: publie sur {len(platforms)} reseaux")
        return data
    except Exception as e:
        log.error(f"Publora echoue: {e}")
        return None


def post_postlake(content: str, url: str = None, platforms: List[str] = None,
                  scheduled_at: str = None) -> Optional[Dict]:
    """Publie sur PostLake (publish + schedule + analytics)."""
    cfg = _get_config()
    api_key = getattr(cfg, "POSTLAKE_API_KEY", "") if cfg else os.getenv("POSTLAKE_API_KEY", "")
    if not api_key:
        log.warning("PostLake: pas de cle (POSTLAKE_API_KEY requise)")
        return None

    if platforms is None:
        platforms = ["twitter", "linkedin", "facebook"]

    try:
        import requests
        payload = {
            "content": content,
            "platforms": platforms,
        }
        if url:
            payload["url"] = url
        if scheduled_at:
            payload["publishDate"] = scheduled_at

        resp = requests.post(
            "https://api.postlake.io/v1/posts",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        log.info(f"PostLake: publie sur {len(platforms)} reseaux")
        return data
    except Exception as e:
        log.error(f"PostLake echoue: {e}")
        return None


def distribuer_video_tous_reseaux(video_data: dict, use_publora: bool = True) -> Dict:
    """Distribue une video sur tous les reseaux sociaux.

    video_data = {titre, url_youtube, description, hashtags, thumbnail_path}
    """
    titre = video_data.get("titre", "")
    url = video_data.get("url_youtube", "")
    hashtags = video_data.get("hashtags", [])
    thumbnail = video_data.get("thumbnail_path", "")

    content = f"{titre}\n\n{' '.join(['#' + h for h in hashtags])}\n\n{url}"

    if use_publora:
        result = post_publora(content, url, thumbnail)
    else:
        result = post_postlake(content, url)

    if result:
        log.info(f"Distribution OK: {titre[:50]}")
    else:
        log.warning(f"Distribution echouee: {titre[:50]}")

    return result or {}


def get_optimal_post_time() -> str:
    """Retourne l'heure optimale de publication (heure de pointe audience)."""
    # Heures de pointe generalement : 9h, 12h, 18h (heure locale)
    now = datetime.now()
    hour = now.hour
    if hour < 9:
        return now.replace(hour=9, minute=0, second=0).isoformat() + "Z"
    elif hour < 12:
        return now.replace(hour=12, minute=0, second=0).isoformat() + "Z"
    elif hour < 18:
        return now.replace(hour=18, minute=0, second=0).isoformat() + "Z"
    else:
        return now.replace(hour=9, minute=0, second=0).isoformat() + "Z"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--post", type=str, help="Contenu du post")
    parser.add_argument("--url", type=str, help="URL a partager")
    parser.add_argument("--image", type=str, help="Chemin de l'image")
    parser.add_argument("--platforms", nargs="+", default=["twitter", "facebook", "linkedin"])
    parser.add_argument("--postlake", action="store_true", help="Utiliser PostLake au lieu de Publora")
    args = parser.parse_args()

    if args.post:
        if args.postlake:
            result = post_postlake(args.post, args.url, args.platforms)
        else:
            result = post_publora(args.post, args.url, args.image, args.platforms)
        print(json.dumps(result, indent=2, ensure_ascii=True) if result else "ECHEC")
    else:
        print("Usage: python multi_social.py --post 'Titre' --url 'URL' [--image 'path'] [--postlake]")