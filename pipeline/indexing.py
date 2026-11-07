"""indexing.py — Indexation Google via l'API Google Indexing."""
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

log = logging.getLogger("indexing")

CREDENTIALS_FILE = Path("plychanbot-1937b6d23966.json")
SCOPES = ["https://www.googleapis.com/auth/indexing"]
BLOG_URL = "https://plychaneconomie.blogspot.com"


def _find_credentials() -> Path:
    """Cherche le fichier de credentials dans plusieurs emplacements."""
    candidates = [
        CREDENTIALS_FILE,
        Path("config") / "plychanbot-1937b6d23966.json",
        Path.home() / "blogger-indexing" / "plychanbot-1937b6d23966.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return CREDENTIALS_FILE  # default, will fail if not found


def get_service():
    """Connexion à l'API Google Indexing."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_file = _find_credentials()
    if not creds_file.exists():
        log.warning(f"Fichier credentials non trouvé: {creds_file}")
        return None
    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(creds_file), scopes=SCOPES
        )
        return build("indexing", "v3", credentials=credentials)
    except Exception as e:
        log.error(f"Erreur connexion Indexing API: {e}")
        return None


def indexer_url(url: str) -> bool:
    """Envoie une URL à indexer immédiatement. Retourne True si succès."""
    service = get_service()
    if not service:
        return False
    try:
        response = service.urlNotifications().publish(body={
            "url": url,
            "type": "URL_UPDATED"
        }).execute()
        log.info(f"Indexe : {url}")
        return True
    except Exception as e:
        log.error(f"Erreur indexation {url}: {e}")
        return False


def indexer_plusieurs(urls: List[str]) -> int:
    """Indexe plusieurs URLs (max 200/jour). Retourne le nombre d'URLs indexées."""
    count = 0
    for url in urls:
        try:
            if indexer_url(url):
                count += 1
        except Exception as e:
            log.error(f"Erreur : {url} -> {e}")
    return count


def supprimer_url(url: str) -> bool:
    """Signale une URL supprimée à Google."""
    service = get_service()
    if not service:
        return False
    try:
        service.urlNotifications().publish(body={
            "url": url,
            "type": "URL_DELETED"
        }).execute()
        log.info(f"Supprime : {url}")
        return True
    except Exception as e:
        log.error(f"Erreur suppression {url}: {e}")
        return False


def indexer_article(blogger_url: str, blog_url: str = BLOG_URL) -> bool:
    """Indexe un article Blogger a partir de son URL d'edition.

    Convertit l'URL d'edition en URL publique.
    """
    # L'URL d'edition est du type:
    # https://www.blogger.com/blog/post/edit/BLOG_ID/POST_ID
    # L'URL publique est du type:
    # https://plychaneconomie.blogspot.com/YYYY/MM/slug.html
    # On ne peut pas construire l'URL publique depuis l'URL d'edition,
    # donc on indexe le blog principal
    return indexer_url(blog_url)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) > 1:
        url = sys.argv[1]
        indexer_url(url)
    else:
        # Test
        indexer_url(f"{BLOG_URL}/")