"""veille.py — RSS-only : récupère, score et sélectionne le fait économique du jour."""
import re, html, logging, requests, feedparser
from datetime import datetime, timezone, timedelta
from time import mktime
import config
from db import db_exists, db_cle_exists
from themes import theme_du_jour, score_theme, detecter_theme

log = logging.getLogger("veille")
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Mots-clés haute valeur — MACRO / FINANCE / BOURSE / GRANDES ENTREPRISES
# +5 chacun, plafonné à 15 points au total (max 3 mots-clés comptés).
# Utilisation de regex avec bornes de mots pour éviter faux positifs (ex: "or " dans "citroën")
KEYWORDS_PATTERNS = [
    # Banques centrales & politique monétaire
    r"\bfed\b", r"\bfederal reserve\b", r"\becb\b", r"\bbce\b", r"\bbanque centrale\b", r"\bcentral bank\b",
    r"\binterest rate\b", r"\btaux directeur\b", r"\btaux d'interet\b", r"\bpolitique monetaire\b",
    r"\bquantitative easing\b", r"\bqe\b", r"\bresserrement\b", r"\bassouplissement\b",
    # Inflation & prix
    r"\binflation\b", r"\bcpi\b", r"\bpce\b", r"\bdeflation\b", r"\bdisinflation\b", r"\bprix a la consommation\b",
    # Croissance & emploi
    r"\brecession\b", r"\brécession\b", r"\bcroissance\b", r"\bgdp\b", r"\bpib\b", r"\brecession technique\b",
    r"\bunemployment\b", r"\bchomage\b", r"\bchômage\b", r"\bemploi\b", r"\bpayroll\b", r"\bnfp\b",
    # Marchés / Bourse / Grandes entreprises
    r"\bbourse\b", r"\bstock market\b", r"\bwall street\b", r"\bcac 40\b", r"\bdow jones\b", r"\bnasdaq\b", r"\bsp 500\b",
    r"\bresultats\b", r"\bearnings\b", r"\bbenefice\b", r"\bprofit\b", r"\bchiffre d'affaires\b", r"\brevenue\b",
    r"\bgeants\b", r"\bmega-cap\b", r"\bapple\b", r"\bmicrosoft\b", r"\bnvidia\b", r"\bamazon\b", r"\bmeta\b", r"\bgoogle\b",
    # Matières premières stratégiques
    r"\bgold\b", r"\bor\b", r"\boil\b", r"\bpetrole\b", r"\bpétrole\b", r"\bbrent\b", r"\bwti\b", r"\bopec\b", r"\bopep\b",
    r"\bcuivre\b", r"\bnickel\b", r"\blithium\b", r"\bmatiere premiere\b", r"\bcommodity\b",
    # Devises & commerce
    r"\bdollar\b", r"\beuro\b", r"\byen\b", r"\byuan\b", r"\bforex\b", r"\bchange\b", r"\bparite\b",
    r"\btariff\b", r"\bdroits de douane\b", r"\bdouane\b", r"\btrade war\b", r"\bguerre commerciale\b",
    # Banques / système financier
    r"\bbanque\b", r"\bbank\b", r"\bsysteme financier\b", r"\bstabilite financiere\b", r"\bbasel\b",
    # Dette / Budget / Etat
    r"\bdette publique\b", r"\bdeficit\b", r"\bbudget\b", r"\bemission obligataire\b", r"\btreasury\b",
    r"\bifs\b", r"\binstitute for fiscal studies\b", r"\bspending\b", r"\bpledges\b", r"\bborrowing\b",
    r"\bpublic finances\b", r"\bfiscal\b", r"\bauditor\b", r"\bdebt\b",
]
RECORD_WORDS = [
    r"\brecord\b", r"all-time high", r"plus haut historique", r"plus bas historique",
    r"\bsommet\b", r"\bplancher\b", r"niveau record", r"seuil historique", r"jamais vu",
]

def count_kw(text: str) -> int:
    """Compte mots-clés macro présents (avec bornes de mots)."""
    return sum(1 for pat in KEYWORDS_PATTERNS if re.search(pat, text, re.IGNORECASE))

def has_record(text: str) -> bool:
    return any(re.search(pat, text, re.IGNORECASE) for pat in RECORD_WORDS)



# Chiffre clé : "$2,710", "2 710 $", "3.5%", "4,2 milliards", "£35bn", "35 milliards"...
RE_NOMBRE = r"\d+(?:[ \u202f\u00a0.,]\d{3})*(?:[.,]\d+)?"
RE_CHIFFRE = re.compile(
    rf"((?:[$€£]\s?{RE_NOMBRE}\s?(?:bn|milliards?|millions?|billion|million|m|b)?)"
    rf"|(?:{RE_NOMBRE}\s?(?:%|\$|€|£|dollars?|euros?|milliards?|millions?|billion|million|bn|m|b|points?\s+de\s+base)))",
    re.IGNORECASE,
)
RE_NOMBRE_SEUL = re.compile(RE_NOMBRE)

def _chiffres(txt: str) -> set:
    """Nombres d'un texte normalisés (2 710 / 2,710 / 2.710 -> '2710')."""
    return {re.sub(r"\D", "", m) for m in RE_NOMBRE_SEUL.findall(txt)}

