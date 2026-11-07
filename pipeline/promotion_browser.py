"""promotion_browser.py — Promotion via automatisation navigateur (sans API keys).

Utilise Playwright pour automatiser les interactions sur Reddit et Twitter/X.
Pas besoin de credentials API — utilise des sessions navigateur.

Usage:
    python pipeline/promotion_browser.py --reddit   # Promouvoir sur Reddit
    python pipeline/promotion_browser.py --twitter  # Promouvoir sur Twitter
    python pipeline/promotion_browser.py --all     # Les deux
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
log = logging.getLogger("promo_browser")

ROOT = Path(__file__).resolve().parent.parent
TRACKER_FILE = ROOT / "output" / "promo_browser_tracker.json"


def _load_tracker() -> dict:
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"reddit_comments": [], "twitter_tweets": [], "last_run": None}


def _save_tracker(data: dict):
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def reddit_promote(subreddits: List[str], video_url: str, comment_text: str) -> int:
    """Promouvoir sur Reddit via automatisation navigateur.

    Necessite Playwright et une session Reddit connectee.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright non installe. pip install playwright && playwright install")
        return 0

    tracker = _load_tracker()
    commented_urls = {c.get("url") for c in tracker.get("reddit_comments", [])}
    posted = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visible pour login manuel
        context = browser.new_context()
        page = context.new_page()

        for sub in subreddits:
            try:
                page.goto(f"https://www.reddit.com/r/{sub}/hot/", timeout=30000)
                time.sleep(3)

                # Trouver les posts recents
                posts = page.query_selector_all("a[data-click-id='body']")
                for post in posts[:5]:
                    try:
                        post_url = post.get_attribute("href")
                        if not post_url or post_url in commented_urls:
                            continue
                        if not post_url.startswith("http"):
                            post_url = "https://www.reddit.com" + post_url

                        # Ouvrir le post
                        page.goto(post_url, timeout=30000)
                        time.sleep(3)

                        # Trouver la zone de commentaire
                        comment_box = page.query_selector("div[contenteditable='true']")
                        if comment_box:
                            comment_box.click()
                            time.sleep(1)
                            page.keyboard.type(comment_text, delay=50)
                            time.sleep(2)
                            # Cliquer sur Commenter
                            submit = page.query_selector("button:has-text('Comment')")
                            if submit:
                                submit.click()
                                time.sleep(3)
                                posted += 1
                                log.info(f"Commentaire Reddit poste sur {sub}: {post_url[:60]}")
                                tracker["reddit_comments"].append({
                                    "subreddit": sub,
                                    "url": post_url,
                                    "date": datetime.now().strftime("%Y-%m-%d"),
                                })
                                _save_tracker(tracker)
                                commented_urls.add(post_url)
                    except Exception as e:
                        log.warning(f"Post Reddit {sub}: {e}")
                    time.sleep(10)  # rate limit

            except Exception as e:
                log.error(f"Subreddit {sub}: {e}")

        browser.close()

    log.info(f"Reddit: {posted} commentaires postes")
    return posted


def twitter_promote(tweet_text: str) -> bool:
    """Publie un tweet via automatisation navigateur.

    Necessite Playwright et une session Twitter connectee.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright non installe.")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto("https://x.com/compose/tweet", timeout=30000)
            time.sleep(5)

            # Trouver la zone de texte
            textbox = page.query_selector("div[contenteditable='true']")
            if textbox:
                textbox.click()
                time.sleep(1)
                page.keyboard.type(tweet_text, delay=50)
                time.sleep(2)

                # Cliquer sur Poster
                post_btn = page.query_selector("button:has-text('Post')")
                if post_btn:
                    post_btn.click()
                    time.sleep(5)
                    log.info("Tweet poste avec succes")
                    browser.close()
                    return True
        except Exception as e:
            log.error(f"Tweet echoue: {e}")

        browser.close()
        return False


def medium_promote(title: str, content: str, tags: List[str] = None) -> Optional[str]:
    """Publie un article sur Medium via automatisation navigateur."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright non installe.")
        return None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto("https://medium.com/new-story", timeout=30000)
            time.sleep(5)

            # Entrer le titre
            title_box = page.query_selector("h3, h4, [data-testid='storyTitle']")
            if title_box:
                title_box.click()
                time.sleep(1)
                page.keyboard.type(title, delay=50)
                time.sleep(2)

            # Entrer le contenu
            content_box = page.query_selector("div[contenteditable='true']")
            if content_box:
                content_box.click()
                time.sleep(1)
                page.keyboard.type(content, delay=30)
                time.sleep(2)

            # Publier
            publish_btn = page.query_selector("button:has-text('Publish')")
            if publish_btn:
                publish_btn.click()
                time.sleep(5)
                log.info("Article Medium publie")
                browser.close()
                return "published"

        except Exception as e:
            log.error(f"Medium echoue: {e}")

        browser.close()
        return None


def run_all(video_url: str = "https://youtube.com/@PlyChan", comment_text: str = None):
    """Execute la promotion sur toutes les plateformes."""
    if comment_text is None:
        comment_text = (
            "Excellent sujet ! J'ai aussi fait une video sur ce theme : " + video_url +
            " — n'hesitez pas a y jeter un oeil. Abonnez-vous pour plus d'analyses !"
        )

    tracker = _load_tracker()
    today = datetime.now().strftime("%Y-%m-%d")

    log.info("=== PROMOTION BROWSER ===")

    # Reddit
    subreddits = ["economy", "finance", "investing", "French", "economie"]
    reddit_posted = reddit_promote(subreddits, video_url, comment_text)
    log.info(f"Reddit: {reddit_posted} commentaires")

    # Twitter
    tweet = f"Nouvelle analyse economique sur PlyChan ! {video_url} #economie #finance #investing"
    twitter_ok = twitter_promote(tweet)
    log.info(f"Twitter: {'OK' if twitter_ok else 'ECHEC'}")

    tracker["last_run"] = today
    _save_tracker(tracker)

    log.info("=== TERMINE ===")
    return {"reddit": reddit_posted, "twitter": twitter_ok}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reddit", action="store_true", help="Promouvoir sur Reddit")
    parser.add_argument("--twitter", action="store_true", help="Promouvoir sur Twitter")
    parser.add_argument("--medium", action="store_true", help="Publier sur Medium")
    parser.add_argument("--all", action="store_true", help="Toutes les plateformes")
    args = parser.parse_args()

    if args.reddit:
        reddit_promote(["economy", "finance"], "https://youtube.com/@PlyChan", "Excellent sujet !")
    elif args.twitter:
        twitter_promote("Nouvelle analyse sur PlyChan ! https://youtube.com/@PlyChan")
    elif args.all:
        run_all()
    else:
        print("Usage: python promotion_browser.py --reddit|--twitter|--medium|--all")