import sqlite3, hashlib, os
from datetime import datetime, timezone, timedelta
import config

def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS articles (
        hash TEXT PRIMARY KEY,
        titre TEXT, source TEXT, url TEXT,
        score INTEGER, statut TEXT, cree_le TEXT, cle TEXT, theme TEXT)""")
    # Migration : ajouter la colonne theme si absente
    cols = [r[1] for r in c.execute("PRAGMA table_info(articles)")]
    if "theme" not in cols:
        c.execute("ALTER TABLE articles ADD COLUMN theme TEXT")
    return c

def _hash(titre: str) -> str:
    return hashlib.sha1(titre.strip().lower().encode("utf-8")).hexdigest()

def db_exists(titre: str) -> bool:
    with _conn() as c:
        return c.execute("SELECT 1 FROM articles WHERE hash=?", (_hash(titre),)).fetchone() is not None

def db_save(art: dict, statut: str = "selectionne"):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO articles VALUES (?,?,?,?,?,?,?,?,?)", (
            _hash(art["titre"]), art["titre"], art.get("source"), art.get("url"),
            art.get("score_final", art.get("score")), statut, datetime.now(timezone.utc).isoformat(),
            art.get("cle"), art.get("theme")))

def db_cle_exists(cle: str, jours: int = 3) -> bool:
    """Même chiffre clé déjà traité récemment = même sujet sous un autre titre."""
    if not cle:
        return False
    limite = (datetime.now(timezone.utc) - timedelta(days=jours)).isoformat()
    with _conn() as c:
        return c.execute("SELECT 1 FROM articles WHERE cle=? AND cree_le>=?", (cle, limite)).fetchone() is not None

def db_set_status(titre: str, statut: str):
    with _conn() as c:
        c.execute("UPDATE articles SET statut=? WHERE hash=?", (statut, _hash(titre)))