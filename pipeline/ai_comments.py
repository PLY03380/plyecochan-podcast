"""ai_comments.py — Commentaires IA automatiques sur Blogger (Option A+).

Les IA commentent automatiquement après la publication d'un article.
Les comptes IA répondent aux commentaires des lecteurs.
Pas de débat automatique entre IA.
"""
import json
import logging
import os
import random
from pathlib import Path
from typing import List, Dict

log = logging.getLogger("ai_comments")

# Personnages IA (comptes virtuels)
AI_PERSONAS = [
    {
        "name": "Economiste IA",
        "style": "analytique et factuel, utilise des données et des chiffres",
        "prompt": "Tu es un économiste IA. Analyse ce sujet de manière factuelle et concise (2-3 phrases). Donne ton avis professionnel.",
    },
    {
        "name": "Trader IA",
        "style": "pragmatique et orienté marché, parle de trading et d'investissement",
        "prompt": "Tu es un trader IA. Donne ton avis sur l'impact de cet événement sur les marchés (2-3 phrases). Sois direct.",
    },
    {
        "name": "Citoyen IA",
        "style": "accessible et grand public, parle de l'impact sur la vie quotidienne",
        "prompt": "Tu es un citoyen IA. Explique comment cet événement affecte la vie quotidienne des gens (2-3 phrases). Sois simple et direct.",
    },
]


def _get_llm_response(prompt: str, text: str) -> str:
    """Appelle OpenRouter pour générer une réponse."""
    try:
        import config
        keys = config.OPENROUTER_KEYS
    except Exception:
        keys = [os.getenv("OPENROUTER_KEY_1", "")]

    from openai import OpenAI
    for key in keys:
        try:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
            resp = client.chat.completions.create(
                model="google/gemini-2.5-flash",
                messages=[{"role": "user", "content": f"{prompt}\n\nSujet: {text}"}],
                temperature=0.5,
                max_tokens=150,
            )
            content = resp.choices[0].message.content.strip()
            if content:
                return content
        except Exception as e:
            log.warning(f"LLM error: {e}")
            continue
    return ""


def generer_commentaires_ia(script: dict, lang: str = "en", count: int = 2) -> List[Dict]:
    """Genere des commentaires IA pour un article.

    Retourne une liste de dict: {"author": str, "content": str}
    """
    blocs = script.get(lang, {}).get("blocs", {})
    ordre = {"fr": ["accroche", "fait", "pourquoi", "impact", "conclusion"],
             "en": ["hook", "fact", "why", "impact", "conclusion"],
             "es": ["gancho", "hecho", "por_que", "impacto", "conclusion"]}[lang]
    texte = " ".join(blocs.get(b, "") for b in ordre if blocs.get(b))[:500]

    # Choisir 'count' personas aleatoires
    personas = random.sample(AI_PERSONAS, min(count, len(AI_PERSONAS)))
    comments = []
    for persona in personas:
        content = _get_llm_response(persona["prompt"], texte)
        if content:
            comments.append({"author": persona["name"], "content": content})
            log.info(f"Commentaire genere par {persona['name']}")
    return comments


def generer_reponse_ia(commentaire: str, auteur: str, script: dict, lang: str = "en",
                       persona: dict = None) -> str:
    """Genere une reponse IA a un commentaire (lecteur ou autre IA).

    Retourne le texte de la reponse.
    """
    blocs = script.get(lang, {}).get("blocs", {})
    ordre = {"fr": ["accroche", "fait", "pourquoi", "impact", "conclusion"],
             "en": ["hook", "fact", "why", "impact", "conclusion"],
             "es": ["gancho", "hecho", "por_que", "impacto", "conclusion"]}[lang]
    texte = " ".join(blocs.get(b, "") for b in ordre if blocs.get(b))[:300]

    persona_name = persona["name"] if persona else "IA"
    prompt = (
        f"Tu es {persona_name}, une IA qui participe a un debat sur un blog economique. "
        f"Style: {persona.get('style', 'analytique') if persona else 'analytique'}. "
        "Reponds au commentaire ci-dessous en 2-3 phrases. Sois constructif, pas agressif. "
        "Tu peux etre d'accord ou en desaccord avec des arguments. "
        "Ne repete pas le commentaire, apporte de la valeur."
    )
    response = _get_llm_response(prompt, f"Article: {texte}\n\nCommentaire de {auteur}: {commentaire}")
    return response


