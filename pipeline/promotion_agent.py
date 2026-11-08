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


def search_youtube_videos(query: str, max_results: int = 10,
                         min_views: int = 1000, max_views: int = 50000) -> List[Dict]:
    """Recherche des videos YouTube dans la niche economique.

    Filtre les videos par nombre de vues (min_views a max_views) pour cibler
    les videos avec assez de trafic mais pas trop de concurrence.
    """
    cfg = _load_config()
    try:
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", developerKey=cfg.YOUTUBE_API_KEY)
        resp = yt.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results * 2,  # Chercher plus pour compenser le filtrage
            order="date",
            relevanceLanguage="fr",
        ).execute()

        # Recuperer les video_ids pour obtenir les stats
        video_ids = [item["id"]["videoId"] for item in resp.get("items", [])]
        if not video_ids:
            return []

        # Obtenir les statistiques (vues) pour filtrer
        stats_resp = yt.videos().list(
            part="statistics,snippet",
            id=",".join(video_ids),
        ).execute()

        stats_map = {}
        for item in stats_resp.get("items", []):
            stats_map[item["id"]] = {
                "views": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
                "comments": int(item["statistics"].get("commentCount", 0)),
            }

        results = []
        for item in resp.get("items", []):
            vid = item["id"]["videoId"]
            stats = stats_map.get(vid, {})
            views = stats.get("views", 0)

            # Filtrer par nombre de vues
            if views < min_views or views > max_views:
                continue

            # Exclure nos propres videos
            channel = item["snippet"]["channelTitle"]
            if "plychan" in channel.lower():
                continue

            results.append({
                "video_id": vid,
                "title": item["snippet"]["title"],
                "channel": channel,
                "description": item["snippet"]["description"][:200],
                "url": f"https://youtube.com/watch?v={vid}",
                "views": views,
                "likes": stats.get("likes", 0),
                "comments": stats.get("comments", 0),
            })

            if len(results) >= max_results:
                break

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


def reply_to_comments() -> int:
    """Repond a TOUS les commentaires recus sur nos videos."""
    cfg = _load_config()
    replied = 0
    try:
        from pipeline.upload import get_authenticated_service
        yt = get_authenticated_service()

        # Lister nos videos recentes
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = yt.playlistItems().list(part="snippet", playlistId=uploads, maxResults=20).execute()

        for item in pl.get("items", []):
            vid = item["snippet"]["resourceId"]["videoId"]
            # Lister les commentaires de cette video
            try:
                comments = yt.commentThreads().list(
                    part="snippet", videoId=vid, maxResults=50
                ).execute()
                for thread in comments.get("items", []):
                    top = thread["snippet"]["topLevelComment"]["snippet"]
                    comment_text = top.get("textDisplay", "")
                    comment_author = top.get("authorDisplayName", "")
                    comment_id = thread["snippet"]["topLevelComment"]["id"]
                    # Ne pas repondre a nos propres commentaires
                    if comment_author.lower() in ("plychan", "plychaneco"):
                        continue
                    # Verifier si deja repondu
                    replies = thread.get("replies", {}).get("comments", [])
                    already_replied = any(
                        r["snippet"]["authorDisplayName"].lower() in ("plychan", "plychaneco")
                        for r in replies
                    )
                    if already_replied:
                        continue
                    # Generer une reponse
                    reply_text = _generate_reply(comment_text, "fr")
                    try:
                        yt.comments().insert(
                            part="snippet",
                            body={
                                "snippet": {
                                    "parentId": comment_id,
                                    "textOriginal": reply_text,
                                }
                            }
                        ).execute()
                        replied += 1
                        log.info(f"Reponse postee sur {vid}: {reply_text[:50]}")
                        time.sleep(1)
                    except Exception as e:
                        log.warning(f"Reponse echouee: {e}")
            except Exception as e:
                log.warning(f"Commentaires video {vid}: {e}")
    except Exception as e:
        log.error(f"reply_to_comments echoue: {e}")
    return replied


