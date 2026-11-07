"""selection.py — Scoring enrichi + filtre date + mots-clés marketing"""
import re, logging, json, html
from datetime import datetime, timezone, timedelta
from pathlib import Path
import config
from db import db_exists, db_cle_exists
from themes import theme_du_jour, score_theme, detecter_theme

log = logging.getLogger("selection")

# ─── CONFIGURATION SCORING ─────────────────────────────────────
SCORE_MIN_SELECTION = 50
SCORE_BON_POTENTIEL = 100
SCORE_VIRAL_POTENTIEL = 150
SCORE_BREAKING_MAX = 200

# ─── MOTS-CLÉS TIER 1 — Marketing absolu (Section 9) ────────────
KEYWORDS_MASTER_30 = [
    # OR
    "gold price", "or record", "gold record", "gold all-time", "prix de l'or",
    "buy gold", "acheter or", "xauusd",
    # FED / BCE
    "fed rate", "fed decision", "rate cut", "rate hike", "fomc",
    "bce taux", "ecb rate", "baisse de taux", "hausse de taux",
    # INFLATION
    "inflation 2026", "cpi report", "inflation france", "inflation rate",
    "core inflation", "pce inflation",
    # PÉTROLE
    "oil price", "brent crude", "opec", "pétrole prix", "hormuz",
    # RÉCESSION / CRISE
    "recession 2026", "recession france", "economic collapse",
    "dollar collapse", "brics",
    # EMPLOI USA
    "jobs report", "nonfarm payroll", "nfp", "unemployment rate",
]

# ─── BONUS MARKETING (Section 6) ───────────────────────────────
BONUS_MARKETING = {
    "trending_2026": {
        "mots": [
            "gold record", "record or", "oil price spike", "hormuz",
            "fed rate hike", "baisse de taux", "rate cut", "rate hike",
            "recession 2026", "recession france", "inflation 2026",
            "dollar collapse", "dette us", "us debt", "brics",
            "nickel price", "copper surge", "buy gold", "acheter or",
            "economic collapse", "effondrement économique",
            "stagflation", "hyperinflation",
        ],
        "bonus": 20,
    },
    "titre_viral": {
        "patterns": [
            r'\d+[.,]?\d*\s*%', r'\$\d+[,.]?\d*', r'record', r'all.time',
            r'crash', r'collapse', r'surge', r'soar', r'spike',
            r'historic', r'historique', r'breaking', r'urgent',
        ],
        "bonus": 15,
        "max_patterns": 3,
    },
    "calendrier_macro": {
        "mots": [
            "nonfarm payroll", "jobs report", "nfp",
            "cpi", "consumer price index", "inflation rate",
            "gdp", "pib", "fomc", "ecb meeting", "bce réunion",
            "pce", "retail sales", "unemployment rate",
            "pmi", "trade balance", "fed minutes",
        ],
        "bonus": 25,
    },
    "geo_prioritaire": {
        "mots": [
            "us", "united states", "federal reserve", "white house",
            "wall street", "europe", "eurozone", "ecb", "france",
            "germany", "uk", "britain",
        ],
        "bonus": 8,
    },
}

