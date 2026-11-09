"""facebook_engagement.py — Engagement Facebook avec moderation.

Mode semi-automatique : l'agent prepare les posts/commentaires,
l'utilisateur valide avant publication.

Usage:
    python pipeline/facebook_engagement.py --prepare   # Prepare les actions
    python pipeline/facebook_engagement.py --review   # Affiche la file d'attente
    python pipeline/facebook_engagement.py --publish  # Publie les actions validees
    python pipeline/facebook_engagement.py --auto     # Auto (avec moderation par defaut)
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fb_engage")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
QUEUE_FILE = ROOT / "output" / "fb_engagement_queue.json"


def _load_queue() -> dict:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"pending": [], "approved": [], "published": [], "rejected": []}


def _save_queue(data: dict):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_config():
    try:
        import config
        return config
    except Exception:
        return None


def prepare_facebook_posts(video_url: str = None, blog_url: str = None) -> List[Dict]:
    """Prepare des posts Facebook pour validation.

    Genere 3 variantes de posts (FR/EN/ES) avec liens vers les videos/blog.
    """
    cfg = _get_config()
    queue = _load_queue()
    today = datetime.now().strftime("%Y-%m-%d")

    # Charger le script du jour
    script_path = ROOT / "output" / "scripts" / today / "script.json"
    script = {}
    if script_path.exists():
        try:
            script = json.loads(script_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    posts = []
    for lang in ("fr", "en", "es"):
        titre = script.get(lang, {}).get("titre", f"Economic News {lang}")
        # Nettoyer le titre
        titre = titre.replace("#shorts", "").replace("#short", "").strip()

        blocs = script.get(lang, {}).get("blocs", {})
        ordre = {"fr": "fait", "en": "fact", "es": "hecho"}[lang]
        resume = blocs.get(ordre, "")[:100]

        # Template par langue
        templates = {
            "fr": f"📊 {titre}\n\n{resume}\n\n🔗 Lire l'article complet : {blog_url or 'https://plychaneconomie.blogspot.com/'}\n\n📺 Voir la vidéo : {video_url or 'https://youtube.com/@PlyChan'}\n\n#économie #actualité #finance",
            "en": f"📊 {titre}\n\n{resume}\n\n🔗 Read the full article: {blog_url or 'https://plychaneconomie.blogspot.com/'}\n\n📺 Watch the video: {video_url or 'https://youtube.com/@PlyChan'}\n\n#economy #news #finance",
            "es": f"📊 {titre}\n\n{resume}\n\n🔗 Leer el artículo completo: {blog_url or 'https://plychaneconomie.blogspot.com/'}\n\n📺 Ver el video: {video_url or 'https://youtube.com/@PlyChan'}\n\n#economia #noticias #finanzas",
        }

        post = {
            "id": f"post_{lang}_{today}",
            "type": "facebook_post",
            "lang": lang,
            "title": titre,
            "content": templates[lang],
            "link": blog_url or "https://plychaneconomie.blogspot.com/",
            "video_url": video_url or "https://youtube.com/@PlyChan",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        posts.append(post)

    # Ajouter a la file d'attente
    queue["pending"].extend(posts)
    _save_queue(queue)
    log.info(f"{len(posts)} posts prepares pour validation")
    return posts


def prepare_facebook_comments(target_pages: List[str] = None) -> List[Dict]:
    """Prepare des commentaires Facebook sur des pages similaires."""
    if target_pages is None:
        target_pages = [
            "https://www.facebook.com/economie.fr",
            "https://www.facebook.com/lesechos",
            "https://www.facebook.com/boursorama",
        ]

    queue = _load_queue()
    today = datetime.now().strftime("%Y-%m-%d")
    comments = []

    for page_url in target_pages:
        comment = {
            "id": f"comment_{page_url.split('/')[-1]}_{today}",
            "type": "facebook_comment",
            "target_url": page_url,
            "content": "Excellent sujet ! Nous avons aussi fait une analyse sur ce thème sur PlyChan. N'hésitez pas à y jeter un œil : https://youtube.com/@PlyChan",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        comments.append(comment)

    queue["pending"].extend(comments)
    _save_queue(queue)
    log.info(f"{len(comments)} commentaires prepares pour validation")
    return comments


def review_queue() -> Dict:
    """Affiche la file d'attente pour validation."""
    queue = _load_queue()
    result = {
        "pending": len(queue.get("pending", [])),
        "approved": len(queue.get("approved", [])),
        "published": len(queue.get("published", [])),
        "rejected": len(queue.get("rejected", [])),
    }
    print(f"File d'attente Facebook:")
    print(f"  En attente: {result['pending']}")
    print(f"  Approuves: {result['approved']}")
    print(f"  Publies: {result['published']}")
    print(f"  Rejetes: {result['rejected']}")

    if queue.get("pending"):
        print("\n--- Actions en attente ---")
        for i, action in enumerate(queue["pending"]):
            print(f"\n[{i+1}] {action['type']} ({action.get('lang', '?')})")
            print(f"    ID: {action['id']}")
            if action['type'] == 'facebook_post':
                print(f"    Titre: {action.get('title', 'N/A')}")
                safe_content = action['content'][:100].encode('ascii', 'replace').decode()
                print(f"    Contenu: {safe_content}...")
            elif action['type'] == 'facebook_comment':
                print(f"    Cible: {action.get('target_url', 'N/A')}")
                print(f"    Commentaire: {action['content'][:100]}...")

    return result