def _clean(txt: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", txt or "")
    return re.sub(r"\s+", " ", html.unescape(txt)).strip()

def extract_chiffre(titre: str, resume: str):
    m = RE_CHIFFRE.search(titre) or RE_CHIFFRE.search(resume)
    return m.group(1).strip() if m else None

def fetch_all_rss(hours_back: int = config.HOURS_BACK) -> list[dict]:
    limite = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    articles = []
    for nom, f in config.RSS_FEEDS.items():
        try:
            r = requests.get(f["url"], headers=HEADERS, timeout=15)
            feed = feedparser.parse(r.content)
        except Exception as e:
            log.warning("Flux %s en erreur : %s", nom, e)
            continue
        n = 0
        for e in feed.entries:
            if not e.get("published_parsed"):
                continue
            date = datetime.fromtimestamp(mktime(e.published_parsed), timezone.utc)
            if date < limite:
                continue
            titre = _clean(e.get("title"))
            resume = _clean(e.get("summary"))
            if not titre:
                continue
            articles.append({
                "titre": titre, "resume": resume, "url": e.get("link"),
                "source": nom, "tier": f["tier"], "lang": f["lang"], "date": date,
            })
            n += 1
        log.info("Flux %s : %d articles récents", nom, n)
    return articles

def score_article(a: dict) -> int:
    texte = f"{a['titre']} {a['resume']}".lower()
    score = 0
    # Mots-clés positifs (macro/finance/bourse) — avec bornes de mots
    nb_kw = count_kw(texte)
    score += min(nb_kw, 3) * 5                        # plafond : 15 pts
    
    # Chiffre clé vérifiable : bonus SEULEMENT si au moins 1 mot-clé macro présent
    if a.get("chiffre_cle") and nb_kw >= 1:
        score += 20
    elif a.get("chiffre_cle") and nb_kw == 0:
        score += 5   # petit bonus si chiffre mais pas de mot-clé macro
    
    # Tier de la source
    score += 15 if a["tier"] == 1 else 8
    # Record / seuil historique
    if has_record(texte):
        score += 25
    return score

def _mots(a: dict) -> set:
    return {w for w in re.findall(r"[a-zA-ZÀ-ÿ]{5,}", a["titre"].lower())}

def _topic_keywords(text: str) -> set:
    """Mots-clés macro qui définissent le SUJET (pour confirmation croisée)."""
    return {pat for pat in KEYWORDS_PATTERNS if re.search(pat, text, re.IGNORECASE)}

def count_confirmations(art: dict, tous: list[dict]) -> int:
    """Nb d'AUTRES sources qui parlent du même sujet :
    - même chiffre clé, OU
    - >=3 mots du titre en commun, OU
    - >=2 mots-clés macro de SUJET en commun (ex: budget + spending = même sujet)."""
    sources = set()
    mots = _mots(art)
    cle = _chiffres(art["chiffre_cle"]) if art.get("chiffre_cle") else set()
    topic_kw = _topic_keywords(f"{art['titre']} {art['resume']}")
    for b in tous:
        if b["source"] == art["source"]:
            continue
        # 1. Même chiffre
        if cle and cle <= _chiffres(f"{b['titre']} {b['resume']}"):
            sources.add(b["source"])
        # 2. Mots titre communs
        elif len(mots & _mots(b)) >= 3:
            sources.add(b["source"])
        # 3. Sujet macro commun (>=2 kw macro)
        else:
            b_topic = _topic_keywords(f"{b['titre']} {b['resume']}")
            if len(topic_kw & b_topic) >= 2:
                sources.add(b["source"])
    return len(sources)

def run_veille(hours_back: int = config.HOURS_BACK, theme: str = None):
    """Retourne le dict du fait du jour (prêt pour script.py), ou None."""
    theme = theme or theme_du_jour()
    articles = fetch_all_rss(hours_back)
    if not articles:
        log.error("Aucun article récupéré : tous les flux sont vides ou en erreur.")
        return None
    for a in articles:
        a["chiffre_cle"] = extract_chiffre(a["titre"], a["resume"])
        a["score_theme"] = score_theme(a, theme)
        a["score"] = score_article(a) + a["score_theme"]
    articles.sort(key=lambda a: a["score"], reverse=True)

    for passe in ("theme", "libre"):
        for a in articles:
            if a["score"] < config.SCORE_MIN:
                break
            if passe == "theme" and a["score_theme"] == 0:
                continue
            if not a["chiffre_cle"]:
                continue
            cle = "|".join(sorted(_chiffres(a["chiffre_cle"])))
            if db_exists(a["titre"]) or db_cle_exists(cle):
                continue
            a["confirmations"] = count_confirmations(a, articles)
            if a["confirmations"] < config.MIN_CONFIRMATIONS:
                continue
            return {
                "date": a["date"].strftime("%d/%m/%Y"),
                "titre": a["titre"], "chiffre_cle": a["chiffre_cle"], "resume": a["resume"],
                "source": a["source"], "url": a["url"], "lang_source": a["lang"],
                "score": a["score"], "confirmations": a["confirmations"], "cle": cle,
                "theme": theme if a["score_theme"] else detecter_theme(a),
            }
    log.warning("Aucun article ne passe les filtres (score >= %d + chiffre clé).", config.SCORE_MIN)
    return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fait = run_veille()
    if fait:
        import json
        print(json.dumps(fait, indent=2, ensure_ascii=False))
    else:
        print("Aucun fait retenu aujourd'hui.")