# ─── CHAMPS SÉMANTIQUES (domaines) ─────────────────────────────
DOMAIN_KEYWORDS = {
    "monetary": ["fed", "federal reserve", "ecb", "bce", "banque centrale", "central bank",
                 "interest rate", "taux directeur", "taux d'interet", "politique monetaire",
                 "quantitative easing", "qe", "resserrement", "assouplissement"],
    "fiscal": ["budget", "deficit", "dette", "borrowing", "spending", "fiscal", "ifs",
               "public finances", "obligation", "gilt", "emprunt", "treasury"],
    "inflation": ["inflation", "cpi", "pce", "prix", "consommation", "ipc", "indice prix"],
    "labor": ["emploi", "unemployment", "payroll", "nfp", "chomage", "chômage", "jobs"],
    "growth": ["croissance", "gdp", "pib", "recession", "récession", "recession technique"],
    "banking": ["banque", "bank", "systeme financier", "stabilite financiere", "basel"],
    "commodities": ["gold", "or ", "oil", "petrole", "pétrole", "brent", "wti", "opec", "opep",
                    "cuivre", "nickel", "lithium", "matiere premiere", "commodity"],
    "fx": ["dollar", "euro", "forex", "change", "parite", "yen", "yuan", "livre", "sterling"],
    "equities": ["bourse", "stock", "cac", "dow", "nasdaq", "sp500", "earnings", "resultats", "benefice"],
    "rates": ["taux", "rate", "yield", "courbe", "spread", "breakeven", "gilt", "bund", "treasury"],
    "trade": ["tariff", "droits de douane", "douane", "trade war", "guerre commerciale"],
    "housing": ["immobilier", "house price", "mortgage", "credit immo", "logement"],
    "energy": ["energie", "energy", "carbone", "renouvelable", "electricite", "prix energie"],
    "inequality": ["inegalite", "inequality", "gini", "pouvoir achat", "pauvreté", "salaire minimum"],
}

RECORD_WORDS = [r"\brecord\b", r"all-time high", r"plus haut historique", r"plus bas historique",
                r"\bsommet\b", r"\bplancher\b", r"niveau record", r"seuil historique", r"jamais vu"]

# ─── MOTS ÉMOTIONNELS MULTILINGUES (Section 11.4) ───────────────
TOUS_MOTS_EMOTIONNELS = {
    "peur": {
        "mots": [
            "menace", "détruit", "s'effondre", "plonge", "dévore", "ronge", "érode",
            "threatens", "destroys", "collapses", "plunges", "wipes out", "erodes",
            "amenaza", "destruye", "se derrumba", "se desploma", "devora",
            "avant qu'il soit trop tard", "before it's too late", "antes de que sea tarde",
            "votre épargne", "your savings", "tus ahorros", "votre retraite", "your retirement",
            "alerte", "warning", "advertencia", "alerta", "signal d'alarme", "alarm signal",
        ],
        "bonus": 20,
        "max_bonus": 40,
    },
    "surprise": {
        "mots": [
            "jamais vu", "inédit", "sans précédent", "historique", "record absolu",
            "never seen", "unprecedented", "historic", "all-time", "record-breaking",
            "nunca visto", "sin precedentes", "histórico", "récord absoluto",
            "pour la première fois", "for the first time", "por primera vez",
            "pour la 1ère fois", "first time",
        ],
        "bonus": 18,
        "max_bonus": 36,
    },
    "colere": {
        "mots": [
            "ce qu'ils ne vous disent pas", "vérité cachée", "vérité que les médias taisent",
            "what they don't tell you", "hidden truth", "what the media won't say",
            "lo que no te dicen", "la verdad oculta", "lo que los medios callan",
            "pendant que vous", "while you", "mientras tú",
            "profit record", "record profits", "profits records", "ganancias récord",
            "pendant que votre", "while your", "mientras tu",
        ],
        "bonus": 15,
        "max_bonus": 30,
    },
    "fomo": {
        "mots": [
            "ne ratez pas", "à saisir", "fenêtre d'opportunité", "fenêtre",
            "don't miss", "act now", "window of opportunity", "window",
            "no te lo pierdas", "actúa ahora", "la ventana",
            "avant la prochaine", "before the next", "antes de la próxima",
            "smart money", "argent intelligent", "insiders",
        ],
        "bonus": 12,
        "max_bonus": 24,
    },
}

def score_emotionnel(article: dict) -> float:
    """Calcule le score émotionnel (0-130 pts) basé sur les mots déclencheurs."""
    text = (article.get("titre", "") + " " + article.get("resume", "")).lower()
    score_total = 0.0
    for emotion, config in TOUS_MOTS_EMOTIONNELS.items():
        score_emotion = 0.0
        for mot in config["mots"]:
            if mot.lower() in text:
                score_emotion += config["bonus"]
        score_emotion = min(score_emotion, config["max_bonus"])
        score_total += score_emotion
    return round(score_total, 1)

