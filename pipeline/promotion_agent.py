"""promotion_agent.py — Agent de promotion automatique pour PlyChan.

Promotion multi-plateformes :
- YouTube : recherche de videos economiques, commentaires strategiques
- Facebook : posts avec lien vers les videos/blog
- Twitter/X : tweets avec liens (si OAuth configure)
- Reddit : recherche de posts pertinents (lecture seule sans credentials)

Usage:
    python promotion_agent.py              # run complet
    python promotion_agent.py --search     # recherche uniquement
    python promotion_agent.py --comment    # commenter uniquement
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
log = logging.getLogger("promo")

ROOT = Path(__file__).resolve().parent.parent
PROMO_FILE = ROOT / "output" / "promotion_tracker.json"
CONFIG_FILE = ROOT / "config.py"


def _load_config():
    sys.path.insert(0, str(ROOT))
    import config
    return config


def _load_tracker() -> dict:
    if PROMO_FILE.exists():
        try:
            return json.loads(PROMO_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"youtube_comments": [], "facebook_posts": [], "twitter_tweets": [], "reddit_found": []}


def _save_tracker(data: dict):
    PROMO_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROMO_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def search_youtube_videos(query: str, max_results: int = 10) -> List[Dict]:
    """Recherche des videos YouTube dans la niche economique."""
    cfg = _load_config()
    try:
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", developerKey=cfg.YOUTUBE_API_KEY)
        resp = yt.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results,
            order="date",
            relevanceLanguage="fr",
        ).execute()
        results = []
        for item in resp.get("items", []):
            results.append({
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "description": item["snippet"]["description"][:200],
                "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
            })
        return results
    except Exception as e:
        log.error(f"Recherche YouTube echouee: {e}")
        return []


def post_youtube_comment(video_id: str, comment_text: str) -> Optional[str]:
    """Poste un commentaire sur une video YouTube (necessite OAuth)."""
    cfg = _load_config()
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
        log.info(f"Commentaire YouTube poste: {comment_id}")
        return comment_id
    except Exception as e:
        log.error(f"Commentaire YouTube echoue: {e}")
        return None


def post_facebook(text: str, link: str = None) -> Optional[str]:
    """Poste sur la page Facebook."""
    cfg = _load_config()
    try:
        import requests
        data = {"message": text, "access_token": cfg.FACEBOOK_PAGE_TOKEN}
        if link:
            data["link"] = link
        r = requests.post(
            f"https://graph.facebook.com/v21.0/{cfg.FACEBOOK_PAGE_ID}/feed",
            data=data, timeout=30,
        )
        r.raise_for_status()
        post_id = r.json().get("id")
        log.info(f"Post Facebook: {post_id}")
        return post_id
    except Exception as e:
        log.error(f"Post Facebook echoue: {e}")
        return None


def post_twitter(text: str) -> Optional[str]:
    """Poste un tweet (necessite OAuth 1.0a User Context)."""
    cfg = _load_config()
    # Twitter posting requires OAuth 1.0a User Context
    # Bearer token (App-Only) ne permet pas de poster
    if not hasattr(cfg, "TWITTER_ACCESS_TOKEN"):
        log.warning("Twitter: pas de access token (OAuth 1.0a requis pour poster)")
        return None
    try:
        import requests
        from requests_oauthlib import OAuth1
        auth = OAuth1(
            cfg.TWITTER_API_KEY,
            cfg.TWITTER_API_SECRET,
            cfg.TWITTER_ACCESS_TOKEN,
            cfg.TWITTER_ACCESS_TOKEN_SECRET,
        )
        r = requests.post(
            "https://api.twitter.com/2/tweets",
            json={"text": text},
            auth=auth, timeout=30,
        )
        r.raise_for_status()
        tweet_id = r.json().get("data", {}).get("id")
        log.info(f"Tweet poste: {tweet_id}")
        return tweet_id
    except Exception as e:
        log.error(f"Tweet echoue: {e}")
        return None


def search_reddit_posts(query: str, subreddits: List[str] = None) -> List[Dict]:
    """Recherche des posts Reddit pertinents (lecture seule)."""
    if subreddits is None:
        subreddits = ["economy", "finance", "investing", "economics", "French", "economie"]
    results = []
    try:
        import requests
        for sub in subreddits[:3]:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/search.json",
                params={"q": query, "restrict_sr": "on", "sort": "new", "limit": 5},
                headers={"User-Agent": "PlyChanBot/1.0"},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                for post in data.get("data", {}).get("children", []):
                    p = post["data"]
                    results.append({
                        "subreddit": sub,
                        "title": p.get("title", ""),
                        "url": f"https://reddit.com{p.get('permalink', '')}",
                        "score": p.get("score", 0),
                        "num_comments": p.get("num_comments", 0),
                    })
    except Exception as e:
        log.error(f"Recherche Reddit echouee: {e}")
    return results


def search_twitter_tweets(query: str, max_results: int = 10) -> List[Dict]:
    """Recherche des tweets pertinents (Bearer token)."""
    cfg = _load_config()
    try:
        import requests
        headers = {"Authorization": f"Bearer {cfg.TWITTER_BEARER_TOKEN}"}
        r = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            params={"query": query, "max_results": max_results},
            headers=headers, timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            results = []
            for tweet in data.get("data", []):
                results.append({
                    "tweet_id": tweet["id"],
                    "text": tweet["text"][:200],
                })
            return results
        else:
            log.warning(f"Twitter search: {r.status_code} {r.text[:100]}")
    except Exception as e:
        log.error(f"Recherche Twitter echouee: {e}")
    return []


def generate_promo_comment(video_title: str, video_url: str, lang: str = "fr") -> str:
    """Genere un commentaire promotionnel adapte a la plateforme."""
    templates = {
        "fr": [
            f"Excellent sujet ! J'ai aussi fait une video sur ce theme : {video_url} — n'hesitez pas a y jeter un oeil.",
            f"Pour aller plus loin sur ce sujet, j'ai publie une analyse complete ici : {video_url}",
            f"Je couvre aussi ce sujet en detail sur ma chaine : {video_url} — abonnez-vous pour plus d'analyses economiques !",
        ],
        "en": [
            f"Great topic! I also made a video on this: {video_url} — check it out.",
            f"For a deeper dive, I published a full analysis here: {video_url}",
            f"I also cover this in detail on my channel: {video_url} — subscribe for more economic insights!",
        ],
        "es": [
            f"Excelente tema! Tambien hice un video sobre esto: {video_url} — echale un vistazo.",
            f"Para profundizar, publique un analisis completo aqui: {video_url}",
            f"Tambien cubro esto en detalle en mi canal: {video_url} — suscribete para mas analisis economicos!",
        ],
    }
    import random
    return random.choice(templates.get(lang, templates["en"]))


def run_promotion():
    """Execute la promotion automatique."""
    cfg = _load_config()
    tracker = _load_tracker()
    today = datetime.now().strftime("%Y-%m-%d")

    log.info("=== AGENT DE PROMOTION ===")

    # 1. Rechercher des videos YouTube dans la niche
    queries = {
        "fr": ["économie actualité", "inflation France", "marché du travail"],
        "en": ["economy news", "inflation rate", "job market"],
        "es": ["economía noticias", "inflación", "mercado laboral"],
    }

    all_yt_results = []
    for lang, qs in queries.items():
        for q in qs:
            results = search_youtube_videos(q, max_results=5)
            all_yt_results.extend(results)
            log.info(f"YouTube search '{q}': {len(results)} resultats")
            time.sleep(1)  # rate limit

    # Filtrer les videos de notre propre chaine
    our_channel = "PlyChan"
    external_videos = [v for v in all_yt_results if our_channel.lower() not in v["channel"].lower()]
    log.info(f"Videos externes trouvees: {len(external_videos)}")

    # 2. Poster des commentaires sur les videos pertinentes (max 3 par run)
    commented_ids = {c["video_id"] for c in tracker.get("youtube_comments", [])}
    comments_posted = 0
    for video in external_videos[:3]:
        if video["video_id"] in commented_ids:
            continue
        if comments_posted >= 3:
            break
        comment = generate_promo_comment(
            video["title"], "https://youtube.com/@PlyChan", "fr"
        )
        comment_id = post_youtube_comment(video["video_id"], comment)
        if comment_id:
            tracker["youtube_comments"].append({
                "video_id": video["video_id"],
                "video_title": video["title"],
                "comment_id": comment_id,
                "date": today,
            })
            comments_posted += 1
            time.sleep(2)  # rate limit

    # 3. Rechercher des posts Reddit pertinents
    reddit_results = search_reddit_posts("economy inflation jobs", ["economy", "finance"])
    log.info(f"Reddit posts trouves: {len(reddit_results)}")
    tracker["reddit_found"].extend([
        {**r, "date": today} for r in reddit_results
        if r["url"] not in [x.get("url") for x in tracker.get("reddit_found", [])]
    ])

    # 4. Rechercher des tweets pertinents
    twitter_results = search_twitter_tweets("economy inflation jobs", max_results=5)
    log.info(f"Tweets trouves: {len(twitter_results)}")

    # 5. Poster sur Facebook (si pas deja fait aujourd'hui)
    fb_today = [p for p in tracker.get("facebook_posts", []) if p.get("date") == today]
    if not fb_today:
        # Chercher le dernier article publie
        published_file = ROOT / "output" / "published.json"
        if published_file.exists():
            published = json.loads(published_file.read_text(encoding="utf-8"))
            # Trouver la derniere date avec des URLs Blogger
            for date_key in sorted(published.keys(), reverse=True):
                blogger_urls = published[date_key].get("blogger", {})
                if blogger_urls:
                    for lang, url in blogger_urls.items():
                        post_id = post_facebook(
                            f"Nouvelle analyse economique sur PlyChan ! 📊\n\n"
                            f"Lire l'article complet : {url}\n\n"
                            f"Abonnez-vous sur YouTube : https://youtube.com/@PlyChan",
                            url,
                        )
                        if post_id:
                            tracker["facebook_posts"].append({
                                "post_id": post_id,
                                "url": url,
                                "date": today,
                            })
                    break

    # 6. Sauvegarder le tracker
    _save_tracker(tracker)
    log.info("=== PROMOTION TERMINEE ===")
    log.info(f"Commentaires YouTube: {comments_posted}")
    log.info(f"Posts Reddit trouves: {len(reddit_results)}")
    log.info(f"Tweets trouves: {len(twitter_results)}")

    return {
        "youtube_comments": comments_posted,
        "reddit_found": len(reddit_results),
        "twitter_found": len(twitter_results),
        "facebook_posted": len([p for p in tracker.get("facebook_posts", []) if p.get("date") == today]),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", action="store_true", help="Recherche uniquement")
    parser.add_argument("--comment", action="store_true", help="Commenter uniquement")
    args = parser.parse_args()

    if args.search:
        results = search_youtube_videos("économie actualité", max_results=5)
        for r in results:
            print(f"  {r['title'][:60]} - {r['channel']}")
    elif args.comment:
        # Commenter sur les videos trouvees
        results = search_youtube_videos("économie actualité", max_results=3)
        for r in results:
            comment = generate_promo_comment(r["title"], "https://youtube.com/@PlyChan", "fr")
            print(f"Video: {r['title'][:40]}")
            print(f"  Commentaire: {comment[:80]}")
    else:
        result = run_promotion()
        print(json.dumps(result, indent=2))