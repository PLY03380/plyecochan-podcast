#!/usr/bin/env python3
"""
Generate SVG images for emotional concepts from CSV.
Creates simple cartoon-style SVGs with text and basic shapes.
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).parent
CSV_FILE = BASE_DIR / "emotional_keywords_complete.csv"
OUTPUT_DIR = BASE_DIR / "images" / "emotional"

# SVG template
SVG_TEMPLATE = '''<svg width="1080" height="1920" viewBox="0 0 1080 1920" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{bg_color}"/>
  <text x="540" y="800" font-family="Arial, sans-serif" font-size="72" font-weight="bold" fill="{text_color}" text-anchor="middle" dominant-baseline="middle">{concept_fr}</text>
  <text x="540" y="900" font-family="Arial, sans-serif" font-size="36" fill="{text_color}" text-anchor="middle" dominant-baseline="middle" opacity="0.7">{concept_en}</text>
  <circle cx="540" cy="1300" r="180" fill="none" stroke="{accent_color}" stroke-width="8" stroke-dasharray="10,10"/>
  <text x="540" y="1310" font-family="Arial, sans-serif" font-size="48" fill="{accent_color}" text-anchor="middle" dominant-baseline="middle">{emoji}</text>
  <text x="540" y="1600" font-family="Arial, sans-serif" font-size="24" fill="{text_color}" text-anchor="middle" dominant-baseline="middle" opacity="0.5">{variant}</text>
</svg>'''

# Color schemes per emotion variant
COLOR_SCHEMES = {
    "Peur (Fear)": {
        "bg_color": "#1a0a0a",
        "text_color": "#ff4444",
        "accent_color": "#ff0000",
    },
    "Surprise (Shock)": {
        "bg_color": "#0a1a2a",
        "text_color": "#ffaa00",
        "accent_color": "#ff8800",
    },
    "Colère (Anger)": {
        "bg_color": "#2a0a0a",
        "text_color": "#ff3333",
        "accent_color": "#cc0000",
    },
    "FOMO": {
        "bg_color": "#0a1a1a",
        "text_color": "#00ff88",
        "accent_color": "#00cc66",
    },
    "Anxiété (Anxiety)": {
        "bg_color": "#1a1a2a",
        "text_color": "#aaaaff",
        "accent_color": "#8888ff",
    },
    "Soulagement/Espoir (Relief)": {
        "bg_color": "#0a2a1a",
        "text_color": "#44ff88",
        "accent_color": "#22cc66",
    },
}


def read_emotional_csv():
    """Read emotional CSV and return rows."""
    rows = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Type", "").strip().lower() == "cartoon svg":
                rows.append(row)
    return rows


def generate_svg(row):
    """Generate SVG content for a row."""
    variant = row.get("Variante Émotion", "").strip()
    colors = COLOR_SCHEMES.get(variant, COLOR_SCHEMES["Peur (Fear)"])

    # Use first char of emoji if available, else default
    emoji = "⚡"
    impact = row.get("Emojis Impact", "").strip()  # Not in this CSV
    # Try to infer from variant
    if "Peur" in variant:
        emoji = "😨"
    elif "Surprise" in variant:
        emoji = "😲"
    elif "Colère" in variant:
        emoji = "😡"
    elif "FOMO" in variant:
        emoji = "💰"
    elif "Anxiété" in variant:
        emoji = "😰"
    elif "Soulagement" in variant or "Espoir" in variant:
        emoji = "😌"

    return SVG_TEMPLATE.format(
        bg_color=colors["bg_color"],
        text_color=colors["text_color"],
        accent_color=colors["accent_color"],
        concept_fr=row.get("Concept FR", "").strip(),
        concept_en=row.get("Concept EN", "").strip(),
        emoji=emoji,
        variant=variant,
    )


def main():
    print("Generating emotional SVGs...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = read_emotional_csv()
    print(f"Found {len(rows)} emotional concepts")

    for row in rows:
        filename = row.get("Nom Fichier", "").strip()
        if not filename:
            continue

        svg_content = generate_svg(row)
        dest = OUTPUT_DIR / filename

        with open(dest, "w", encoding="utf-8") as f:
            f.write(svg_content)

        print(f"  Created: {filename}")

    print(f"\nDone! {len(rows)} SVGs generated in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()