# ─── HELPERS ───────────────────────────────────────────────────
def _clean(txt: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", txt or "")
    return re.sub(r"\s+", " ", html.unescape(txt)).strip()

def _chiffres(txt: str) -> set:
    return {re.sub(r"\D", "", m) for m in re.findall(r"\d+(?:[ \u202f\u00a0.,]\d{3})*(?:[.,]\d+)?", txt)}

def extract_chiffre(titre: str, resume: str):
    RE_NOMBRE = r"\d+(?:[ \u202f\u00a0.,]\d{3})*(?:[.,]\d+)?"
    RE_CHIFFRE = re.compile(
        rf"((?:[$€£]\s?{RE_NOMBRE}\s?(?:bn|milliards?|millions?|billion|million|m|b)?)"
        rf"|(?:{RE_NOMBRE}\s?(?:%|\$|€|£|dollars?|euros?|milliards?|millions?|billion|million|bn|m|b|points?\s+de\s+base)))",
        re.IGNORECASE,
    )
    m = RE_CHIFFRE.search(titre) or RE_CHIFFRE.search(resume)
    return m.group(1).strip() if m else None

# ─── FILTRE DATE STRICT (Section 10.2) ─────────────────────────
def _get_date_pub(article: dict):
    """Récupère date_pub ou date (depuis veille.py) et normalise en datetime UTC."""
    date_pub = article.get("date_pub") or article.get("date")
    if not date_pub:
        return None
    if isinstance(date_pub, str):
        try:
            date_pub = datetime.fromisoformat(date_pub.replace("Z", "+00:00"))
        except Exception:
            return None
    if date_pub.tzinfo is None:
        date_pub = date_pub.replace(tzinfo=timezone.utc)
    return date_pub

def filtre_date_strict(article: dict, heures_max: int = 36) -> bool:
    date_pub = _get_date_pub(article)
    if not date_pub:
        return False
    age_h = (datetime.now(timezone.utc) - date_pub).total_seconds() / 3600
    return age_h <= heures_max

def score_fraicheur(article: dict) -> float:
    date_pub = _get_date_pub(article)
    if not date_pub:
        return 0
    age_h = (datetime.now(timezone.utc) - date_pub).total_seconds() / 3600
    if age_h <= 3:    return 50
    if age_h <= 6:    return 40
    if age_h <= 12:   return 30
    if age_h <= 24:   return 20
    if age_h <= 36:   return 10
    return 0

# ─── SCORING MOTS-CLÉS ─────────────────────────────────────────
def count_kw(text: str, kw_list: list) -> int:
    return sum(1 for kw in kw_list if kw.lower() in text.lower())

def score_keywords_tier1(article: dict) -> float:
    """Mots-clés maîtres Tier 1 — +25 pts chacun (max 75)"""
    text = (article.get("titre", "") + " " + article.get("resume", "")).lower()
    hits = sum(1 for kw in KEYWORDS_MASTER_30 if kw.lower() in text)
    return min(hits * 25, 75)

def score_keywords_tier2(article: dict) -> float:
    """Mots-clés domaines — +5 par mot, max 3 par domaine (plafond 15/domaine)"""
    text = (article.get("titre", "") + " " + article.get("resume", "")).lower()
    score = 0
    for domain, kws in DOMAIN_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in text)
        score += min(hits, 3) * 5
    return min(score, 60)

def has_record(text: str) -> bool:
    return any(re.search(pat, text, re.IGNORECASE) for pat in RECORD_WORDS)

# ─── BONUS MARKETING ───────────────────────────────────────────
def _contains_kw(text: str, kw: str) -> bool:
    """Mot-clé avec bornes de mots pour éviter les faux positifs (ex: 'us' dans 'business')."""
    return re.search(r"\b" + re.escape(kw.lower()) + r"\b", text) is not None

