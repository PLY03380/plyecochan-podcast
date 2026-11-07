#!/usr/bin/env python3
"""
🏗️ Image Library Builder — Wikimedia Commons + SVG Generation
Télécharge images "Image Libre" depuis Wikimedia, génère SVG pour "Cartoon SVG",
produit manifest.json pour visuels.py
"""

import csv
import json
import os
import re
import logging
import shutil
from pathlib import Path
from urllib.parse import urlparse, quote
from datetime import datetime
import requests
from tqdm import tqdm

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(__file__).parent
CSV_DIR = BASE_DIR / "Slide"
OUTPUT_DIR = BASE_DIR / "images"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

CSV_FILES = {
    "tier1": "tier1_keywords_complete.csv",
    "tier2": "tier2_keywords_complete.csv",
    "tier3": "tier3_keywords_complete.csv",
    "emotional": "emotional_keywords_complete.csv",
    "trend2026": "trend2026_keywords_complete.csv",
}

# Charte graphique (depuis visuels.py)
STYLE = {
    "bg": "#0B1D3A",
    "gold": "#FFD700",
    "gold_dark": "#B8860B",
    "white": "#FFFFFF",
    "gray": "#888888",
    "red": "#E74C3C",
    "green": "#2ECC71",
    "blue": "#3498DB",
}

# Wikimedia Commons API
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_HEADERS = {"User-Agent": "EcoShortsBot/1.0 (https://github.com/; contact@)"}
WIKIMEDIA_LICENSES = ["CC0", "CC-BY", "CC-BY-SA", "CC-BY-2.0", "CC-BY-3.0", "CC-BY-4.0"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "build_image_library.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ============================================================================
# CSV PARSING
# ============================================================================
def parse_all_csvs() -> dict:
    """Parse tous les CSV, retourne {tier: [concepts]}"""
    all_concepts = {}
    for tier, filename in CSV_FILES.items():
        path = CSV_DIR / filename
        if not path.exists():
            log.warning(f"CSV non trouvé: {path}")
            all_concepts[tier] = []
            continue

        concepts = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                concept = {
                    "tier": tier,
                    "id": row.get("Nom Fichier", "").replace(".jpg", "").replace(".svg", ""),
                    "concept_fr": row.get("Concept FR", ""),
                    "concept_en": row.get("Concept EN", ""),
                    "concept_es": row.get("Concept ES", ""),
                    "type": row.get("Type", "").strip(),
                    "filename": row.get("Nom Fichier", ""),
                    "emoji": row.get("Emojis Impact", row.get("Emojis", row.get("Impact Bonus", ""))),
                    "category": row.get("Catégorie", row.get("Variante Émotion", row.get("Tendance 2026", ""))),
                }
                # Nettoyage ID
                concept["id"] = concept["id"].replace(" ", "_").replace("-", "_")
                if concept["id"] and concept["filename"]:
                    concepts.append(concept)
        all_concepts[tier] = concepts
        log.info(f"{tier}: {len(concepts)} concepts")
    return all_concepts


# ============================================================================
# WIKIMEDIA COMMONS DOWNLOADER
# ============================================================================
def search_wikimedia(query: str, limit: int = 3) -> list[dict]:
    """Recherche images sur Wikimedia Commons, retourne liste de résultats avec URL directe et licence"""
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": f"{query} filetype:bitmap",
        "srlimit": limit,
        "srnamespace": 6,  # File namespace
    }
    try:
        r = requests.get(WIKIMEDIA_API, params=params, headers=WIKIMEDIA_HEADERS, timeout=10)
        r.raise_for_status()
        results = r.json().get("query", {}).get("search", [])
        # Récupérer détails (URL, licence) pour chaque résultat
        detailed = []
        for item in results:
            title = item["title"]
            info = get_file_info(title)
            if info:
                detailed.append(info)
        return detailed
    except Exception as e:
        log.debug(f"Wikimedia search error for '{query}': {e}")
        return []


def get_file_info(title: str) -> dict | None:
    """Récupère URL directe, licence, dimensions pour un fichier Wikimedia"""
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": 1920,
    }
    try:
        r = requests.get(WIKIMEDIA_API, params=params, headers=WIKIMEDIA_HEADERS, timeout=10)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        for page in pages.values():
            if "imageinfo" in page:
                info = page["imageinfo"][0]
                extmeta = info.get("extmetadata", {})
                license_val = extmeta.get("LicenseShortName", {}).get("value", "").upper()
                # Filtrer licences acceptables
                if not any(lic in license_val for lic in WIKIMEDIA_LICENSES):
                    return None
                return {
                    "title": title,
                    "url": info["url"],
                    "license": license_val,
                    "width": info.get("width"),
                    "height": info.get("height"),
                    "mime": info.get("mime"),
                    "attribution": extmeta.get("Artist", {}).get("value", "Wikimedia Commons"),
                }
    except Exception as e:
        log.debug(f"File info error for {title}: {e}")
    return None


