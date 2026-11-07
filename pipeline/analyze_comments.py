"""analyze_comments.py — Analyse les commentaires YouTube et génère un sujet de vidéo longue."""
import json
import logging
import os
from pathlib import Path
from typing import List, Dict
from collections import Counter
import re

log = logging.getLogger("analyze_comments")

# Mots-clés thématiques pour catégoriser les commentaires
THEME_KEYWORDS = {
    "inflation": ["inflation", "prix", "cher", "coût", "pouvoir d'achat", "budget"],
    "emploi": ["emploi", "travail", "chômage", "salaire", "licenciement", "job"],
    "immobilier": ["immobilier", "logement", "loyer", "maison", "appartement", "hypothèque"],
    "or": ["or", "gold", "once", "lingot", "métal précieux"],
    "petrole": ["pétrole", "oil", "essence", "carburant", "énergie", "brent"],
    "taux": ["taux", "rate", "fed", "bce", "crédit", "prêt", "intérêts"],
    "crypto": ["crypto", "bitcoin", "blockchain", "ethereum"],
    "recession": ["récession", "crise", "effondrement", "krach"],
}


def get_video_comments(video_id: str, max_results: int = 100) -> List[str]:
    """Récupère les commentaires d'une vidéo YouTube."""
    try:
        import pickle
        creds = pickle.load(open(Path.home() / ".youtube_token.pickle", "rb"))
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", credentials=creds)
        comments = []
        page_token = None
        while len(comments) < max_results:
            resp = yt.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_results - len(comments)),
                pageToken=page_token,
                textFormat="plainText",
            ).execute()
            for item in resp.get("items", []):
                text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(text)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return comments
    except Exception as e:
        log.error(f"Erreur récupération commentaires YouTube: {e}")
        return []


def get_blog_comments(post_id: str, max_results: int = 100) -> List[str]:
    """Récupère les commentaires d'un article Blogger."""
    try:
        import pickle
        # Le token Blogger est en JSON, pas en pickle
        import json
        token_path = Path("blogger_token.json")
        if not token_path.exists():
            log.warning("blogger_token.json non trouvé")
            return []
        data = json.loads(token_path.read_text(encoding="utf-8"))
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes", ["https://www.googleapis.com/auth/blogger"]),
        )
        service = build("blogger", "v3", credentials=creds)
        comments = []
        page_token = None
        while len(comments) < max_results:
            resp = service.comments().listByPost(
                blogId="4322044525709685461",
                postId=post_id,
                maxResults=min(100, max_results - len(comments)),
                pageToken=page_token,
            ).execute()
            for item in resp.get("items", []):
                text = item.get("content", "")
                if text:
                    comments.append(text)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return comments
    except Exception as e:
        log.error(f"Erreur récupération commentaires Blogger: {e}")
        return []


def analyser_themes(comments: List[str]) -> Dict[str, int]:
    """Analyse les thèmes récurrents dans les commentaires."""
    themes = Counter()
    for comment in comments:
        text = comment.lower()
        for theme, keywords in THEME_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    themes[theme] += 1
                    break
    return dict(themes.most_common())


def generer_sujet_long(themes: Dict[str, int], comments: List[str]) -> dict:
    """Génère un sujet de vidéo longue basé sur les thèmes et commentaires."""
    # Thème le plus demandé
    top_theme = max(themes, key=themes.get) if themes else "economie"
    top_count = themes.get(top_theme, 0)

    # Extraire les questions des commentaires
    questions = [c for c in comments if "?" in c][:5]

    # Générer le sujet via LLM
    try:
        import config
        keys = config.OPENROUTER_KEYS
    except Exception:
        keys = [os.getenv("OPENROUTER_KEY_1", "")]

    from openai import OpenAI
    prompt = f"""Tu es un stratège YouTube pour une chaîne d'actualités économiques.
Analyse les données suivantes et propose un sujet de vidéo longue (10-15 minutes).

THÈMES LES PLUS DEMANDÉS PAR LE PUBLIC :
{json.dumps(themes, ensure_ascii=False)}

EXEMPLES DE COMMENTAIRES/QUESTIONS :
{chr(10).join(questions[:5]) if questions else "Pas de questions spécifiques."}

Génère un JSON avec :
- "titre" : titre de la vidéo longue (optimisé SEO, max 80 chars)
- "sujet" : description du sujet en 2-3 phrases
- "angle" : angle éditorial unique
- "structure" : liste de 5-7 sections pour la vidéo longue
- "duree_estimee" : durée estimée en minutes
- "mots_cles" : liste de 5 mots-clés pour le SEO

Sortie JSON uniquement."""

    for key in keys:
        try:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
            resp = client.chat.completions.create(
                model="google/gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=500,
            )
            content = resp.choices[0].message.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                content = content[start:end+1]
            data = json.loads(content)
            if data.get("titre"):
                log.info(f"Sujet long genere: {data['titre']}")
                return data
        except Exception as e:
            log.warning(f"Erreur LLM: {e}")
            continue

    # Fallback
    return {
        "titre": f"Guide complet : {top_theme} en 2026",
        "sujet": f"Analyse approfondie du thème {top_theme} demandé par le public.",
        "angle": "Explication pédagogique et accessible.",
        "structure": ["Introduction", "Contexte", "Analyse", "Impact", "Conclusion"],
        "duree_estimee": 10,
        "mots_cles": [top_theme, "économie", "2026"],
    }


def analyser_et_generer(video_id: str = None, comments: List[str] = None) -> dict:
    """Analyse les commentaires et génère un sujet de vidéo longue.

    Si video_id est fourni, récupère les commentaires de YouTube.
    Sinon, utilise la liste de commentaires fournie.
    """
    if video_id and not comments:
        comments = get_video_comments(video_id)
    if not comments:
        log.warning("Aucun commentaire disponible")
        return {}

    themes = analyser_themes(comments)
    log.info(f"Themes detectes: {themes}")

    sujet = generer_sujet_long(themes, comments)
    sujet["themes"] = themes
    sujet["nb_commentaires"] = len(comments)
    return sujet


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Test avec des commentaires simulés
    test_comments = [
        "J'aimerais comprendre l'inflation en détail",
        "Pourquoi le prix de l'or monte autant ?",
        "L'immobilier va-t-il baisser ?",
        "Comment protéger son épargne ?",
        "Excellent vidéo, mais j'aimerais plus de détails sur les taux",
        "Inflation trop élevée, comment survivre ?",
        "L'or c'est un bon investissement ?",
    ]
    result = analyser_et_generer(comments=test_comments)
    print(json.dumps(result, indent=2, ensure_ascii=False))