"""themes.py — rotation, mots-clés et angle éditorial par thème."""
import re
from datetime import datetime

THEME_PAR_JOUR = {
    0: "ia_emploi",
    1: "immobilier",
    2: "inflation",
    3: "emploi",
    4: "ia_emploi",
    5: "immobilier",
    6: "bourse",
}

THEMES = {
    "ia_emploi": {
        "label": "IA + Emploi",
        "emotion": "peur",
        "angle": "Impact de l'IA sur les métiers et l'économie, jamais un tutoriel d'outil. Finir sur une action concrète.",
        "keywords": [
            r"\bai\b", r"\bia\b", r"intelligence artificielle", r"artificial intelligence",
            r"inteligencia artificial", r"\blayoffs?\b", r"licenciements?", r"despidos",
            r"automati[sz]ation", r"automatisation", r"\bchatgpt\b", r"\bopenai\b",
        ],
    },
    "immobilier": {
        "label": "Immobilier",
        "emotion": "colère",
        "angle": "Accessibilité du logement : prix, loyers, crédit. Expliquer pourquoi, puis ce que ça change pour acheter ou louer.",
        "keywords": [
            r"immobilier", r"real estate", r"\bhousing\b", r"mortgage", r"hypoth[eè]que",
            r"\bloyers?\b", r"\brent\b", r"logement", r"vivienda", r"hipoteca", r"house prices?",
        ],
    },
    "inflation": {
        "label": "Inflation / pouvoir d'achat",
        "emotion": "colère",
        "angle": "Pourquoi tout coûte plus cher et comment protéger son budget. Une seule phrase de colère, ton pédagogique.",
        "keywords": [
            r"inflation", r"\bcpi\b", r"\bpce\b", r"pouvoir d'achat", r"cost of living",
            r"co[uû]t de la vie", r"inflaci[oó]n", r"poder adquisitivo",
        ],
    },
    "emploi": {
        "label": "Emploi",
        "emotion": "peur",
        "angle": "Marché du travail : chômage, embauches, salaires. Finir sur un conseil.",
        "keywords": [
            r"unemployment", r"ch[oô]mage", r"\bpayroll\b", r"\bnfp\b", r"jobs report",
            r"\bhiring\b", r"embauches?", r"salaires?", r"\bwages?\b", r"desempleo",
        ],
    },
    "bourse": {
        "label": "Investissement / Bourse",
        "emotion": "fomo",
        "angle": "Marchés et investissement pour débutants : ce qui bouge, quoi retenir, sans conseil personnalisé.",
        "keywords": [
            r"bourse", r"stock market", r"wall street", r"nasdaq", r"s&p 500", r"cac 40",
            r"dow jones", r"earnings", r"\betf\b", r"\bbolsa\b",
        ],
    },
}


def theme_du_jour() -> str:
    return THEME_PAR_JOUR[datetime.now().weekday()]


def score_theme(article: dict, theme: str) -> int:
    if theme not in THEMES:
        return 0
    texte = f"{article.get('titre', '')} {article.get('resume', '')}"
    n = sum(1 for p in THEMES[theme]["keywords"] if re.search(p, texte, re.IGNORECASE))
    return 0 if n == 0 else (40 if n == 1 else 70)


def detecter_theme(article: dict) -> str:
    """Thème réel d'un article (pour choisir le bon fond vidéo si le thème du jour n'a rien donné)."""
    meilleur = max(THEMES, key=lambda t: score_theme(article, t))
    return meilleur if score_theme(article, meilleur) else "generique"