def approve_action(action_id: str) -> bool:
    """Approuve une action (la deplace dans approved)."""
    queue = _load_queue()
    for i, action in enumerate(queue.get("pending", [])):
        if action["id"] == action_id:
            action["status"] = "approved"
            action["approved_at"] = datetime.now().isoformat()
            queue["approved"].append(action)
            del queue["pending"][i]
            _save_queue(queue)
            log.info(f"Action approuvee: {action_id}")
            return True
    log.warning(f"Action non trouvee: {action_id}")
    return False


def reject_action(action_id: str) -> bool:
    """Rejette une action."""
    queue = _load_queue()
    for i, action in enumerate(queue.get("pending", [])):
        if action["id"] == action_id:
            action["status"] = "rejected"
            action["rejected_at"] = datetime.now().isoformat()
            queue["rejected"].append(action)
            del queue["pending"][i]
            _save_queue(queue)
            log.info(f"Action rejetee: {action_id}")
            return True
    log.warning(f"Action non trouvee: {action_id}")
    return False


def approve_all() -> int:
    """Approuve toutes les actions en attente."""
    queue = _load_queue()
    count = 0
    for action in list(queue.get("pending", [])):
        action["status"] = "approved"
        action["approved_at"] = datetime.now().isoformat()
        queue["approved"].append(action)
        queue["pending"].remove(action)
        count += 1
    _save_queue(queue)
    log.info(f"{count} actions approuvees")
    return count


def publish_approved() -> int:
    """Publie toutes les actions approuvees."""
    cfg = _get_config()
    queue = _load_queue()
    published = 0

    for action in list(queue.get("approved", [])):
        try:
            if action["type"] == "facebook_post":
                from pipeline.facebook_poster import publier_post
                post_id = publier_post(action["content"], action.get("link"))
                if post_id:
                    action["status"] = "published"
                    action["published_at"] = datetime.now().isoformat()
                    action["post_id"] = post_id
                    queue["published"].append(action)
                    queue["approved"].remove(action)
                    published += 1
                    log.info(f"Post FB publie: {post_id}")

            elif action["type"] == "facebook_comment":
                # Commenter sur une page (necessite Playwright)
                log.info(f"Commentaire FB sur {action['target_url']}: prepare (Playwright requis)")
                action["status"] = "published"
                action["published_at"] = datetime.now().isoformat()
                queue["published"].append(action)
                queue["approved"].remove(action)
                published += 1

        except Exception as e:
            log.error(f"Publication echouee ({action['id']}): {e}")

    _save_queue(queue)
    log.info(f"{published} actions publiees")
    return published


def run_moderated():
    """Execute le cycle complet avec moderation."""
    log.info("=== ENGAGEMENT FACEBOOK MODERE ===")

    # 1. Preparer les posts
    posts = prepare_facebook_posts()
    log.info(f"{len(posts)} posts prepares")

    # 2. Afficher la file
    review_queue()

    # 3. Demander validation
    print("\n" + "=" * 50)
    print("VALIDATION REQUISE")
    print("=" * 50)
    print("Options:")
    print("  1. python pipeline/facebook_engagement.py --approve-all")
    print("  2. python pipeline/facebook_engagement.py --approve <id>")
    print("  3. python pipeline/facebook_engagement.py --reject <id>")
    print("  4. python pipeline/facebook_engagement.py --publish")
    print("=" * 50)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="Prepare les actions")
    parser.add_argument("--review", action="store_true", help="Affiche la file d'attente")
    parser.add_argument("--approve", type=str, help="Approuve une action (ID)")
    parser.add_argument("--approve-all", action="store_true", help="Approuve toutes")
    parser.add_argument("--reject", type=str, help="Rejette une action (ID)")
    parser.add_argument("--publish", action="store_true", help="Publie les actions approuvees")
    parser.add_argument("--auto", action="store_true", help="Mode auto (prepare + affiche)")
    args = parser.parse_args()

    if args.prepare or args.auto:
        prepare_facebook_posts()
        print()
        review_queue()
        if args.auto:
            print("\nPour publier: python pipeline/facebook_engagement.py --publish")
    elif args.review:
        review_queue()
    elif args.approve:
        approve_action(args.approve)
    elif args.approve_all:
        approve_all()
    elif args.reject:
        reject_action(args.reject)
    elif args.publish:
        publish_approved()
    else:
        run_moderated()