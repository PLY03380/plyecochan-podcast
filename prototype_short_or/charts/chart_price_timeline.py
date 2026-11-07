#!/usr/bin/env python3
"""
chart_price_timeline.py — Graphique prix or 2020-2026 avec pic annoté
Output: PNG 1080x1920 (vertical Shorts) + MP4 animation optionnel
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import sys

# ─── Chemins ────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "gold_daily.csv"  # ou gold.csv (mensuel)
OUT_DIR = ROOT / "charts" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Style charte graphique ────────────────────────────────────
STYLE = {
    "bg": "#0B1D3A",           # Bleu foncé
    "gold": "#FFD700",         # Or
    "gold_dark": "#B8860B",    # Or foncé
    "white": "#FFFFFF",
    "gray": "#888888",
    "font_title": "DejaVu Sans",
    "font_body": "DejaVu Sans",
    "line_width": 2.5,
    "grid_alpha": 0.15,
}

# ─── Chargement données ─────────────────────────────────────────
def load_data():
    if not DATA_FILE.exists():
        print(f"❌ Fichier non trouvé: {DATA_FILE}")
        print("   Lancez: python fetch_data.py --series gold_daily")
        sys.exit(1)
    df = pd.read_csv(DATA_FILE)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df

# ─── Graphique principal ────────────────────────────────────────
def create_chart(df: pd.DataFrame, save_png=True, save_mp4=False):
    # Trouver le pic historique (janvier 2026 ~ 5595)
    peak_date = pd.Timestamp("2026-01-29")
    peak_val = 5595

    # Filtrer 2020-2026
    df = df[(df["date"] >= "2020-01-01") & (df["date"] <= "2026-10-12")].copy()

    # Figure verticale 9:16
    fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=100, facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])

    # Courbe principale
    ax.plot(df["date"], df["goldpmgbdb228nlbm"], color=STYLE["gold"], linewidth=STYLE["line_width"], zorder=3)

    # Zone sous courbe
    ax.fill_between(df["date"], df["goldpmgbdb228nlbm"], alpha=0.1, color=STYLE["gold"], zorder=2)

    # Point pic
    ax.scatter([peak_date], [peak_val], color=STYLE["white"], s=120, zorder=5, edgecolor=STYLE["gold"], linewidth=2)
    ax.scatter([peak_date], [peak_val], color=STYLE["gold"], s=60, zorder=6)

    # Annotation pic
    ax.annotate(
        f"RECORD HISTORIQUE\n{peak_val:,.0f} $/oz\n29 jan 2026",
        xy=(peak_date, peak_val),
        xytext=(peak_date + pd.DateOffset(months=8), peak_val + 400),
        fontsize=22, fontweight="bold", color=STYLE["white"],
        fontfamily=STYLE["font_title"],
        bbox=dict(boxstyle="round,pad=0.5", facecolor=STYLE["gold_dark"], edgecolor=STYLE["gold"], linewidth=1.5),
        arrowprops=dict(arrowstyle="->", color=STYLE["gold"], lw=2, connectionstyle="arc3,rad=-0.2"),
        ha="left", va="bottom",
    )

    # Axes
    ax.set_ylabel("Prix ($/oz)", fontsize=18, color=STYLE["white"], fontfamily=STYLE["font_body"], labelpad=15)
    ax.tick_params(axis="both", colors=STYLE["gray"], labelsize=14, pad=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 7)))
    ax.set_xlim(df["date"].min(), df["date"].max() + pd.DateOffset(months=2))

    # Grille
    ax.grid(True, which="major", axis="both", alpha=STYLE["grid_alpha"], color=STYLE["gray"], linestyle="-", linewidth=0.5)
    ax.grid(True, which="minor", axis="x", alpha=STYLE["grid_alpha"]/2, color=STYLE["gray"], linestyle=":", linewidth=0.3)

    # Titre
    fig.suptitle(
        "ÉVOLUTION DU PRIX DE L'OR (2020–2026)",
        fontsize=28, fontweight="bold", color=STYLE["gold"], fontfamily=STYLE["font_title"],
        y=0.96
    )

    # Source
    fig.text(
        0.5, 0.02,
        "Source : FRED (St. Louis Fed) — GOLDPMGBD228NLBM  |  Graphique original",
        ha="center", fontsize=12, color=STYLE["gray"], fontfamily=STYLE["font_body"]
    )

    # Watermark logo (optionnel)
    fig.text(0.98, 0.98, "@VotreChaine", ha="right", va="top", fontsize=14, color=STYLE["gray"], alpha=0.5)

    plt.tight_layout(rect=[0.05, 0.05, 0.95, 0.94])

    if save_png:
        png_path = OUT_DIR / "price_timeline.png"
        plt.savefig(png_path, facecolor=STYLE["bg"], bbox_inches="tight")
        print(f"✅ PNG saved: {png_path}")

    if save_mp4:
        # Animation simple (nécessite ffmpeg)
        try:
            import matplotlib.animation as animation
            mp4_path = OUT_DIR / "price_timeline.mp4"
            print("⚠️ Animation MP4 non implémentée (optionnel)")
        except Exception as e:
            print(f"⚠️ MP4 skipped: {e}")

    plt.close()

# ─── Main ───────────────────────────────────────────────────────
def main():
    df = load_data()
    create_chart(df, save_png=True, save_mp4=False)

if __name__ == "__main__":
    main()