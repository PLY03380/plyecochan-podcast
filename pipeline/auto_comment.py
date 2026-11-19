"""auto_comment.py — Poste un commentaire epingle sur nos propres videos.

Strategie : poster un commentaire sur chaque nouvelle video avec :
- Un resume du sujet
- Un lien vers l'article du blog
- Un appel a l'action (abonnez-vous, commentez)

Usage:
    python pipeline/auto_comment.py              # aujourd'hui
    python pipeline/auto_comment.py 2026-11-13   # date specifique
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("auto_comment")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TRACKER_FILE = ROOT / "output" / "auto_comment_tracker.json"


def _load_tracker() -> dict:
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"commented_videos": []}


def _save_tracker(data: dict):
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_our_recent_videos(max_results: int = 10) -> List[Dict]:
    """Recupere nos videos recentes sur YouTube."""
    try:
        from googleapiclient.discovery import build
        import config
        yt = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = yt.playlistItems().list(part="snippet", playlistId=uploads, maxResults=max_results).execute()
        results = []
        for item in pl.get("items", []):
            results.append({
                "video_id": item["snippet"]["resourceId"]["videoId"],
                "title": item["snippet"]["title"],
                "published": item["snippet"]["publishedAt"],
            })
        return results
    except Exception as e:
        log.error(f"Erreur recuperation videos: {e}")
        return []


def generate_pinned_comment(title: str, lang: str = "fr") -> str:
    """Genere un commentaire epingle pour nos propres videos."""
    templates = {
        "fr": [
            f"📌 RÉSUMÉ : {title}\n\n🔗 Article complet sur le blog : https://plychaneconomie.blogspot.com/\n📺 Abonnez-vous pour ne rien rater !\n💬 Qu'en pensez-vous ? Commentez ci-dessous 👇",
            f"📊 ANALYSE : {title}\n\n🔗 Lire l'article détaillé : https://plychaneconomie.blogspot.com/\n📺 Abonnez-vous à PlyChan !\n💬 Votre avis ? 👇",
        ],
        "en": [
            f"📌 SUMMARY: {title}\n\n🔗 Full article on the blog: https://plychaneconomie.blogspot.com/\n📺 Subscribe for more! \n💬 What do you think? Comment below 👇",
            f"📊 ANALYSIS: {title}\n\n🔗 Read the detailed article: https://plychaneconomie.blogspot.com/\n📺 Subscribe to PlyChan!\n💬 Your thoughts? 👇",
        ],
        "es": [
            f"📌 RESUMEN: {title}\n\n🔗 Artículo completo en el blog: https://plychaneconomie.blogspot.com/\n📺 ¡Suscríbete para más!\n💬 ¿Qué opinas? Comenta abajo 👇",
            f"📊 ANÁLISIS: {title}\n\n🔗 Leer el artículo detallado: https://plychaneconomie.blogspot.com/\n📺 ¡Suscríbete a PlyChan!\n💬 ¿Tu opinión? 👇",
        ],
    }
    import random
    return random.choice(templates.get(lang, templates["en"]))


def post_pinned_comment(video_id: str, comment_text: str) -> Optional[str]:
    """Poste un commentaire sur notre propre video."""
    try:
        from pipeline.upload import get_authenticated_service
        yt = get_authenticated_service()
        resp = yt.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text,
                        }
                    }
                }
            }
        ).execute()
        comment_id = resp["id"]
        log.info(f"Commentaire epingle poste: {comment_id}")
        return comment_id
    except Exception as e:
        log.error(f"Commentaire epingle echoue: {e}")
        return None


def run_auto_comment(date_str: str = None):
    """Poste un commentaire epingle sur nos videos recentes."""
    tracker = _load_tracker()
    commented = {c["video_id"] for c in tracker.get("commented_videos", [])}

    videos = get_our_recent_videos(max_results=10)
    log.info(f"Videos recentes: {len(videos)}")

    posted = 0
    for video in videos:
        if video["video_id"] in commented:
            continue
        if posted >= 5:  # Max 5 par run
            break

        # Determiner la langue du titre
        title = video["title"]
        lang = "fr"
        if any(w in title.lower() for w in ["ai", "jobs", "economy", "market", "inflation"]):
            if "inflation" in title.lower() and "ce" in title.lower():
                lang = "fr"
            elif "november" in title.lower() or "jobs" in title.lower():
                lang = "en"
            elif "noviembre" in title.lower() or "empleo" in title.lower():
                lang = "es"

        comment = generate_pinned_comment(title, lang)
        comment_id = post_pinned_comment(video["video_id"], comment)
        if comment_id:
            tracker["commented_videos"].append({
                "video_id": video["video_id"],
                "title": title,
                "comment_id": comment_id,
                "date": datetime.now().strftime("%Y-%m-%d"),
            })
            posted += 1
            _save_tracker(tracker)
            log.info(f"  Commentaire epingle: {title[:40]}")

    log.info(f"Total: {posted} commentaires epingles")
    return posted


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_auto_comment(date_arg)