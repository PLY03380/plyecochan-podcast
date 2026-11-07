"""package.py — Validation et amélioration des titres/thumbnails YouTube (règles yt-package)."""
import re

VAGUE = {"amazing", "incredible", "insane", "crazy", "huge", "massive", "ultimate", "best",
         "powerful", "secret", "revolutionary", "mindblowing", "epic", "perfect", "complete",
         "everything"}
STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are", "with",
        "your", "you", "my", "i", "this", "that", "it", "how", "what", "why"}

DESKTOP, MOBILE, HARD = 60, 40, 100


def _words(t):
    return re.findall(r"[a-z0-9']+", t.lower())


def check_title(title: str, thumb: str = None) -> dict:
    """Valide un titre (+ thumbnail optionnel) selon les règles yt-package."""
    t = title.strip()
    n = len(t)
    issues, good = [], []

    if n > HARD:
        issues.append(("length", f"{n} chars - hard limit {HARD}"))
    elif n > DESKTOP:
        issues.append(("length", f"{n} chars - desktop cut near {DESKTOP}"))
    else:
        good.append(f"{n} chars, inside {DESKTOP} desktop cut")

    if n > MOBILE:
        head = t[:MOBILE].rsplit(" ", 1)[0]
        issues.append(("mobile", f'mobile feed shows "{head}..." - check subject survives'))

    caps = [w for w in t.split() if len(w) > 2 and w.isupper()]
    if len(caps) > 2:
        issues.append(("shouting", f"{len(caps)} all-caps words - max 2"))
    elif caps:
        good.append(f"{len(caps)} all-caps word(s) for emphasis")

    v = [w for w in _words(t) if w in VAGUE]
    if v:
        issues.append(("vague", f"{', '.join(sorted(set(v)))} - swap for number/name/date"))
    nums = re.findall(r"\d[\d,.]*%?", t)
    if nums:
        good.append(f"concrete figure ({', '.join(nums[:3])})")
    else:
        issues.append(("no-number", "no number/date/name - most reliable fix"))

    if t.endswith("?"):
        good.append("open question in title")

    front = [w for w in _words(t)[:3] if w not in STOP]
    if not front:
        issues.append(("front-load", "first 3 words are filler - move subject forward"))

    if thumb:
        tw = set(_words(t)) - STOP
        hw = set(_words(thumb)) - STOP
        shared = tw & hw
        if shared:
            issues.append(("duplicate", f"thumbnail repeats title on {', '.join(sorted(shared))}"))
        else:
            good.append("thumbnail and title carry different words")
        if len(_words(thumb)) > 4:
            issues.append(("thumb-length", f"{len(_words(thumb))} words on thumbnail - max 3-4"))

    score = max(0, min(100, 100 - 14 * len(issues) + 4 * len(good)))
    return {"title": t, "chars": n, "score": score, "issues": issues, "good": good}


def suggest_thumb(title: str) -> str:
    """Suggere un thumbnail text de 3 mots max, different du titre."""
    nums = re.findall(r"\d[\d,.]*%?", title)
    if nums:
        return nums[0]
    # Prendre les mots non-STOP du titre, max 3
    words = [w for w in _words(title) if w not in STOP and w not in VAGUE]
    return " ".join(words[:3]).upper()


def improve_title(title: str) -> dict:
    """Valide un titre et suggere des ameliorations."""
    result = check_title(title)
    result["suggested_thumb"] = suggest_thumb(title)
    return result


import subprocess, json as _json, os as _os

HOOKSCORE_PATH = r"D:\dotfiles\agents\skills\yt-script\hookscore.py"


def score_hook(hook_text: str) -> dict:
    """Score un hook avec hookscore.py (21 formules)."""
    try:
        result = subprocess.run(
            ["python", HOOKSCORE_PATH, "--hook", hook_text, "--json"],
            capture_output=True, text=True, timeout=10,
        )
        data = _json.loads(result.stdout)
        if isinstance(data, list) and data:
            data = data[0]
        return {
            "hook": hook_text,
            "score": data.get("verdict", 0),
            "verdict": data.get("band", "UNKNOWN"),
            "formula": data.get("formula", "Unclassified"),
            "properties": data.get("properties", {}),
        }
    except Exception as e:
        return {"hook": hook_text, "score": 0, "verdict": "ERROR", "formula": "error", "raw": str(e)}


def score_hooks_script(script: dict) -> dict:
    """Score les accroches de toutes les langues."""
    scores = {}
    for lang in ("fr", "en", "es"):
        blocs = script.get(lang, {}).get("blocs", {})
        ordre = {"fr": "accroche", "en": "hook", "es": "gancho"}[lang]
        hook = blocs.get(ordre, "")
        if hook:
            scores[lang] = score_hook(hook)
    script["hook_scores"] = scores
    return script