def download_wikimedia_image(url: str, filepath: Path, timeout: int = 15) -> bool:
    """Télécharge une image depuis Wikimedia"""
    try:
        if filepath.exists():
            return True
        r = requests.get(url, headers=WIKIMEDIA_HEADERS, timeout=timeout, stream=True)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        log.debug(f"Downloaded: {filepath.name}")
        return True
    except Exception as e:
        log.warning(f"Download failed {url}: {e}")
        return False


def build_search_query(concept: dict) -> str:
    """Construit une requête de recherche optimisée depuis le concept"""
    # Priorité: concept EN (plus universel), puis FR
    base = concept["concept_en"] or concept["concept_fr"]
    # Nettoyer
    base = re.sub(r"[\(\)\[\]]", "", base).strip()
    # Mots-clés économiques pour contexte
    if concept["tier"] in ("tier1", "tier2", "tier3", "trend2026"):
        return f"{base} economy finance chart"
    elif concept["tier"] == "emotional":
        return f"{base} abstract concept"
    return base


# ============================================================================
# SVG GENERATOR (Cartoon SVG concepts)
# ============================================================================
SVG_TEMPLATES = {
    # --- PEUR ---
    "peur_menace": ("⚠️", "triangle_alert"),
    "peur_destroy": ("💥", "explosion"),
    "peur_wipeout": ("🧹", "wipe"),
    "peur_erodes": ("🌊", "erosion"),
    "peur_devours": ("👹", "devour"),
    "peur_collapse": ("🏚️", "collapse"),
    "peur_plunge": ("📉", "plunge"),
    "peur_vanish": ("💨", "vanish"),
    "peur_urgent": ("⏰", "urgent"),
    "peur_now": ("🔴", "now"),
    "peur_window": ("🪟", "window_closing"),
    "peur_savings": ("💰", "savings"),
    "peur_retirement": ("👴", "retirement"),

    # --- SURPRISE ---
    "surprise_never": ("😲", "never_seen"),
    "surprise_unprecedented": ("🌟", "unprecedented"),
    "surprise_historic": ("🏛️", "historic"),
    "surprise_firsttime": ("1️⃣", "first_time"),
    "surprise_unexpected": ("🎭", "unexpected"),
    "surprise_shock": ("⚡", "shock"),
    "surprise_staggering": ("🤯", "staggering"),
    "surprise_gamechanger": ("🎮", "game_changer"),
    "surprise_odds": ("🎲", "odds"),
    "surprise_twist": ("🔄", "twist"),

    # --- COLÈRE ---
    "anger_while": ("⏳", "while_you"),
    "anger_banks": ("🏦", "banks"),
    "anger_hidden": ("🤫", "hidden"),
    "anger_scandal": ("📢", "scandal"),
    "anger_unacceptable": ("🚫", "unacceptable"),
    "anger_wages": ("📊", "wages"),
    "anger_profits": ("💸", "profits"),
    "anger_elites": ("🎩", "elites"),
    "anger_double": ("⚖️", "double_standard"),

    # --- FOMO ---
    "fomo_miss": ("🚀", "dont_miss"),
    "fomo_actnow": ("⚡", "act_now"),
    "fomo_window": ("🪟", "window_open"),
    "fomo_acttoday": ("📅", "act_today"),
    "fomo_surge": ("📈", "before_surge"),
    "fomo_unique": ("💎", "unique"),
    "fomo_stilltime": ("⏳", "still_time"),
    "fomo_smartmoney": ("🧠", "smart_money"),

    # --- ANXIÉTÉ ---
    "anxiety_uncertain": ("🌫️", "uncertainty"),
    "anxiety_worry": ("😰", "worry"),
    "anxiety_concern": ("🤔", "concern"),
    "anxiety_unstable": ("⚖️", "unstable"),
    "anxiety_tension": ("🔗", "tension"),
    "anxiety_turbulent": ("🌪️", "turbulence"),
    "anxiety_risk": ("⚠️", "risk"),
    "anxiety_vulnerable": ("🛡️", "vulnerable"),
    "anxiety_fragile": ("🥚", "fragile"),
    "anxiety_pressure": ("📊", "pressure"),

    # --- ESPOIR/SOULAGEMENT ---
    "relief_good": ("🌅", "good_news"),
    "relief_finally": ("✅", "finally"),
    "relief_improving": ("📈", "improving"),
    "relief_rebound": ("↩️", "rebound"),
    "relief_recovery": ("🌱", "recovery"),
    "relief_stable": ("⚖️", "stable"),
    "relief_protect": ("🛡️", "protect"),
    "relief_solution": ("💡", "solution"),
    "relief_howto": ("📋", "howto"),
    "relief_howprotect": ("🛡️", "protect"),

    # --- TIER 1 CARTOON SVG ---
    "t1_historic_peak": ("🏔️", "peak"),
    "t1_qe": ("🖨️", "money_printer"),
    "t1_qe_short": ("💰", "qe"),
    "t1_qt": ("🛑", "money_shrink"),
    "t1_qt_short": ("📉", "qt"),

    # --- TIER 3 CARTOON SVG ---
    "t3_softlanding": ("✈️", "soft_landing"),
    "t2_invertedyield": ("📈", "inverted_yield"),

    # Fallback générique
    "default": ("📊", "chart"),
}


