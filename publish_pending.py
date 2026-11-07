#!/usr/bin/env python3
"""publish_pending.py — Publie les articles Blogger et posts Facebook manquants.

Ce script ne relance PAS le pipeline complet. Il verifie quels videos
sont uploadees sur YouTube, quels articles Blogger existent, et quels
posts Facebook ont ete publies, puis complete ce qui manque.

Usage:
    python publish_pending.py          # aujourd'hui
    python publish_pending.py 2026-11-06  # date specifique
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("publish_pending")

ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "output" / "scripts"
PUBLISHED_FILE = ROOT / "output" / "published.json"


def get_published() -> dict:
    """Charge le suivi des publications."""
    if PUBLISHED_FILE.exists():
        try:
            return json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_published(data: dict):
    """Sauvegarde le suivi des publications."""
    PUBLISHED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUBLISHED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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


def get_uploaded_titles() -> dict:
    """Retourne un dict {titre_lower: video_id} des videos uploadees."""
    result = {}
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
                title = item["snippet"]["title"].lower().strip()
                vid = item["snippet"]["resourceId"]["videoId"]
                result[title] = vid
            page_token = pl.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        log.error(f"Impossible de recuperer les titres: {e}")
    return result


def find_script(date_str: str) -> dict:
    """Cherche le script JSON pour une date."""
    script_path = SCRIPTS_DIR / date_str / "script.json"
    if script_path.exists():
        try:
            return json.loads(script_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def publish_pending(date_str: str = None):
    """Publie les articles Blogger et posts Facebook manquants."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    log.info(f"=== PUBLISH PENDING - {date_str} ===")

    script = find_script(date_str)
    if not script:
        log.error(f"Pas de script JSON pour {date_str}")
        return

    published = get_published()
    if date_str not in published:
        published[date_str] = {"blogger": {}, "facebook": {}}

    # Recuperer les videos uploadees
    uploaded_titles = get_uploaded_titles()
    log.info(f"Videos uploadees sur YouTube: {len(uploaded_titles)}")

    # Pour chaque langue, trouver le video_id correspondant
    video_ids = {}
    for lang in ("fr", "en", "es"):
        titre = script.get(lang, {}).get("titre", "")
        if titre and titre.lower().strip() in uploaded_titles:
            video_ids[lang] = uploaded_titles[titre.lower().strip()]
            log.info(f"Video {lang}: {video_ids[lang]}")

    # Aussi verifier les videos longues
    long_video_ids = {}
    for lang in ("fr", "en", "es"):
        # Chercher par titre + "long" ou par nom de fichier
        titre = script.get(lang, {}).get("titre", "")
        # Les longues ont souvent un titre different
        for t, vid in uploaded_titles.items():
            if titre.lower().strip() in t and "long" not in t:
                # C'est probablement le short, pas le long
                pass
        # Pour les longues, on cherche dans les titres qui contiennent "analyse" ou "long"
        # Simpler: just use the video_ids we found (shorts)
        # Long videos are handled separately if needed

    # Publication Blogger
    blogger_secret = ROOT / "client_secret.json"
    if blogger_secret.exists():
        from blogger_poster import build_article_html, safe_publish, generer_article_blog
        blogger_urls = published[date_str].get("blogger", {})

        for lang in ("fr", "en", "es"):
            if lang in blogger_urls:
                log.info(f"Blogger {lang}: deja publie")
                continue

            video_id = video_ids.get(lang)
            if not video_id:
                log.warning(f"Blogger {lang}: pas de video_id, skip")
                continue

            try:
                article = generer_article_blog(script, lang=lang)
                titre = script.get(lang, {}).get("titre", f"Economic News {lang}")
                html = build_article_html(
                    summary=article["summary"],
                    youtube_video_id=video_id,
                    channel_url="https://www.youtube.com/@PlyChan",
                    bullets=article.get("bullets", []),
                    opinion=article.get("opinion"),
                    ai_analysis=article.get("ai_analysis"),
                )
                url = safe_publish(titre, html, labels=["economy", lang], is_draft=False)
                if url:
                    log.info(f"Article Blogger {lang} cree: {url}")
                    blogger_urls[lang] = url
                    published[date_str]["blogger"] = blogger_urls
                    save_published(published)
            except Exception as e:
                log.warning(f"Publication Blogger {lang} echouee: {e}")

        if blogger_urls:
            published[date_str]["blogger"] = blogger_urls
            save_published(published)

            # Indexation
            try:
                from pipeline.indexing import indexer_url
                indexer_url("https://plychaneconomie.blogspot.com/")
                log.info("Indexation Google demandee")
            except Exception as e:
                log.warning(f"Indexation Google echouee: {e}")

            try:
                from pipeline.indexing_bing import indexer_bing
                indexer_bing("https://plychaneconomie.blogspot.com/p/indexnow-key.html")
                log.info("Indexation Bing/DuckDuckGo demandee")
            except Exception as e:
                log.warning(f"Indexation Bing echouee: {e}")
    else:
        log.info("Blogger ignore (pas de client_secret.json)")

    # Publication Facebook
    fb_token = os.getenv("FACEBOOK_PAGE_TOKEN", "")
    if not fb_token:
        try:
            import config
            fb_token = getattr(config, "FACEBOOK_PAGE_TOKEN", "")
        except Exception:
            pass

    if fb_token:
        from pipeline.facebook_poster import safe_publish_facebook
        fb_posts = published[date_str].get("facebook", {})
        blogger_urls = published[date_str].get("blogger", {})

        for lang in ("fr", "en", "es"):
            if lang in fb_posts:
                log.info(f"Facebook {lang}: deja publie")
                continue

            titre = script.get(lang, {}).get("titre", "")
            blogger_url = blogger_urls.get(lang)
            if not titre or not blogger_url:
                continue

            try:
                post_id = safe_publish_facebook(
                    titre, blogger_url,
                    resume=script.get(lang, {}).get("blocs", {}).get(
                        {"fr": "fait", "en": "fact", "es": "hecho"}[lang], ""),
                )
                if post_id:
                    log.info(f"Post Facebook {lang} cree: {post_id}")
                    fb_posts[lang] = post_id
                    published[date_str]["facebook"] = fb_posts
                    save_published(published)
            except Exception as e:
                log.warning(f"Publication Facebook {lang} echouee: {e}")

        if fb_posts:
            published[date_str]["facebook"] = fb_posts
            save_published(published)
    else:
        log.info("Facebook ignore (pas de FACEBOOK_PAGE_TOKEN)")

    # Distribution multi-reseaux (Publora/PostLake)
    try:
        from pipeline.multi_social import distribuer_video_tous_reseaux
        for lang, url in blogger_urls.items():
            titre = script.get(lang, {}).get("titre", "")
            if titre and url:
                video_data = {
                    "titre": titre,
                    "url_youtube": f"https://youtube.com/watch?v={video_ids.get(lang, '')}",
                    "hashtags": ["economie", "finance", "actualite"],
                }
                distribuer_video_tous_reseaux(video_data)
                log.info(f"Distribution multi-reseaux {lang}: OK")
    except Exception as e:
        log.warning(f"Distribution multi-reseaux echouee: {e}")

    # Newsletter Brevo
    try:
        from pipeline.newsletter import envoyer_newsletter
        for lang, url in blogger_urls.items():
            titre = script.get(lang, {}).get("titre", "")
            if titre and url:
                video_id = video_ids.get(lang, "")
                youtube_url = f"https://youtube.com/watch?v={video_id}" if video_id else None
                envoyer_newsletter(titre, url, youtube_url)
                log.info(f"Newsletter {lang}: envoyee")
    except Exception as e:
        log.warning(f"Newsletter echouee: {e}")

    log.info("=== PUBLISH PENDING TERMINE ===")
    # Afficher le resume
    print(json.dumps(published.get(date_str, {}), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    publish_pending(date_arg)