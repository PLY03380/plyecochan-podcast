#!/usr/bin/env python3
"""
veille.py — Module A : Veille économique quotidienne via RSS uniquement
Aucune clé API requise. Sources : Reuters, AP, BBC, RFI, Le Monde, Les Echos, Bloomberg, CNBC.
Usage: python veille.py
"""

import feedparser
import re
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional
from pathlib import Path
import json

# ─── Configuration ──────────────────────────────────────────────
RSS_FEEDS = {
    "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
    "reuters_markets": "https://feeds.reuters.com/reuters/marketsNews",
    "ap_economics": "https://feeds.apnews.com/rss/apf-economics",
    "ap_business": "https://feeds.apnews.com/rss/apf-business",
    "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "bbc_economy": "https://feeds.bbci.co.uk/news/business/economy/rss.xml",
    "rfi_economie": "https://www.rfi.fr/fr/economie/rss",
    "lemonde_economie": "https://www.lemonde.fr/economie/rss_full.xml",
    "lesechos": "https://www.lesechos.fr/rss.xml",
    "bloomberg_markets": "https://feeds.bloomberg.com/markets/news.rss",
    "cnbc_economy": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
}

KEYWORDS_HIGH_VALUE = [
    # Banques centrales
    "fed", "federal reserve", "bce", "ecb", "banque centrale", "central bank",
    "taux", "rate", "interest rate", "policy rate", "discount rate",
    # Indicateurs macro
    "inflation", "cpi", "pce", "pib", "gdp", "croissance", "recession",
    "emploi", "unemployment", "jobs", "payroll", "chomage",
    # Marchés
    "record", "all-time high", "sommet", "chute", "plunge", "crash", "surge",
    "or", "gold", "petrole", "oil", "brent", "wti", "dollar", "euro", "yen",
    "bourse", "stock", "indice", "index", "cac", "dow", "nasdaq", "sp500",
    # Décisions
    "decision", "annonce", "statement", "communique", "minutes", "projection",
    # Matières premières / Afrique
    "nickel", "cobalt", "lithium", "vanille", "cafe", "cacao", "cotton",
    "madagascar", "afrique", "africa", "ariary",
]

TIER1_SOURCES = {"reuters_business", "reuters_markets", "ap_economics", "ap_business", "bbc_business", "bbc_economy"}

DB_PATH = Path(__file__).parent.parent / "data" / "eco_news.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─── Modèles ────────────────────────────────────────────────────
@dataclass
class RSSFact:
    titre: str
    date: str
    source: str
    url: str
    resume: str
    chiffre_cle: str = ""
    pourquoi: str = ""
    impact: str = ""
    score: float = 0.0

    def to_dict(self):
        return asdict(self)

# ─── Base de données ────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            resume TEXT,
            chiffre_cle TEXT,
            pourquoi TEXT,
            impact TEXT,
            score REAL,
            selected_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_url ON facts(url)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_date ON facts(date)")
    conn.commit()
    return conn

def fact_exists(conn, titre: str, date: str) -> bool:
    cur = conn.execute("SELECT 1 FROM facts WHERE titre = ? AND date = ?", (titre, date))
    return cur.fetchone() is not None