def generate_svg(concept_id: str, concept_fr: str, tier: str) -> str:
    """Génère un SVG 1080x1920 pour un concept Cartoon"""
    # Trouver template
    template_key = concept_id.lower().replace(".svg", "")
    emoji, icon_type = SVG_TEMPLATES.get(template_key, SVG_TEMPLATES["default"])

    # Couleur selon tier/émotion
    if tier == "emotional":
        if "peur" in template_key:
            accent = STYLE["red"]
        elif "surprise" in template_key:
            accent = STYLE["gold"]
        elif "anger" in template_key or "colere" in template_key:
            accent = STYLE["red"]
        elif "fomo" in template_key:
            accent = STYLE["gold"]
        elif "anxiety" in template_key:
            accent = STYLE["blue"]
        elif "relief" in template_key:
            accent = STYLE["green"]
        else:
            accent = STYLE["gold"]
    else:
        accent = STYLE["gold"]

    svg = f'''<svg width="1080" height="1920" viewBox="0 0 1080 1920" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="1080" height="1920" fill="{STYLE['bg']}"/>

  <!-- Central emoji/icon -->
  <text x="540" y="800" font-size="280" text-anchor="middle" dominant-baseline="middle">{emoji}</text>

  <!-- Label FR -->
  <text x="540" y="1150" font-size="56" font-weight="bold" fill="{STYLE['white']}" text-anchor="middle" font-family="system-ui, sans-serif">{concept_fr}</text>

  <!-- Accent line -->
  <line x1="340" y1="1230" x2="740" y2="1230" stroke="{accent}" stroke-width="4" stroke-linecap="round"/>

  <!-- Subtitle -->
  <text x="540" y="1300" font-size="36" fill="{STYLE['gray']}" text-anchor="middle" font-family="system-ui, sans-serif">Concept visuel — EcoShorts</text>

  <!-- Watermark -->
  <text x="1040" y="1880" font-size="24" fill="{STYLE['gray']}" text-anchor="end" opacity="0.4" font-family="system-ui, sans-serif">@EcoShorts</text>
</svg>'''
    return svg