def score_marketing_bonus(article: dict) -> float:
    text = (article.get("titre", "") + " " + article.get("resume", "")).lower()
    titre = article.get("titre", "").lower()
    bonus = 0.0

    # Trending 2026 (1 seul bonus)
    for mot in BONUS_MARKETING["trending_2026"]["mots"]:
        if _contains_kw(text, mot):
            bonus += BONUS_MARKETING["trending_2026"]["bonus"]
            break

    # Patterns titre viral (max 3)
    patterns_trouves = 0
    for pat in BONUS_MARKETING["titre_viral"]["patterns"]:
        if re.search(pat, titre) and patterns_trouves < BONUS_MARKETING["titre_viral"]["max_patterns"]:
            bonus += BONUS_MARKETING["titre_viral"]["bonus"]
            patterns_trouves += 1

    # Événement calendrier
    for mot in BONUS_MARKETING["calendrier_macro"]["mots"]:
        if _contains_kw(text, mot):
            bonus += BONUS_MARKETING["calendrier_macro"]["bonus"]
            break

    # Géographie prioritaire
    for mot in BONUS_MARKETING["geo_prioritaire"]["mots"]:
        if _contains_kw(text, mot):
            bonus += BONUS_MARKETING["geo_prioritaire"]["bonus"]
            break

    return bonus

# ─── CONFIRMATION CROISÉE ──────────────────────────────────────
def _mots(titre: str) -> set:
    return {w for w in re.findall(r"[a-zA-ZÀ-ÿ]{5,}", titre.lower())}

def count_confirmations(art: dict, tous: list[dict]) -> int:
    sources = set()
    mots = _mots(art["titre"])
    cle = _chiffres(art["chiffre_cle"]) if art.get("chiffre_cle") else set()
    topic_kw = {kw for domain, kws in DOMAIN_KEYWORDS.items() for kw in kws if kw in f"{art['titre']} {art['resume']}".lower()}

    for b in tous:
        if b["source"] == art["source"]:
            continue
        b_text = f"{b['titre']} {b['resume']}".lower()
        # 1. Même chiffre
        if cle and cle <= _chiffres(b_text):
            sources.add(b["source"])
        # 2. Mots titre communs
        elif len(mots & _mots(b["titre"])) >= 3:
            sources.add(b["source"])
        # 3. Sujet macro commun (≥2 mots-clés domaine)
        else:
            b_topic = {kw for domain, kws in DOMAIN_KEYWORDS.items() for kw in kws if kw in b_text}
            if len(topic_kw & b_topic) >= 2:
                sources.add(b["source"])
    return len(sources)

# ─── SCORE TOTAL ───────────────────────────────────────────────
def score_total(article: dict, theme: str = None) -> float:
    # Filtre date dur
    if not filtre_date_strict(article, heures_max=36):
        return -1

    score = 0.0
    score += score_fraicheur(article)                    # 0-50
    score += score_keywords_tier1(article)               # 0-75
    score += score_keywords_tier2(article)               # 0-60

    # Chiffre clé
    if article.get("chiffre_cle"):
        score += 20

    # Tier source
    score += 15 if article.get("tier") == 1 else 8

    # Record
    texte = f"{article.get('titre', '')} {article.get('resume', '')}".lower()
    if has_record(texte):
        score += 25

    # Thème du jour (bonus doux)
    if theme:
        score += score_theme(article, theme)

    # Calendrier macro (inclus dans marketing)
    score += score_marketing_bonus(article)

    # Émotionnel
    score += score_emotionnel(article)

    return round(score, 1)

