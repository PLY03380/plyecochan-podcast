"""visuels.py — Selectionne des images de la bibliotheque (changement ~toutes les 5s)."""
import json, shutil, logging, math
from pathlib import Path
from datetime import datetime
import config

log = logging.getLogger("visuels")

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "images" / "manifest.json"

# Concepts candidats par bloc (ids du manifest)
CANDIDATS = {
    "accroche": ["t1_record", "t1_firsttime", "t1_unprecedented", "t1_historic_peak", "t1_crash", "t1_collapse"],
    "fait": ["t2_cpi", "t2_inflationreport", "t2_jobsreport", "t2_nfp", "t2_unemployment", "t2_jobs", "t2_pce"],
    "pourquoi": ["t1_ratecut", "t1_ratehike", "t2_fed", "t2_bce", "t1_opec", "t2_opec", "t1_straithormuz", "t2_oil"],
    "impact": ["t3_employment", "t3_wagegrowth", "t2_unemployment", "t2_jobs", "t3_layoffs", "t2_sp500", "t2_nasdaq"],
    "conclusion": ["t2_dxy", "t1_alltimelow", "t1_record", "t3_employment", "emo_fomo_miss", "emo_relief_good"],
    # Blocs supplementaires pour les videos longues
    "introduction": ["t1_record", "t1_firsttime", "t1_unprecedented", "emo_surprise_shock"],
    "contexte": ["t2_cpi", "t2_inflationreport", "t3_g7", "t3_g20"],
    "analyse": ["t2_cpi", "t2_pce", "t2_inflationreport", "t2_jobsreport"],
    "opinion": ["emo_relief_good", "emo_fomo_miss", "emo_peur_menace", "t1_record"],
    "ia_analysis": ["t2_sp500", "t2_nasdaq", "t3_earnings", "t3_revenue"],
    "perspectives": ["t1_ratecut", "t1_ratehike", "t2_fed", "t2_bce", "t2_dxy"],
}

_manifest_cache = None
DUREE_PAR_IMAGE = 5.0  # secondes cibles par image (Shorts)
DUREE_PAR_IMAGE_LONG = 10.0  # secondes cibles par image (vidéos longues)


def _load_manifest():
    global _manifest_cache
    if _manifest_cache is None:
        if MANIFEST_PATH.exists():
            _manifest_cache = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["concepts"]
        else:
            _manifest_cache = {}
    return _manifest_cache


def _pick_images(cid_list, used, count):
    """Selectionne 'count' images distinctes parmi les candidats."""
    result = []
    for cid in cid_list:
        if len(result) >= count:
            break
        info = _load_manifest().get(cid)
        if not info:
            continue
        p = ROOT / info["path"]
        if not p.exists() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp") or p in used:
            continue
        used.add(p)
        result.append(p)
    # Fallback si pas assez
    if len(result) < count:
        for cid, info in _load_manifest().items():
            if len(result) >= count:
                break
            p = ROOT / info["path"]
            if p.exists() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and p not in used:
                used.add(p)
                result.append(p)
    return result


def selectionner_images(fait: dict, durees_blocs: dict = None, mode: str = "short") -> list[tuple[str, list[Path]]]:
    """Selectionne des images par bloc depuis la bibliotheque.

    mode="short" : blocs Shorts (5 blocs, ~5s par image)
    mode="long" : blocs longs (10 blocs, ~10s par image)
    durees_blocs: dict {bloc: duree_secondes} pour calculer le nombre d'images.
    Retourne [(bloc, [path1, path2, ...]), ...].
    """
    duree_par_image = DUREE_PAR_IMAGE_LONG if mode == "long" else DUREE_PAR_IMAGE

    if mode == "long":
        blocs_list = ["introduction", "contexte", "fait", "analyse", "pourquoi",
                      "impact", "opinion", "ia_analysis", "perspectives", "conclusion"]
    else:
        blocs_list = ["accroche", "fait", "pourquoi", "impact", "conclusion"]

    chosen = []
    used = set()
    for bloc in blocs_list:
        if durees_blocs and bloc in durees_blocs:
            dur = durees_blocs[bloc]
            n = max(1, math.ceil(dur / duree_par_image))
        else:
            n = 1
        imgs = _pick_images(CANDIDATS.get(bloc, []), used, n)
        if not imgs:
            raise RuntimeError(f"Aucune image disponible pour le bloc {bloc}")
        chosen.append((bloc, imgs))
        log.info(f"Images pour {bloc}: {len(imgs)} (duree ~{durees_blocs.get(bloc, '?') if durees_blocs else '?'})")
    return chosen


def generer_visuels(fait: dict, data_dir=None, out_base=None, durees_blocs=None, mode: str = "short"):
    """Selectionne des images et les copie dans output/visuels/YYYY-MM-DD/.

    Retourne la liste de tuples (bloc, [path1, path2, ...]).
    """
    from pathlib import Path as P
    if out_base is None:
        out_base = P(config.OUTPUT_DIR) / "visuels" if hasattr(config, "OUTPUT_DIR") else P("output") / "visuels"
        today = datetime.now().strftime("%Y-%m-%d")
        out_dir = P(out_base) / today
    else:
        out_dir = P(out_base)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Nettoyer les anciennes images du jour
    for old in out_dir.glob("img_*"):
        try:
            old.unlink()
        except Exception:
            pass

    chosen = selectionner_images(fait, durees_blocs, mode=mode)
    result = []
    global_idx = 0
    for bloc, imgs in chosen:
        bloc_paths = []
        for img in imgs:
            dst = out_dir / f"img_{global_idx:02d}_{bloc}{img.suffix}"
            shutil.copy2(img, dst)
            bloc_paths.append(dst)
            global_idx += 1
        result.append((bloc, bloc_paths))
        log.info(f"Images copiees pour {bloc}: {len(bloc_paths)}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fait_test = {"titre": "Test", "chiffre_cle": "2 710 $", "date": "20/10/2026", "source": "test"}
    # Simuler des durees
    durees = {"accroche": 5, "fait": 8, "pourquoi": 12, "impact": 15, "conclusion": 8}
    res = generer_visuels(fait_test, durees_blocs=durees)
    for bloc, paths in res:
        print(f"  {bloc}: {len(paths)} images")
        for p in paths:
            print(f"    {p.name}")