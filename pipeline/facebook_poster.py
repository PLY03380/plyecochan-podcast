"""facebook_poster.py — Publication sur la page Facebook Plychaneco."""
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Ajouter le repertoire parent au path pour import config
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

log = logging.getLogger("facebook")

GRAPH = "https://graph.facebook.com/v21.0"

def _get_config():
    try:
        import config
        return config
    except Exception:
        return None

_cfg = _get_config()
PAGE_ID = (_cfg.FACEBOOK_PAGE_ID if _cfg else os.getenv("FACEBOOK_PAGE_ID", "1389261604274221"))
PAGE_TOKEN = (_cfg.FACEBOOK_PAGE_TOKEN if _cfg else os.getenv("FACEBOOK_PAGE_TOKEN", ""))


def _get_token() -> str:
    """Recupere le token Facebook depuis config ou variable d'environnement."""
    if PAGE_TOKEN:
        return PAGE_TOKEN
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("FACEBOOK_PAGE_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def publier_post(texte: str, lien: str = None) -> Optional[str]:
    """Publie un post texte (+ lien) sur la page Facebook. Retourne l'ID du post ou None."""
    token = _get_token()
    if not token:
        log.warning("FACEBOOK_PAGE_TOKEN non configure")
        return None
    try:
        import requests
        data = {"message": texte, "access_token": token}
        if lien:
            data["link"] = lien
        r = requests.post(f"{GRAPH}/{PAGE_ID}/feed", data=data, timeout=30)
        r.raise_for_status()
        post_id = r.json().get("id")
        log.info(f"Post Facebook publie: {post_id}")
        return post_id
    except Exception as e:
        log.error(f"Publication Facebook echouee: {e}")
        return None


def publier_video(chemin_mp4: str, description: str) -> Optional[str]:
    """Publie une video sur la page Facebook. Retourne l'ID de la video ou None."""
    token = _get_token()
    if not token:
        log.warning("FACEBOOK_PAGE_TOKEN non configure")
        return None
    try:
        import requests
        with open(chemin_mp4, "rb") as f:
            r = requests.post(
                f"{GRAPH}/{PAGE_ID}/videos",
                data={"description": description, "access_token": token},
                files={"source": f},
                timeout=600,
            )
        r.raise_for_status()
        video_id = r.json().get("id")
        log.info(f"Video Facebook publiee: {video_id}")
        return video_id
    except Exception as e:
        log.error(f"Publication video Facebook echouee: {e}")
        return None


def publier_reel(chemin_mp4: str, description: str) -> Optional[str]:
    """Publie un Reel sur la page Facebook (3 phases). Retourne l'ID ou None."""
    token = _get_token()
    if not token:
        log.warning("FACEBOOK_PAGE_TOKEN non configure")
        return None
    try:
        import requests
        r = requests.post(
            f"{GRAPH}/{PAGE_ID}/video_reels",
            data={"upload_phase": "start", "access_token": token},
            timeout=30,
        )
        r.raise_for_status()
        upload_session_id = r.json().get("upload_session_id")
        if not upload_session_id:
            log.error("Pas de session d'upload retournee")
            return None

        with open(chemin_mp4, "rb") as f:
            r = requests.post(
                f"{GRAPH}/{PAGE_ID}/video_reels",
                data={"upload_phase": "transfer", "upload_session_id": upload_session_id, "access_token": token},
                files={"video_file_chunk": f},
                timeout=600,
            )
        r.raise_for_status()

        r = requests.post(
            f"{GRAPH}/{PAGE_ID}/video_reels",
            data={"upload_phase": "finish", "upload_session_id": upload_session_id,
                  "description": description, "access_token": token},
            timeout=60,
        )
        r.raise_for_status()
        video_id = r.json().get("video_id")
        log.info(f"Reel Facebook publie: {video_id}")
        return video_id
    except Exception as e:
        log.error(f"Publication Reel Facebook echouee: {e}")
        return None


def publier_article_blog(titre: str, lien_blog: str, resume: str = None) -> Optional[str]:
    """Publie un post Facebook partageant un article du blog."""
    texte = f"{titre}\n\n"
    if resume:
        texte += f"{resume}\n\n"
    texte += f"Lire l'article complet : {lien_blog}\n\nAbonnez-vous a PlyChan sur YouTube : https://www.youtube.com/@PlyChan"
    return publier_post(texte, lien_blog)


def safe_publish_facebook(titre: str, lien_blog: str, resume: str = None,
                          video_path: str = None, is_reel: bool = False) -> Optional[str]:
    """Publication Facebook pour le pipeline : ne plante jamais, retourne l'ID ou None."""
    try:
        if video_path and Path(video_path).exists():
            if is_reel:
                return publier_reel(video_path, f"{titre}\n\n{lien_blog}")
            return publier_video(video_path, f"{titre}\n\n{lien_blog}")
        return publier_article_blog(titre, lien_blog, resume)
    except Exception as e:
        log.error(f"safe_publish_facebook echoue: {e}")
        return None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        post_id = publier_post("Test PlyChanBot - article partage automatiquement")
        if post_id:
            print(f"Post publie: {post_id}")
    else:
        print("Usage: python facebook_poster.py test")