#!/usr/bin/env python3
"""
chart_annual_perf.py — Performance annuelle or (%) 2015-2025
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
DATA_FILE = ROOT / "data" / "gold_daily.csv"  # mensuel aussi possible
OUT_DIR = ROOT / "charts" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STYLE = {
    "bg": "#0B1D3A",
    "gold": "#FFD700",
    "gold_dark": "#B8860B",
    "green": "#2ECC71",
    "red": "#E74C3C",
    "white": "#FFFFFF",
    "gray": "#888888",
    "font_title": "DejaVu Sans",
    "font_body": "DejaVu Sans",
    "bar_width": 0.6,
    "grid_alpha": 0.15,
}

def compute_annual_perf(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule performance annuelle % depuis prix fin d'année."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Dernier prix de chaque année
    yearly = df.groupby(df["date"].dt.year).last().reset_index()
    yearly.columns = ["year", "price"]
    yearly["pct_change"] = yearly["price"].pct_change() * 100

    # Filtrer 2015-2025
    yearly = yearly[(yearly["year"] >= 2015) & (yearly["year"] <= 2025)]
    return yearly

def create_chart(perf_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=100, facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])

    years = perf_df["year"].values
    pct = perf_df["pct_change"].values

    # Couleurs : 2025 en or vif, positives en vert, négatives en rouge
    colors = []
    for i, (y, v) in enumerate(zip(years, pct)):
        if y == 2025:
            colors.append(STYLE["gold"])
        elif v >= 0:
            colors.append(STYLE["green"])
        else:
            colors.append(STYLE["red"])

    bars = ax.barh(
        years[::-1], pct[::-1],
        height=STYLE["bar_width"],
        color=colors[::-1],
        edgecolor=STYLE["white"],
        linewidth=0.5,
        zorder=3
    )

    # Valeurs sur barres
    for bar, v in zip(bars, pct[::-1]):
        label = f"{v:+.1f}%"
        ax.text(
            bar.get_width() + (1 if v >= 0 else -1), bar.get_y() + bar.get_height()/2,
            label, va="center", ha="left" if v >= 0 else "right",
            fontsize=14, fontweight="bold", color=STYLE["white"],
            fontfamily=STYLE["font_body"]
        )

    # Ligne zéro
    ax.axvline(0, color=STYLE["gray"], linewidth=0.8, alpha=0.5, zorder=2)

    # Axes
    ax.set_xlabel("Performance annuelle (%)", fontsize=18, color=STYLE["white"], fontfamily=STYLE["font_body"], labelpad=15)
    ax.set_ylabel("Année", fontsize=18, color=STYLE["white"], fontfamily=STYLE["font_body"], labelpad=15)
    ax.tick_params(axis="both", colors=STYLE["gray"], labelsize=14, pad=8)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+.0f}%"))
    max_abs = max(abs(pct.min()), abs(pct.max()))
    ax.set_xlim(-max_abs * 1.3, max_abs * 1.3)

    # Grille
    ax.grid(True, which="major", axis="x", alpha=STYLE["grid_alpha"], color=STYLE["gray"], linestyle="-", linewidth=0.5)
    ax.set_axisbelow(True)

    # Titre
    fig.suptitle(
        "PERFORMANCE ANNUELLE DE L'OR (2015–2025)",
        fontsize=26, fontweight="bold", color=STYLE["gold"], fontfamily=STYLE["font_title"],
        y=0.95
    )

    # Annotation 2025
    idx_2025 = np.where(years == 2025)[0]
    if len(idx_2025):
        v = pct[idx_2025[0]]
        ax.annotate(
            f"2025 : {v:+.1f}%\nMEILLEURE ANNÉE DEPUIS 1979",
            xy=(v, 2025), xytext=(v + 10, 2023),
            fontsize=18, fontweight="bold", color=STYLE["gold"],
            fontfamily=STYLE["font_title"],
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#1A1A00", edgecolor=STYLE["gold"], linewidth=1.5),
            arrowprops=dict(arrowstyle="->", color=STYLE["gold"], lw=2, connectionstyle="arc3,rad=-0.3"),
            ha="left", va="bottom",
        )

    # Source
    fig.text(
        0.5, 0.02,
        "Source : FRED (GOLDPMGBD228NLBM) — Calcul performance fin d'année  |  Graphique original",
        ha="center", fontsize=12, color=STYLE["gray"], fontfamily=STYLE["font_body"]
    )

    fig.text(0.98, 0.98, "@VotreChaine", ha="right", va="top", fontsize=14, color=STYLE["gray"], alpha=0.5)

    plt.tight_layout(rect=[0.05, 0.05, 0.95, 0.93])

    png_path = OUT_DIR / "annual_perf.png"
    plt.savefig(png_path, facecolor=STYLE["bg"], bbox_inches="tight")
    print(f"✅ PNG saved: {png_path}")
    plt.close()

def main():
    if not DATA_FILE.exists():
        print(f"❌ Fichier non trouvé: {DATA_FILE}")
        print("   Lancez: python fetch_data.py --series gold_daily")
        sys.exit(1)
    df = pd.read_csv(DATA_FILE)
    perf_df = compute_annual_perf(df)
    print(perf_df[["year", "price", "pct_change"]].to_string(index=False))
    create_chart(perf_df)

if __name__ == "__main__":
    main()