def ameliorer_titres(script: dict) -> dict:
    """Valide et ameliore les titres de toutes les langues dans le script.

    Ajoute un champ 'package' au script avec les scores et thumbnails suggeres.
    """
    package = {}
    for lang in ("fr", "en", "es"):
        titre = script.get(lang, {}).get("titre", "")
        if not titre:
            continue
        result = improve_title(titre)
        package[lang] = {
            "titre_original": titre,
            "score": result["score"],
            "issues": result["issues"],
            "good": result["good"],
            "thumbnail_text": result["suggested_thumb"],
        }
    script["package"] = package
    return script


def generer_seo(script: dict) -> dict:
    """Genere description + tags pour YouTube a partir du script (regles yt-seo).

    Ajoute un champ 'seo' au script.
    """
    seo = {}
    for lang in ("fr", "en", "es"):
        blocs = script.get(lang, {}).get("blocs", {})
        if not blocs:
            continue

        # Ordre des blocs par langue
        ordre = {"fr": ["accroche", "fait", "pourquoi", "impact", "conclusion"],
                 "en": ["hook", "fact", "why", "impact", "conclusion"],
                 "es": ["gancho", "hecho", "por_que", "impacto", "conclusion"]}[lang]

        # Description : 2 premieres lignes = snippet (accroche + fait), puis le reste
        accroche = blocs.get(ordre[0], "")
        fait = blocs.get(ordre[1], "")
        pourquoi = blocs.get(ordre[2], "")
        impact = blocs.get(ordre[3], "")
        conclusion = blocs.get(ordre[4], "")

        # Premiere ligne : ce que la video donne (en mots de recherche)
        # Optimise pour le snippet YouTube (150 chars max visibles)
        titre_clean = script.get(lang, {}).get("titre", "").replace("#shorts", "").strip()
        premiere_ligne = f"{titre_clean} | {accroche[:80]}" if accroche else titre_clean
        deuxieme_ligne = fait[:120] if fait else ""

        description = f"{premiere_ligne}\n{deuxieme_ligne}\n\n"
        description += f"{pourquoi}\n\n{impact}\n\n{conclusion}\n\n"
        # Hashtags (3 max, pertinents pour le SEO)
        hashtags = {
            "fr": ["#economie", "#actualite", "#shorts"],
            "en": ["#economy", "#news", "#shorts"],
            "es": ["#economia", "#noticias", "#shorts"],
        }
        description += " ".join(hashtags.get(lang, ["#shorts"]))

        # Tags : extraire les mots-cles significatifs (max 15)
        all_text = " ".join(blocs.values()).lower()
        titre = script.get(lang, {}).get("titre", "").lower()
        sujet = script.get("sujet", "").lower()

        # Mots-cles economiques courants + termes specifiques au sujet
        keywords = set()
        eco_terms = {
            "fr": ["economie", "inflation", "or", "gold", "fed", "bce", "taux", "emploi", "pib",
                   "recession", "petrole", "dollar", "euro", "bourse", "marche", "finance",
                   "actualite", "news", "shorts", "analyse", "decryptage", "comprendre"],
            "en": ["economy", "inflation", "gold", "fed", "ecb", "rates", "jobs", "gdp",
                   "recession", "oil", "dollar", "euro", "stock", "market", "finance",
                   "news", "shorts", "economic", "analysis", "explained", "understand"],
            "es": ["economia", "inflacion", "oro", "fed", "bce", "tasas", "empleo", "pib",
                   "recesion", "petroleo", "dolar", "euro", "bolsa", "mercado", "finanzas",
                   "noticias", "shorts", "analisis", "explicado", "entender"],
        }
        for term in eco_terms.get(lang, []):
            if term in all_text or term in titre or term in sujet:
                keywords.add(term)

        # Extraire les entites nommees et termes specifiques du texte
        import re as _re
        # Mots de plus de 4 lettres qui ne sont pas des stop words
        specific_words = [w for w in _words(all_text + " " + titre + " " + sujet)
                         if w not in STOP and len(w) > 4 and w.isalpha()]
        # Compter la frequence
        from collections import Counter
        word_counts = Counter(specific_words)
        for word, count in word_counts.most_common(8):
            if count >= 2:
                keywords.add(word)

        # Ajouter le titre en mots (non-stop)
        titre_words = [w for w in _words(titre) if w not in STOP and len(w) > 3]
        for w in titre_words[:5]:
            keywords.add(w)

        # Ajouter des tags longue traine (2-3 mots) bases sur le sujet
        sujet_words = [w for w in _words(sujet) if w not in STOP and len(w) > 3]
        if len(sujet_words) >= 2:
            keywords.add(" ".join(sujet_words[:2]))

        tags = sorted(keywords)[:15]

        seo[lang] = {
            "description": description.strip(),
            "tags": tags,
            "queries": [accroche[:60], fait[:60], f"{lang} economic news"],
        }
    script["seo"] = seo
    return script


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        title = sys.argv[1]
        thumb = sys.argv[2] if len(sys.argv) > 2 else None
        r = check_title(title, thumb)
        print(f"Title: {r['title']}")
        print(f"Chars: {r['chars']}  Score: {r['score']}/100")
        for k, m in r["issues"]:
            print(f"  X  {k}: {m}")
        for m in r["good"]:
            print(f"  OK  {m}")
        print(f"  Suggested thumb: {suggest_thumb(title)}")