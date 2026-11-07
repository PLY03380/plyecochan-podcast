"""promotion_apis.py — APIs gratuites du repo public-apis pour la promotion.

Integre des APIs gratuites pour ameliorer la promotion de PlyChan:
- TrendsMCP: tendances de recherche (Google, TikTok, YouTube, Amazon, Reddit)
- RedditAPIs: donnees Reddit sans OAuth
- GetXAPI: donnees Twitter/X
- CoinGecko: donnees crypto (pour contenu economique)
- Scrappa: resultats Google/YouTube structures

Usage:
    python pipeline/promotion_apis.py --trends "economie"  # Tendances
    python pipeline/promotion_apis.py --reddit "inflation"  # Posts Reddit
    python pipeline/promotion_apis.py --youtube "emploi"   # Videos YouTube
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("promo_apis")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def get_trends(keywords: List[str]) -> List[Dict]:
    """Recupere les tendances de recherche via TrendsMCP."""
    results = []
    try:
        import requests
        for kw in keywords:
            # TrendsMCP API
            r = requests.get(
                "https://api.trendsmcp.ai/trends",
                params={"keyword": kw, "platform": "youtube"},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                results.append({"keyword": kw, "data": data})
                log.info(f"Tendance '{kw}': OK")
            else:
                log.warning(f"TrendsMCP '{kw}': {r.status_code}")
    except Exception as e:
        log.error(f"TrendsMCP echoue: {e}")
    return results


def search_reddit_noauth(query: str, subreddits: List[str] = None) -> List[Dict]:
    """Recherche Reddit sans authentification via RedditAPIs."""
    if subreddits is None:
        subreddits = ["economy", "finance", "investing"]
    results = []
    try:
        import requests
        for sub in subreddits:
            r = requests.get(
                f"https://www.redditapis.com/v1/search",
                params={"q": query, "subreddit": sub, "limit": 10},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                for post in data.get("posts", []):
                    results.append({
                        "subreddit": sub,
                        "title": post.get("title", ""),
                        "url": post.get("url", ""),
                        "score": post.get("score", 0),
                    })
                log.info(f"Reddit '{sub}': {len(data.get('posts', []))} posts")
    except Exception as e:
        log.warning(f"RedditAPIs echoue: {e}")
        # Fallback: Reddit JSON API
        results = _reddit_fallback(query, subreddits)
    return results


def _reddit_fallback(query: str, subreddits: List[str]) -> List[Dict]:
    """Fallback: Reddit JSON API (sans auth)."""
    results = []
    try:
        import requests
        for sub in subreddits:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/search.json",
                params={"q": query, "restrict_sr": "on", "sort": "new", "limit": 5, "raw_json": 1},
                headers={"User-Agent": "PlyChanBot/1.0"},
                timeout=10,
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
                    })
    except Exception as e:
        log.error(f"Reddit fallback echoue: {e}")
    return results


def search_twitter_noauth(query: str, max_results: int = 10) -> List[Dict]:
    """Recherche Twitter/X via GetXAPI ou TwittrAPI."""
    results = []
    try:
        import requests
        # Try GetXAPI
        r = requests.get(
            "https://api.getxapi.com/v1/search",
            params={"q": query, "limit": max_results},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            for tweet in data.get("tweets", data.get("data", [])):
                results.append({
                    "tweet_id": tweet.get("id", ""),
                    "text": tweet.get("text", "")[:200],
                    "author": tweet.get("author", {}).get("username", ""),
                })
            log.info(f"GetXAPI: {len(results)} tweets")
            return results
    except Exception as e:
        log.warning(f"GetXAPI echoue: {e}")

    # Fallback: xfetch
    try:
        r = requests.get(
            "https://xfetch.io/api/search",
            params={"q": query, "limit": max_results},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            for tweet in data.get("results", []):
                results.append({
                    "tweet_id": tweet.get("id", ""),
                    "text": tweet.get("text", "")[:200],
                })
            log.info(f"xfetch: {len(results)} tweets")
    except Exception as e:
        log.warning(f"xfetch echoue: {e}")

    return results


def get_crypto_prices(symbols: List[str] = None) -> Dict:
    """Recupere les prix crypto via CoinGecko (pour contenu economique)."""
    if symbols is None:
        symbols = ["bitcoin", "ethereum", "gold"]
    try:
        import requests
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ",".join(symbols), "vs_currencies": "usd,eur", "include_24hr_change": "true"},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            log.info(f"CoinGecko: {len(data)} prix")
            return data
    except Exception as e:
        log.error(f"CoinGecko echoue: {e}")
    return {}


def search_youtube_transcripts(video_id: str) -> Optional[str]:
    """Recupere la transcription d'une video YouTube."""
    try:
        import requests
        # Try TranscriptYT
        r = requests.get(
            f"https://transcript-yt.com/api/transcript/{video_id}",
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("transcript", "")
    except Exception as e:
        log.warning(f"TranscriptYT echoue: {e}")

    # Fallback: youtube-transcript-api (local)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except Exception as e:
        log.warning(f"youtube-transcript-api echoue: {e}")
    return None


def get_social_analytics() -> Dict:
    """Recupere des analytics sociales via InsightSocial."""
    results = {}
    try:
        import requests
        # InsightSocial - public profiles from 25 platforms
        r = requests.get(
            "https://api.insightsocial.app/v1/profiles",
            params={"platform": "youtube", "handle": "PlyChan"},
            timeout=15,
        )
        if r.status_code == 200:
            results["insightsocial"] = r.json()
    except Exception as e:
        log.warning(f"InsightSocial echoue: {e}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--trends", nargs="+", help="Mots-cles pour les tendances")
    parser.add_argument("--reddit", type=str, help="Recherche Reddit")
    parser.add_argument("--twitter", type=str, help="Recherche Twitter")
    parser.add_argument("--crypto", action="store_true", help="Prix crypto")
    parser.add_argument("--transcript", type=str, help="Transcription YouTube (video_id)")
    args = parser.parse_args()

    if args.trends:
        results = get_trends(args.trends)
        print(json.dumps(results, indent=2, ensure_ascii=True))
    elif args.reddit:
        results = search_reddit_noauth(args.reddit)
        for r in results[:5]:
            print(f"  {r['title'][:60]} (score: {r['score']})")
    elif args.twitter:
        results = search_twitter_noauth(args.twitter)
        for r in results[:5]:
            print(f"  {r['text'][:60]}")
    elif args.crypto:
        prices = get_crypto_prices()
        print(json.dumps(prices, indent=2))
    elif args.transcript:
        text = search_youtube_transcripts(args.transcript)
        if text:
            print(text[:500])
        else:
            print("Pas de transcription disponible")
    else:
        print("Usage: python promotion_apis.py --trends KW1 KW2 | --reddit QUERY | --twitter QUERY | --crypto | --transcript VIDEO_ID")