# ============================================================================
# MAIN BUILDER
# ============================================================================
def build_library():
    log.info("=== BUILD IMAGE LIBRARY START ===")

    # 1. Parse CSVs
    all_concepts = parse_all_csvs()

    # 2. Prepare directories
    for tier in CSV_FILES.keys():
        (OUTPUT_DIR / tier).mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "version": "1.0",
        "style": STYLE,
        "concepts": {}
    }

    stats = {"total": 0, "wikimedia": 0, "svg_generated": 0, "skipped": 0, "errors": 0, "from_slide": 0}

    # Répertoire source des vraies images
    SLIDE_IMAGES = BASE_DIR / "Slide" / "images"

    # 3. Process each concept
    for tier, concepts in all_concepts.items():
        log.info(f"\n--- Processing {tier} ({len(concepts)} concepts) ---")

        for concept in tqdm(concepts, desc=tier):
            stats["total"] += 1
            concept_id = concept["id"]
            filename = concept["filename"]
            out_path = OUTPUT_DIR / tier / filename

            # 1. D'abord vérifier Slide/images/ (images réelles)
            slide_path = SLIDE_IMAGES / tier / filename
            if slide_path.exists():
                # Copier vers OUTPUT_DIR
                out_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(slide_path, out_path)
                manifest["concepts"][concept_id] = {
                    "path": str(out_path.relative_to(BASE_DIR)),
                    "tier": tier,
                    "type": concept["type"],
                    "concept_fr": concept["concept_fr"],
                    "concept_en": concept["concept_en"],
                    "license": "Slide/images",
                    "attribution": "Slide/images (real image)"
                }
                stats["from_slide"] += 1
                continue

            # 2. Déjà existe dans OUTPUT_DIR ?
            if out_path.exists():
                manifest["concepts"][concept_id] = {
                    "path": str(out_path.relative_to(BASE_DIR)),
                    "tier": tier,
                    "type": concept["type"],
                    "concept_fr": concept["concept_fr"],
                    "concept_en": concept["concept_en"],
                    "license": "cached",
                    "attribution": "cached"
                }
                continue

            if concept["type"] == "Cartoon SVG":
                # Générer SVG
                svg_content = generate_svg(concept_id, concept["concept_fr"], tier)
                # Sauvegarder en .svg (même si filename dit .jpg)
                svg_path = out_path.with_suffix(".svg")
                try:
                    with open(svg_path, "w", encoding="utf-8") as f:
                        f.write(svg_content)
                    manifest["concepts"][concept_id] = {
                        "path": str(svg_path.relative_to(BASE_DIR)),
                        "tier": tier,
                        "type": "Cartoon SVG",
                        "concept_fr": concept["concept_fr"],
                        "concept_en": concept["concept_en"],
                        "license": "generated",
                        "attribution": "EcoShorts (generated)"
                    }
                    stats["svg_generated"] += 1
                except Exception as e:
                    log.error(f"SVG generation failed for {concept_id}: {e}")
                    stats["errors"] += 1

            elif concept["type"] == "Image Libre":
                # Rechercher sur Wikimedia
                query = build_search_query(concept)
                results = search_wikimedia(query, limit=3)

                downloaded = False
                for result in results:
                    # Accepter toute image (on pourra recadrer plus tard)
                    w, h = result.get("width", 0), result.get("height", 0)

                    # Déterminer extension
                    ext = ".jpg"
                    if result["mime"]:
                        if "png" in result["mime"]:
                            ext = ".png"
                        elif "webp" in result["mime"]:
                            ext = ".webp"
                        elif "svg" in result["mime"]:
                            ext = ".svg"

                    target_path = out_path.with_suffix(ext)
                    if download_wikimedia_image(result["url"], target_path):
                        manifest["concepts"][concept_id] = {
                            "path": str(target_path.relative_to(BASE_DIR)),
                            "tier": tier,
                            "type": "Image Libre",
                            "concept_fr": concept["concept_fr"],
                            "concept_en": concept["concept_en"],
                            "license": result["license"],
                            "attribution": result["attribution"],
                            "source_url": result["url"]
                        }
                        stats["wikimedia"] += 1
                        downloaded = True
                        break

                if not downloaded:
                    log.warning(f"No suitable Wikimedia image for {concept_id} (query: {query})")
                    # Fallback: générer SVG simple
                    svg_content = generate_svg(concept_id, concept["concept_fr"], tier)
                    svg_path = out_path.with_suffix(".svg")
                    with open(svg_path, "w", encoding="utf-8") as f:
                        f.write(svg_content)
                    manifest["concepts"][concept_id] = {
                        "path": str(svg_path.relative_to(BASE_DIR)),
                        "tier": tier,
                        "type": "Image Libre (fallback SVG)",
                        "concept_fr": concept["concept_fr"],
                        "concept_en": concept["concept_en"],
                        "license": "generated",
                        "attribution": "EcoShorts (fallback)"
                    }
                    stats["svg_generated"] += 1

            else:
                stats["skipped"] += 1

    # 4. Save manifest
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 5. Summary
    log.info("\n=== BUILD COMPLETE ===")
    log.info(f"Total concepts: {stats['total']}")
    log.info(f"Wikimedia downloaded: {stats['wikimedia']}")
    log.info(f"SVG generated: {stats['svg_generated']}")
    log.info(f"Skipped: {stats['skipped']}")
    log.info(f"Errors: {stats['errors']}")
    log.info(f"Manifest: {MANIFEST_PATH}")

    return manifest, stats


if __name__ == "__main__":
    build_library()