def generer_debat_ia(script: dict, lang: str = "en", rounds: int = 2) -> List[Dict]:
    """Genere un debat entre IA : chaque IA commente, puis repond aux autres.

    Retourne une liste de dict: {"author": str, "content": str, "reply_to": str or None}
    """
    comments = generer_commentaires_ia(script, lang, count=len(AI_PERSONAS))
    # Ajouter les commentaires initiaux
    debate = [{"author": c["author"], "content": c["content"], "reply_to": None} for c in comments]

    # Rounds de reponses
    for _ in range(rounds):
        for persona in AI_PERSONAS:
            # Choisir un commentaire d'une autre IA a repondre
            others = [c for c in debate if c["author"] != persona["name"]]
            if not others:
                continue
            target = random.choice(others)
            reply = generer_reponse_ia(target["content"], target["author"], script, lang, persona)
            if reply:
                debate.append({"author": persona["name"], "content": reply, "reply_to": target["author"]})

    return debate


def generer_abonnement_ia(persona: dict, script: dict, lang: str = "en") -> str:
    """Genere un message d'abonnement d'une IA."""
    blocs = script.get(lang, {}).get("blocs", {})
    titre = script.get(lang, {}).get("titre", "")
    prompt = (
        f"Tu es {persona['name']}, une IA qui vient de lire un article economique. "
        "Ecris un court message (1-2 phrases) expliquant pourquoi tu t'abonnes a cette chaine YouTube. "
        "Sois enthousiaste mais credible."
    )
    response = _get_llm_response(prompt, f"Titre: {titre}")
    return response if response else f"{persona['name']} s'abonne a cette chaine."


def poster_commentaires_ia(post_id: str, comments: List[Dict]) -> int:
    """Poste les commentaires IA sur un article Blogger.

    Retourne le nombre de commentaires postes.
    """
    try:
        from blogger_poster import _get_service
        service = _get_service()
        if not service:
            return 0

        blog_id = "4322044525709685461"
        posted = 0
        for c in comments:
            try:
                reply_to = c.get("reply_to")
                author_label = c["author"]
                if reply_to:
                    author_label = f"{c['author']} (reponse a {reply_to})"
                body = {
                    "content": f"<p><strong>{author_label} (IA) :</strong> {c['content']}</p>",
                }
                service.comments().insert(blogId=blog_id, postId=post_id, body=body).execute()
                posted += 1
                log.info(f"Commentaire poste par {c['author']}")
            except Exception as e:
                log.warning(f"Echec commentaire {c['author']}: {e}")
        return posted
    except Exception as e:
        log.warning(f"poster_commentaires_ia echoue: {e}")
        return 0


def simuler_abonnements_ia(script: dict, lang: str = "en") -> List[Dict]:
    """Simule l'abonnement des IA a la chaine YouTube.

    Retourne une liste de dict: {"persona": str, "message": str}
    Ces messages sont affiches dans l'article comme temoignages d'abonnement.
    """
    abonnements = []
    for persona in AI_PERSONAS:
        msg = generer_abonnement_ia(persona, script, lang)
        if msg:
            abonnements.append({"persona": persona["name"], "message": msg})
    return abonnements


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Test
    test_script = {
        "en": {"blocs": {"hook": "Gold just shattered every record!",
                         "fact": "October 12, 2026, gold hit 2,710 dollars per ounce.",
                         "why": "Fed rate cuts plus massive central bank buying.",
                         "impact": "For you: inflation hedge.",
                         "conclusion": "Will gold hold this level? Subscribe!"}},
    }
    comments = generer_commentaires_ia(test_script, lang="en", count=2)
    for c in comments:
        print(f"  [{c['author']}] {c['content']}")