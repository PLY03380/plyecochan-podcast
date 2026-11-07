#!/usr/bin/env python3
"""
chart_cb_purchases.py — Achats nets banques centrales (tonnes/an) 2010-2026
Output: PNG 1080x1920 vertical
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "cb_gold_purchases.csv"
OUT_DIR = ROOT / "charts" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STYLE = {
    "bg": "#0B1D3A",
    "gold": "#FFD700",
    "gold_dark": "#B8860B",
    "gold_light": "#FFF8DC",
    "white": "#FFFFFF",
    "gray": "#888888",
    "red": "#E74C3C",
    "font_title": "DejaVu Sans",
    "font_body": "DejaVu Sans",
    "bar_width": 0.6,
    "grid_alpha": 0.15,
}

def load_data():
    if not DATA_FILE.exists():
        print(f"❌ Fichier non trouvé: {DATA_FILE}")
        print("   Lancez: python fetch_data.py --series cb_gold")
        sys.exit(1)
    df = pd.read_csv(DATA_FILE)
    return df

def create_chart(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=100, facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])

    years = df["year"].values
    tonnes = df["net_purchases_tonnes"].values
    notes = df["note"].values if "note" in df.columns else [""] * len(df)

    # Couleurs : 2022-2026 en or vif, avant en or plus foncé
    colors = [STYLE["gold"] if y >= 2022 else STYLE["gold_dark"] for y in years]

    bars = ax.barh(
        years[::-1], tonnes[::-1],
        height=STYLE["bar_width"],
        color=colors[::-1],
        edgecolor=STYLE["gold"],
        linewidth=0.8,
        zorder=3
    )

    # Valeurs sur barres
    for i, (bar, t, n) in enumerate(zip(bars, tonnes[::-1], notes[::-1])):
        label = f"{t:,.0f} t"
        if n:
            label += f"  ({n})"
        ax.text(
            bar.get_width() + 15, bar.get_y() + bar.get_height()/2,
            label, va="center", ha="left",
            fontsize=14, fontweight="bold", color=STYLE["white"],
            fontfamily=STYLE["font_body"]
        )

    # Ligne de tendance récente (2022+)
    recent_mask = years >= 2022
    if recent_mask.any():
        z = np.polyfit(years[recent_mask], tonnes[recent_mask], 1)
        p = np.poly1d(z)
        ax.plot(p(years[recent_mask]), years[recent_mask], color=STYLE["red"], linestyle="--", linewidth=2, alpha=0.7, zorder=4, label="Tendance 2022+")

    # Axes
    ax.set_xlabel("Tonnes (achats nets annuels)", fontsize=18, color=STYLE["white"], fontfamily=STYLE["font_body"], labelpad=15)
    ax.set_ylabel("Année", fontsize=18, color=STYLE["white"], fontfamily=STYLE["font_body"], labelpad=15)
    ax.tick_params(axis="both", colors=STYLE["gray"], labelsize=14, pad=8)
    ax.invert_yaxis()  # 2026 en haut
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_xlim(0, max(tonnes) * 1.35)

    # Grille
    ax.grid(True, which="major", axis="x", alpha=STYLE["grid_alpha"], color=STYLE["gray"], linestyle="-", linewidth=0.5)
    ax.set_axisbelow(True)

    # Titre
    fig.suptitle(
        "ACHATS NETS D'OR PAR LES BANQUES CENTRALES\n(2010–2026)",
        fontsize=26, fontweight="bold", color=STYLE["gold"], fontfamily=STYLE["font_title"],
        y=0.95
    )

    # Annotation explosion 2022+
    ax.annotate(
        "↗ EXPLOSION 2022–2026\n~800 t/an (record historique)",
        xy=(800, 2022), xytext=(1000, 2018),
        fontsize=18, fontweight="bold", color=STYLE["red"],
        fontfamily=STYLE["font_title"],
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#2C0D0D", edgecolor=STYLE["red"], linewidth=1.5),
        arrowprops=dict(arrowstyle="->", color=STYLE["red"], lw=2, connectionstyle="arc3,rad=0.3"),
        ha="left", va="bottom",
    )

    # Source
    fig.text(
        0.5, 0.02,
        "Source : World Gold Council — Gold Demand Trends (données publiques)  |  Graphique original",
        ha="center", fontsize=12, color=STYLE["gray"], fontfamily=STYLE["font_body"]
    )

    fig.text(0.98, 0.98, "@VotreChaine", ha="right", va="top", fontsize=14, color=STYLE["gray"], alpha=0.5)

    plt.tight_layout(rect=[0.05, 0.05, 0.95, 0.93])

    png_path = OUT_DIR / "cb_purchases.png"
    plt.savefig(png_path, facecolor=STYLE["bg"], bbox_inches="tight")
    print(f"✅ PNG saved: {png_path}")
    plt.close()

def main():
    df = load_data()
    create_chart(df)

if __name__ == "__main__":
    main()