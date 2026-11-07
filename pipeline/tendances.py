"""tendances.py — Veille tendances multi-plateformes (TrendsMCP + Reddit + CoinGecko).

Remplace/complemente la veille RSS actuelle avec des donnees de tendances reelles.
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("tendances")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def get_trending_topics(keywords: List[str], platforms: List[str] = None) -> List[Dict]:
    """Recupere les tendances de recherche multi-plateformes.

    Combine TrendsMCP (si disponible) + Reddit trending + CoinGecko.
    Retourne une liste de sujets tries par score viral.
    """
    if platforms is None:
        platforms = ["youtube", "reddit"]

    results = []

    # 1. TrendsMCP (si cle disponible)
    try:
        import config
        trends_key = getattr(config, "TRENDSMCP_API_KEY", "")
    except Exception:
        trends_key = os.getenv("TRENDSMCP_API_KEY", "")

    if trends_key:
        try:
            import requests
            for kw in keywords:
                resp = requests.get(
                    "https://api.trendsmcp.com/v1/trends",
                    params={"query": kw, "sources": ",".join(platforms), "lang": "fr"},
                    headers={"Authorization": f"Bearer {trends_key}"},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for trend in data.get("trends", []):
                        results.append({
                            "term": trend.get("term", kw),
                            "score": trend.get("score", 50),
                            "source": trend.get("source", "trendsmcp"),
                            "keyword": kw,
                        })
                    log.info(f"TrendsMCP '{kw}': {len(data.get('trends', []))} tendances")
        except Exception as e:
            log.warning(f"TrendsMCP echoue: {e}")

    # 2. Reddit trending (sans auth via JSON API)
    try:
        import requests
        for sub in ["economy", "finance", "worldnews", "investing"]:
            resp = requests.get(
                f"https://www.reddit.com/r/{sub}/hot.json",
                params={"limit": 10, "raw_json": 1},
                headers={"User-Agent": "PlyChanBot/1.0"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                for post in data.get("data", {}).get("children", []):
                    p = post["data"]
                    score = p.get("score", 0)
                    if score > 500:  # Seuil de viralite
                        results.append({
                            "term": p.get("title", ""),
                            "score": min(100, score // 100),
                            "source": "reddit",
                            "subreddit": sub,
                            "url": f"https://reddit.com{p.get('permalink', '')}",
                        })
    except Exception as e:
        log.warning(f"Reddit trending echoue: {e}")

    # 3. CoinGecko (si sujet crypto/finance)
    try:
        import requests
        resp = requests.get(
            "https://api.coingecko.com/api/v3/search/trending",
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            for coin in data.get("coins", [])[:5]:
                item = coin.get("item", {})
                results.append({
                    "term": f"{item.get('name', '')} ({item.get('symbol', '')})",
                    "score": 70,
                    "source": "coingecko",
                    "type": "crypto",
                })
    except Exception as e:
        log.warning(f"CoinGecko trending echoue: {e}")

    # Trier par score decroissant
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    log.info(f"Tendances totales: {len(results)}")
    return results[:20]


def get_wallstreetbets_sentiment(ticker: str = "BTC") -> Dict:
    """Sentiment Reddit finance (WallstreetBets)."""
    try:
        import requests
        resp = requests.get(
            f"https://api.tradestie.com/api/v1/apps/reddit?date={datetime.now().strftime('%Y-%m-%d')}",
            timeout=15,
            verify=False,
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                if item.get("ticker", "").upper() == ticker.upper():
                    return {
                        "ticker": ticker,
                        "sentiment": item.get("sentiment", "neutral"),
                        "mentions": item.get("no_of_comments", 0),
                        "score": item.get("sentiment_score", 0),
                    }
    except Exception as e:
        log.warning(f"WallstreetBets echoue: {e}")
    return {"ticker": ticker, "sentiment": "neutral", "mentions": 0, "score": 0}


def enrichir_sujet_avec_tendances(fait: dict) -> dict:
    """Enrichit un sujet d'actualite avec des donnees de tendances.

    Ajoute au fait:
    - tendance_score: score viral du sujet
    - sentiment: sentiment Reddit finance
    - mots_cles_tendance: mots-cles associes
    """
    titre = fait.get("titre", "")
    mots = titre.split()[:5]

    tendances = get_trending_topics(mots)
    sentiment = get_wallstreetbets_sentiment("BTC")

    fait["tendance_score"] = tendances[0]["score"] if tendances else 50
    fait["sentiment_finance"] = sentiment
    fait["tendances_associees"] = [t["term"] for t in tendances[:5]]

    return fait


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", nargs="+", default=["economie", "inflation", "emploi"])
    parser.add_argument("--sentiment", type=str, default="BTC")
    args = parser.parse_args()

    if args.keywords:
        trends = get_trending_topics(args.keywords)
        for t in trends[:10]:
            print(f"  [{t['score']}] {t['term'][:60]} ({t['source']})")

    sentiment = get_wallstreetbets_sentiment(args.sentiment)
    print(f"\nSentiment {args.sentiment}: {sentiment}")