def _generate_reply(comment: str, lang: str = "fr") -> str:
    """Genere une reponse a un commentaire."""
    templates = {
        "fr": [
            "Merci pour ton commentaire ! N'hesite pas a t'abonner pour plus d'analyses.",
            "Merci ! Quel aspect t'interesse le plus ? Je peux faire une video dessus.",
            "Super remarque ! Je vais approfondir ce sujet dans une prochaine video.",
            "Merci de ton retour ! Abonne-toi pour ne rien rater.",
        ],
        "en": [
            "Thanks for your comment! Subscribe for more analysis.",
            "Great point! I'll cover this in more detail in an upcoming video.",
            "Thanks! What aspect interests you most? I can make a video about it.",
            "Appreciate the feedback! Subscribe to stay updated.",
        ],
        "es": [
            "Gracias por tu comentario! Suscribete para mas analisis.",
            "Buen punto! Profundizare en este tema en un proximo video.",
            "Gracias! Que aspecto te interesa mas? Puedo hacer un video sobre ello.",
            "Agradezco tu feedback! Suscribete para no perderte nada.",
        ],
    }
    import random
    return random.choice(templates.get(lang, templates["en"]))


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
        for sub in subreddits[:2]:
            try:
                r = requests.get(
                    f"https://www.reddit.com/r/{sub}/search.json",
                    params={"q": query, "restrict_sr": "on", "sort": "new", "limit": 3, "raw_json": 1},
                    headers={"User-Agent": "PlyChanBot/1.0 (by /u/plychan)"},
                    timeout=10,
                )
                if r.status_code == 200 and r.text:
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
                log.warning(f"Reddit {sub}: {e}")
            time.sleep(1)
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
    """Genere un commentaire promotionnel adapte a la plateforme (LLM + templates)."""
    # Essayer le LLM d'abord
    try:
        sys.path.insert(0, str(ROOT / "pipeline")) if str(ROOT / "pipeline") not in sys.path else None
        from llm import call_llm
        prompt = f"""Genere un commentaire YouTube court et naturel en {lang} pour promouvoir une chaine economique.
Le commentaire doit :
- Etre pertinent au sujet de la video: "{video_title}"
- Mentionner subtilement notre chaine: {video_url}
- Etre conversationnel, pas spammy
- Faire 1-2 phrases max
- Inclure un appel a l'action subtil (abonnez-vous, voir notre analyse)

Reponds UNIQUEMENT avec le commentaire, sans guillemets ni explication."""
        result = call_llm(prompt, max_tokens=100)
        if result and len(result) > 20 and len(result) < 300:
            return result.strip()
    except Exception:
        pass

    # Fallback templates
    templates = {
        "fr": [
            f"Excellent sujet ! J'ai aussi fait une video sur ce theme : {video_url} — n'hesitez pas a y jeter un oeil.",
            f"Pour aller plus loin sur ce sujet, j'ai publie une analyse complete ici : {video_url}",
            f"Je couvre aussi ce sujet en detail sur ma chaine : {video_url} — abonnez-vous pour plus d'analyses !",
        ],
        "en": [
            f"Great topic! I also made a video on this: {video_url} — check it out.",
            f"For a deeper dive, I published a full analysis here: {video_url}",
            f"I also cover this in detail on my channel: {video_url} — subscribe for more insights!",
        ],
        "es": [
            f"Excelente tema! Tambien hice un video sobre esto: {video_url} — echale un vistazo.",
            f"Para profundizar, publique un analisis completo aqui: {video_url}",
            f"Tambien cubro esto en detalle en mi canal: {video_url} — suscribete para mas analisis!",
        ],
    }
    import random
    return random.choice(templates.get(lang, templates["en"]))


def post_medium_article(title: str, content: str, tags: List[str] = None) -> Optional[str]:
    """Publie un article sur Medium (necessite un integration token)."""
    cfg = _load_config()
    token = getattr(cfg, "MEDIUM_TOKEN", "")
    if not token:
        log.warning("Medium: pas de token (MEDIUM_TOKEN requis)")
        return None
    try:
        import requests
        # Get user ID
        r = requests.get(
            "https://api.medium.com/v1/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        user_id = r.json()["data"]["id"]
        # Create post
        r = requests.post(
            f"https://api.medium.com/v1/users/{user_id}/posts",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "title": title,
                "contentFormat": "html",
                "content": content,
                "tags": tags or ["economy", "finance"],
                "publishStatus": "public",
            },
            timeout=30,
        )
        r.raise_for_status()
        post_url = r.json()["data"]["url"]
        log.info(f"Article Medium publie: {post_url}")
        return post_url
    except Exception as e:
        log.error(f"Medium echoue: {e}")
        return None