def save_fact(conn, fact: RSSFact):
    conn.execute("""
        INSERT OR IGNORE INTO facts (titre, date, source, url, resume, chiffre_cle, pourquoi, impact, score, selected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fact.titre, fact.date, fact.source, fact.url, fact.resume,
          fact.chiffre_cle, fact.pourquoi, fact.impact, fact.score,
          datetime.now().isoformat() if fact.score > 0 else None))
    conn.commit()

# ─── Nettoyage texte ────────────────────────────────────────────
def clean_title(title: str) -> str:
    title = re.sub(r'\s+', ' ', title).strip()
    title = re.sub(r'^(Video|Audio|Photo|Gallery|Live|Update|Breaking)\s*[:|\-]\s*', '', title, flags=re.I)
    return title[:180]

def clean_summary(summary: str) -> str:
    summary = re.sub(r'<[^>]+>', '', summary)  # strip HTML
    summary = re.sub(r'\s+', ' ', summary).strip()
    return summary[:500]

# ─── Extraction chiffre clé ─────────────────────────────────────
CHIFFRE_PATTERNS = [
    r'\$?\d+[.,]?\d*\s*(?:milliard|million|mrd|bn|m)\s*(?:€|\$|USD|EUR)',
    r'\d+[.,]?\d*\s*%',
    r'\d+[.,]?\d*\s*(?:pb|bp|points? de base)',
    r'\$?\d+[.,]?\d*\s*(?:tonne|baril|once|oz)',
    r'(?:à|à|reaches?|hits?|at|above|over|below|under)\s+\$?\d+[.,]?\d*',
    r'\d+[.,]?\d*\s*(?:euros?|dollars?)\b',
]

def extract_chiffre(text: str) -> str:
    for pat in CHIFFRE_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(0).strip()
    return ""

# ─── Enrichissement basique (sans LLM) ──────────────────────────
def extract_sentence_with(text: str, triggers: List[str]) -> str:
    """Retourne la première phrase contenant un déclencheur."""
    sentences = re.split(r'[.!?]+', text)
    for sent in sentences:
        sent_lower = sent.lower()
        if any(t in sent_lower for t in triggers):
            return sent.strip()[:250]
    return ""

def enrich_fact(fact: RSSFact):
    """Tente d'extraire pourquoi/impact depuis le résumé RSS."""
    text = fact.titre + " " + fact.resume
    
    # Chiffre
    if not fact.chiffre_cle:
        fact.chiffre_cle = extract_chiffre(text)
    
    # Pourquoi (causes)
    pourquoi_triggers = ["because", "due to", "after", "following", "après", "suite à", "car ", "puisque", "since", "as ", "amid", "amidst"]
    fact.pourquoi = extract_sentence_with(text, pourquoi_triggers)
    
    # Impact
    impact_triggers = ["impact", "consequence", "effect", "affect", "pour les", "for consumers", "for households", "ménage", "consommateur", "épargnant", "prix", "coût", "pouvoir d'achat"]
    fact.impact = extract_sentence_with(text, impact_triggers)

# ─── Scoring ────────────────────────────────────────────────────
def score_fact(fact: RSSFact) -> float:
    score = 0.0
    text = (fact.titre + " " + fact.resume).lower()
    
    # Mots-clés haute valeur
    for kw in KEYWORDS_HIGH_VALUE:
        if kw in text:
            score += 5
    
    # Chiffre présent
    if fact.chiffre_cle:
        score += 15
    
    # Source tier-1
    if fact.source in TIER1_SOURCES:
        score += 10
    
    # Fraîcheur (bonus si aujourd'hui)
    try:
        pub_date = datetime.fromisoformat(fact.date)
        if pub_date.date() == datetime.now().date():
            score += 10
        elif pub_date.date() == (datetime.now() - timedelta(days=1)).date():
            score += 5
    except:
        pass
    
    # Titre long = plus d'info
    if len(fact.titre) > 60:
        score += 3
    
    fact.score = round(score, 1)
    return fact.score

# ─── Pipeline principal ─────────────────────────────────────────
def fetch_all_rss(hours_back: int = 36) -> List[RSSFact]:
    cutoff = datetime.now() - timedelta(hours=hours_back)
    facts = []
    
    print(f"🔍 Fetching {len(RSS_FEEDS)} RSS feeds (last {hours_back}h)...")
    
    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                pub_date = None
                for field in ["published_parsed", "updated_parsed"]:
                    if entry.get(field):
                        pub_date = datetime(*entry[field][:6])
                        break
                
                if pub_date and pub_date < cutoff:
                    continue
                
                title = clean_title(entry.get("title", ""))
                summary = clean_summary(entry.get("summary", entry.get("description", "")))
                link = entry.get("link", "")
                
                if not title or len(title) < 15:
                    continue
                
                chiffre = extract_chiffre(title + " " + summary)
                
                fact = RSSFact(
                    titre=title,
                    date=pub_date.strftime("%Y-%m-%d") if pub_date else datetime.now().strftime("%Y-%m-%d"),
                    source=name,
                    url=link,
                    resume=summary,
                    chiffre_cle=chiffre
                )
                enrich_fact(fact)
                facts.append(fact)
                count += 1
                if count >= 15:  # max 15 par feed
                    break
            print(f"   ✅ {name}: {count} articles")
        except Exception as e:
            print(f"   ❌ {name}: {e}")
    
    return facts

def select_best_fact(facts: List[RSSFact], conn, min_score: float = 30) -> Optional[RSSFact]:
    scored = [f for f in facts if score_fact(f) >= min_score]
    scored.sort(key=lambda f: f.score, reverse=True)
    
    print(f"\n📊 Top {min(len(scored), 10)} faits (score ≥ {min_score}):")
    for i, f in enumerate(scored[:10], 1):
        exists = "⚠️ DÉJÀ TRAITÉ" if fact_exists(conn, f.titre, f.date) else ""
        print(f"  {i:2d}. [{f.score:5.1f}] {f.titre[:70]}... ({f.source}) {exists}")
    
    for f in scored:
        if not fact_exists(conn, f.titre, f.date):
            return f
    return None

# ─── Main ───────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🕵️  MODULE A — VEILLE ÉCONOMIQUE QUOTIDIENNE (RSS ONLY)")
    print("=" * 60)
    
    conn = init_db()
    
    # 1. Récupération
    facts = fetch_all_rss(hours_back=36)
    print(f"\n📰 Total articles récupérés: {len(facts)}")
    
    if not facts:
        print("⚠️ Aucun article trouvé")
        return
    
    # 2. Sélection
    best = select_best_fact(facts, conn, min_score=30)
    
    if best:
        save_fact(conn, best)
        print(f"\n✅ FAIT SÉLECTIONNÉ POUR LA VIDÉO DU JOUR:")
        print(f"   Titre: {best.titre}")
        print(f"   Date: {best.date}")
        print(f"   Source: {best.source}")
        print(f"   URL: {best.url}")
        print(f"   Chiffre clé: {best.chiffre_cle or '—'}")
        print(f"   Pourquoi: {best.pourquoi or '—'}")
        print(f"   Impact: {best.impact or '—'}")
        print(f"   Score: {best.score}")
        
        # Export JSON pour le module suivant
        output = {
            "selected": True,
            "fact": best.to_dict(),
            "timestamp": datetime.now().isoformat(),
            "alternatives": [f.to_dict() for f in facts if score_fact(f) >= 30 and f.titre != best.titre][:5]
        }
        out_path = DB_PATH.parent / "fact_du_jour.json"
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Exporté vers: {out_path}")
    else:
        print("\n⚠️ Aucun fait nouveau au-dessus du seuil")
        out_path = DB_PATH.parent / "fact_du_jour.json"
        out_path.write_text(json.dumps({"selected": False, "timestamp": datetime.now().isoformat()}, indent=2))
    
    conn.close()

if __name__ == "__main__":
    main()