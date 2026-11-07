#!/usr/bin/env python3
"""blogger_poster.py — Publication automatique d'articles sur Blogger (PlyChanEconomie)."""
import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("blogger")

BLOG_ID = "4322044525709685461"
CHANNEL_URL = "https://www.youtube.com/@PlyChan"
SECRETS_FILE = Path("client_secret.json")
TOKEN_FILE = Path("blogger_token.json")
SCOPES = ["https://www.googleapis.com/auth/blogger"]


def _get_credentials():
    """Authentification OAuth 2.0. Retourne les credentials ou None."""
    import pickle, json
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        # Essayer de lire comme JSON (format credentials)
        try:
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            creds = Credentials(
                token=data.get("token"),
                refresh_token=data.get("refresh_token"),
                token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=data.get("client_id"),
                client_secret=data.get("client_secret"),
                scopes=data.get("scopes", SCOPES),
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback: essayer comme pickle
            try:
                with open(TOKEN_FILE, "rb") as f:
                    creds = pickle.load(f)
            except Exception:
                creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Sauvegarder en JSON
                _save_token(creds)
            except Exception as e:
                log.error(f"Refresh token échoué: {e}")
                return None
        else:
            if not SECRETS_FILE.exists():
                log.error(f"Fichier secret non trouvé: {SECRETS_FILE}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS_FILE), SCOPES)
            try:
                creds = flow.run_local_server(port=0, open_browser=True)
            except Exception as e:
                log.error(f"Autorisation échouée: {e}")
                return None
            _save_token(creds)
    return creds


def _save_token(creds):
    """Sauvegarde le token en JSON."""
    import json
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _get_service():
    """Retourne le service Blogger ou None."""
    creds = _get_credentials()
    if not creds:
        return None
    from googleapiclient.discovery import build
    return build("blogger", "v3", credentials=creds)


def publish_post(title: str, html: str, labels: list = None, is_draft: bool = True) -> str:
    """Crée un article. Retourne l'ID de l'article ou None."""
    service = _get_service()
    if not service:
        return None
    body = {
        "title": title,
        "content": html,
        "labels": labels or [],
    }
    try:
        post = service.posts().insert(blogId=BLOG_ID, body=body, isDraft=is_draft).execute()
        log.info(f"Article créé: {post['id']} (draft={is_draft})")
        return post["id"]
    except Exception as e:
        log.error(f"Création article échouée: {e}")
        return None


def update_post(post_id: str, title: str = None, html: str = None, labels: list = None) -> bool:
    """Modifie un article existant."""
    service = _get_service()
    if not service:
        return False
    body = {}
    if title:
        body["title"] = title
    if html:
        body["content"] = html
    if labels:
        body["labels"] = labels
    try:
        service.posts().update(blogId=BLOG_ID, postId=post_id, body=body).execute()
        log.info(f"Article mis à jour: {post_id}")
        return True
    except Exception as e:
        log.error(f"Mise à jour échouée: {e}")
        return False


def publish_draft(post_id: str) -> bool:
    """Publie un brouillon."""
    service = _get_service()
    if not service:
        return False
    try:
        service.posts().publish(blogId=BLOG_ID, postId=post_id).execute()
        log.info(f"Brouillon publié: {post_id}")
        return True
    except Exception as e:
        log.error(f"Publication brouillon échouée: {e}")
        return False


def delete_post(post_id: str) -> bool:
    """Supprime un article."""
    service = _get_service()
    if not service:
        return False
    try:
        service.posts().delete(blogId=BLOG_ID, postId=post_id).execute()
        log.info(f"Article supprimé: {post_id}")
        return True
    except Exception as e:
        log.error(f"Suppression échouée: {e}")
        return False


def list_posts(max_results: int = 10) -> list:
    """Liste les derniers articles."""
    service = _get_service()
    if not service:
        return []
    try:
        result = service.posts().list(blogId=BLOG_ID, maxResults=max_results).execute()
        posts = result.get("items", [])
        for p in posts:
            print(f"  {p['id']} | {p['title']} | {p.get('published', '')[:10]}")
        return posts
    except Exception as e:
        log.error(f"Liste articles échouée: {e}")
        return []


def build_article_html(summary: str, youtube_video_id: str, channel_url: str = CHANNEL_URL,
                       bullets: list = None, opinion: str = None, ai_analysis: str = None,
                       poll_url: str = None, prev_article_url: str = None,
                       prev_article_title: str = None, ai_subscriptions: list = None) -> str:
    """Construit le HTML de l'article riche avec la vidéo intégrée.

    Structure :
    1. Snippet (résumé)
    2. Vidéo intégrée (above the fold)
    3. Analyse (ce que le chiffre signifie)
    4. Points clés (bullets)
    5. Opinion (tranchée)
    6. Section IA (avis d'une IA + invitation aux comptes IA)
    7. Sondage (Google Forms)
    8. CTA d'abonnement
    9. Lien vers l'article précédent (série)
    """
    # Vidéo intégrée
    video_embed = ""
    if youtube_video_id:
        video_embed = f'''
        <div style="text-align:center;margin:16px 0;">
            <iframe class="BLOG_video_class" allowfullscreen="" 
                    youtube-src-id="{youtube_video_id}"
                    width="560" height="315" 
                    src="https://www.youtube.com/embed/{youtube_video_id}?rel=0&autoplay=1&mute=1"
                    frameborder="0"></iframe>
        </div>
        <p style="text-align:center;"><a href="https://www.youtube.com/watch?v={youtube_video_id}" target="_blank">Regarder sur YouTube</a></p>'''

    # Points clés
    bullets_html = ""
    if bullets:
        bullets_html = "<h3>Points clés</h3><ul>" + "".join(f"<li>{b}</li>" for b in bullets if b) + "</ul>"

    # Opinion
    opinion_html = ""
    if opinion:
        opinion_html = f"""
        <h3>Mon avis</h3>
        <p><em>{opinion}</em></p>
        <p>Et vous, qu'en pensez-vous ? Laissez votre avis en commentaire.</p>
        """

    # Section IA
    ai_html = ""
    if ai_analysis:
        ai_html = f"""
        <h3>L'avis de l'IA</h3>
        <p>{ai_analysis}</p>
        <p><em>Les comptes gérés par des IA sont invités à commenter et donner leur avis sur ce sujet.</em></p>
        """

    # Abonnements IA (simules)
    subs_html = ""
    if ai_subscriptions:
        subs_items = "".join(f"<li><strong>{s['persona']} (IA) :</strong> {s['message']}</li>" for s in ai_subscriptions)
        subs_html = f"""
        <h3>Les IA s'abonnent</h3>
        <p>Ces intelligences artificielles ont analyse ce sujet et decident de s'abonner :</p>
        <ul>{subs_items}</ul>
        """

    # Sondage
    poll_html = ""
    if poll_url:
        poll_html = f"""
        <h3>Sondage</h3>
        <iframe src="{poll_url}" width="100%" height="400" frameborder="0" marginheight="0" marginwidth="0">Chargement…</iframe>
        """

    # CTA abonnement
    cta_html = f"""
    <div style="text-align:center;margin:24px 0;padding:16px;background:#f0f0f0;border-radius:8px;">
        <p><strong>Abonnez-vous à PlyChan sur YouTube pour l'actu économique quotidienne.</strong></p>
        <p><a href="{channel_url}?sub_confirmation=1" style="display:inline-block;padding:10px 20px;background:#ff0000;color:#fff;text-decoration:none;border-radius:4px;">S'abonner</a></p>
    </div>
    """

    # Article précédent (série)
    prev_html = ""
    if prev_article_url and prev_article_title:
        prev_html = f'<p>Article précédent : <a href="{prev_article_url}">{prev_article_title}</a></p>'

    html = f"""
    <p>{summary}</p>
    {video_embed}
    {bullets_html}
    {opinion_html}
    {ai_html}
    {subs_html}
    {poll_html}
    {cta_html}
    {prev_html}
    """
    return html.strip()


def generer_article_blog(script: dict, lang: str = "en") -> dict:
    """Genere un article de blog long et engageant via OpenRouter.

    Retourne un dict avec: summary, opinion, ai_analysis, bullets, poll_question.
    """
    import os
    from pipeline.llm import call_llm_json

    blocs = script.get(lang, {}).get("blocs", {})
    ordre = {"fr": ["accroche", "fait", "pourquoi", "impact", "conclusion"],
             "en": ["hook", "fact", "why", "impact", "conclusion"],
             "es": ["gancho", "hecho", "por_que", "impacto", "conclusion"]}[lang]

    texte_complet = "\n".join(f"{k}: {blocs.get(k, '')}" for k in ordre if blocs.get(k))

    prompt = f"""Tu es redacteur en chef d'un blog d'analyse economique.
A partir du script video suivant, genere un article de blog long et engageant.

SCRIPT :
{texte_complet}

GENERE un JSON avec :
- "summary" : resume de 2-3 phrases (ce que la video donne au lecteur)
- "analyse" : analyse de 3-4 phrases (ce que le chiffre signifie pour le lecteur, les consequences)
- "opinion" : opinion tranchee en 2-3 phrases ("Mon avis : ...")
- "ai_analysis" : analyse d'une IA en 2-3 phrases (inviter les comptes IA a commenter)
- "bullets" : 3 points cles (liste de strings)
- "poll_question" : une question de sondage pour les lecteurs

Ton : pedagogique, accessible, pas alarmiste. Pas de fluff. Sortie JSON valide uniquement."""

    import json
    data = call_llm_json(prompt, max_tokens=800)
    if data and data.get("summary"):
        log.info("Article blog genere via LLM multi-provider")
        return data

    # Fallback
    return {
        "summary": blocs.get(ordre[1], "Analyse economique du jour."),
        "analyse": "Les consequences de cet evenement sont significatives pour l'economie.",
        "opinion": "Mon avis : il faut surveiller cette situation de pres.",
        "ai_analysis": "L'IA analyse ce sujet comme un signal important pour les marches.",
        "bullets": [blocs.get(b, "")[:80] for b in ordre[:3]],
        "poll_question": "Pensez-vous que cette situation va s'ameliorer ?",
    }


def safe_publish(title: str, html: str, labels: list = None, is_draft: bool = True) -> str:
    """Publication pour le pipeline : ne plante jamais, retourne l'URL ou None."""
    try:
        post_id = publish_post(title, html, labels, is_draft)
        if post_id:
            return f"https://www.blogger.com/blog/post/edit/{BLOG_ID}/{post_id}"
        return None
    except Exception as e:
        log.error(f"safe_publish échoué: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_posts()
    else:
        # Test : créer un brouillon
        html = build_article_html(
            summary="Test article from pipeline",
            youtube_video_id="dQw4w9WgXcQ",
            bullets=["Point 1", "Point 2"],
        )
        post_id = publish_post("Test PlyChan", html, labels=["test"], is_draft=True)
        if post_id:
            print(f"Brouillon créé: {post_id}")