# ─── PIPELINE PRINCIPAL ────────────────────────────────────────
def run_selection(articles: list[dict], theme: str = None) -> dict | None:
    """Retourne le meilleur article ou None."""
    if not articles:
        return None
    theme = theme or theme_du_jour()

    # Enrichir
    for a in articles:
        a["chiffre_cle"] = extract_chiffre(a["titre"], a["resume"])
        a["score_theme"] = score_theme(a, theme)
        a["score_base"] = score_total(a, theme)
        a["confirmations"] = count_confirmations(a, articles)
        a["score_final"] = a["score_base"] + (15 if a["confirmations"] >= 2 else 0)

    # Trier
    articles.sort(key=lambda a: a["score_final"], reverse=True)

    for passe in ("theme", "libre"):
        for a in articles:
            if a["score_final"] < SCORE_MIN_SELECTION:
                break
            if passe == "theme" and a["score_theme"] == 0:
                continue
            if not a["chiffre_cle"]:
                continue
            cle = "|".join(sorted(_chiffres(a["chiffre_cle"])))
            if db_exists(a["titre"]) or db_cle_exists(cle):
                continue
            a["theme"] = theme if a["score_theme"] else detecter_theme(a)
            log.info("SÉLECTION: %s | score=%.1f | theme=%s | %s",
                     a["titre"][:60], a["score_final"], a["theme"], a["source"])
            return a

    log.warning("Aucun article ne passe les filtres (min=%d).", SCORE_MIN_SELECTION)
    return None

# ─── TEST ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import html
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Articles de test simulés (issus des flux RSS réels)
    now = datetime.now(timezone.utc)
    test_articles = [
        {
            "titre": "Healey faces £35bn Budget challenge to meet spending pledges, says think tank",
            "resume": "The Institute for Fiscal Studies says the government will need a top-up of billions of pounds if it wants to meet its spending plans.",
            "source": "bbc_business", "tier": 1, "lang": "en",
            "url": "https://bbc.co.uk/...", "date_pub": now - timedelta(hours=4),
        },
        {
            "titre": "L'or franchit 2 710 $ l'once — record historique",
            "resume": "Le prix de l'or a dépassé 2 710 $ pour la première fois, porté par la baisse des taux de la Fed et les achats massifs des banques centrales.",
            "source": "rfi_economie", "tier": 1, "lang": "fr",
            "url": "https://rfi.fr/...", "date_pub": now - timedelta(hours=2),
        },
        {
            "titre": "Avec la 2 CV électrique, Citroën ressuscite une légende",
            "resume": "La marque du groupe Stellantis présente une nouvelle version de son modèle historique au Mondial de l'automobile. Prix visé : 15 000 euros.",
            "source": "lemonde_economie", "tier": 1, "lang": "fr",
            "url": "https://lemonde.fr/...", "date_pub": now - timedelta(hours=6),
        },
        {
            "titre": "CPI report shows inflation at 2.1% in September",
            "resume": "US consumer price index rose 2.1% year-over-year, below expectations. Core CPI at 3.2%.",
            "source": "bbc_business", "tier": 1, "lang": "en",
            "url": "https://bbc.co.uk/...", "date_pub": now - timedelta(hours=1),
        },
        {
            "titre": "Fed minutes show officials split on next rate move",
            "resume": "Federal Reserve officials debated whether further rate cuts are needed as inflation remains sticky.",
            "source": "bbc_business", "tier": 1, "lang": "en",
            "url": "https://bbc.co.uk/...", "date_pub": now - timedelta(hours=3),
        },
    ]

    # Ajouter date_pub en ISO pour test
    for a in test_articles:
        a["date_pub"] = a["date_pub"].isoformat()

    print("=== TEST SELECTION ===")
    for a in test_articles:
        a["chiffre_cle"] = extract_chiffre(a["titre"], a["resume"])
        a["score_final"] = score_total(a)
        print(f"[{a['score_final']:6.1f}] {a['titre'][:70]} | chiffre={a['chiffre_cle']}")

    print("\n--- SÉLECTION FINALE ---")
    selection = run_selection(test_articles)
    if selection:
        print(json.dumps(selection, indent=2, ensure_ascii=False))
    else:
        print("Aucun article sélectionné.")