def post_reddit_comment(subreddit: str, post_id: str, comment_text: str) -> Optional[str]:
    """Poste un commentaire sur Reddit (necessite OAuth)."""
    # Reddit posting requires OAuth credentials
    cfg = _load_config()
    if not hasattr(cfg, "REDDIT_CLIENT_ID"):
        log.warning("Reddit: pas de credentials (REDDIT_CLIENT_ID requis)")
        return None
    try:
        import requests
        # Get access token
        auth = requests.auth.HTTPBasicAuth(cfg.REDDIT_CLIENT_ID, cfg.REDDIT_CLIENT_SECRET)
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": "PlyChanBot/1.0"},
            timeout=15,
        )
        r.raise_for_status()
        token = r.json()["access_token"]
        # Post comment
        r = requests.post(
            f"https://oauth.reddit.com/api/comment",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "PlyChanBot/1.0"},
            data={"thing_id": f"t3_{post_id}", "text": comment_text},
            timeout=15,
        )
        r.raise_for_status()
        comment_id = r.json().get("json", {}).get("data", {}).get("things", [{}])[0].get("data", {}).get("id")
        log.info(f"Commentaire Reddit poste: {comment_id}")
        return comment_id
    except Exception as e:
        log.error(f"Reddit comment echoue: {e}")
        return None


def optimize_thumbnail(title: str, blocs: dict) -> str:
    """Genere un texte de thumbnail optimise (3-4 mots max, different du titre)."""
    import re
    STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are", "with",
            "your", "you", "my", "i", "this", "that", "it", "how", "what", "why", "le", "la",
            "les", "de", "du", "des", "un", "une", "et", "ou", "est", "sont", "pour", "dans",
            "el", "la", "los", "las", "de", "del", "un", "una", "y", "o", "es", "son", "para", "en"}
    # Extraire les chiffres du titre
    nums = re.findall(r"\d[\d,.]*%?", title)
    if nums:
        return nums[0]
    # Prendre les mots significatifs des blocs
    all_text = " ".join(blocs.values()).lower()
    words = [w for w in re.findall(r"[a-zà-ÿ0-9']+", all_text) if w not in STOP and len(w) > 3]
    # Compter la frequence
    from collections import Counter
    counts = Counter(words)
    top = [w for w, _ in counts.most_common(3)]
    return " ".join(top).upper()[:20]


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

    # 2. Poster des commentaires sur les videos pertinentes (max 10 par run)
    commented_ids = {c["video_id"] for c in tracker.get("youtube_comments", [])}
    comments_posted = 0
    for video in external_videos[:10]:
        if video["video_id"] in commented_ids:
            continue
        if comments_posted >= 10:
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

    # 5. Repondre a TOUS les commentaires recus
    replied = reply_to_comments()
    log.info(f"Reponses aux commentaires: {replied}")

    # 6. Sauvegarder le tracker
    _save_tracker(tracker)
    log.info("=== PROMOTION TERMINEE ===")
    log.info(f"Commentaires YouTube: {comments_posted}")
    log.info(f"Reponses: {replied}")
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
            safe_title = r['title'][:60].encode('ascii', 'replace').decode()
            print(f"  {safe_title} - {r['channel']} | Views: {r.get('views', '?')}")
    elif args.comment:
        # Commenter sur les videos trouvees
        results = search_youtube_videos("économie actualité", max_results=3)
        for r in results:
            comment = generate_promo_comment(r["title"], "https://youtube.com/@PlyChan", "fr")
            print(f"Video: {r['title'][:40]}")
            print(f"  Commentaire: {comment[:80]}")
    else:
        result = run_promotion()
        print(json.dumps(result, indent=2, ensure_ascii=True))