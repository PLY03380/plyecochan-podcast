"""presets.py — Detection automatique des presets video generiques par bloc et langue.

Les presets sont des petites videos (avec leur propre son) placees dans
D:/Cahine youtube economique/video/<Bloc>/<fichier>.mp4

Dossiers attendus :
  video/Impacte pour vous/  -> accroche (debut)
  video/Fait/              -> fait
  video/Pourquoi/          -> pourquoi
  video/Impact/            -> impact
  video/Conclusion/        -> conclusion
  video/Suscribe/          -> subscribe (fin)

Nommage des fichiers : le code langue (fr, en/es, eng/esp) doit apparaitre
dans le nom du fichier, ex. fr.mp4, fact eng.mp4, elecho esp.mp4.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent

PRESET_DIRS = {
    "accroche": "Accroche",
    "fait": "Fait",
    "pourquoi": "Pourquoi",
    "impact": "Impact",
    "conclusion": "Conclusion",
    "subscribe": "Subscribe",
}

LANG_CODES = {
    "fr": ["fr"],
    "en": ["en", "eng"],
    "es": ["es", "esp", "sp"],
}


def find_preset(bloc: str, lang: str) -> Path | None:
    """Retourne le chemin du preset pour un bloc et une langue, ou None si absent."""
    d = ROOT / "video" / PRESET_DIRS.get(bloc, bloc)
    if not d.exists():
        return None
    codes = LANG_CODES.get(lang, [lang])
    for f in sorted(d.glob("*.mp4")):
        name = f.stem.lower()
        if any(c in name for c in codes):
            return f
    return None


def list_presets(lang: str) -> dict[str, Path]:
    """Retourne {bloc: path} pour tous les presets disponibles pour une langue."""
    result = {}
    for bloc in PRESET_DIRS:
        p = find_preset(bloc, lang)
        if p is not None:
            result[bloc] = p
    return result


def organiser_presets() -> None:
    """Renomme automatiquement les fichiers presets pour coherence.

    Scanne video/<Bloc>/ et renomme chaque .mp4 en '<bloc> <lang>.mp4'
    selon le code langue detecte dans le nom du fichier.
    Les fichiers deja bien nommes sont ignores.
    """
    for bloc, dossier in PRESET_DIRS.items():
        d = ROOT / "video" / dossier
        if not d.exists():
            continue
        for f in d.glob("*.mp4"):
            name = f.stem.lower()
            # Detecter le code langue dans le nom
            lang_detecte = None
            for lang, codes in LANG_CODES.items():
                if any(c in name for c in codes):
                    lang_detecte = lang
                    break
            if lang_detecte is None:
                continue
            nom_cible = f"{bloc} {lang_detecte}.mp4"
            cible = d / nom_cible
            if f.name == nom_cible:
                continue  # deja bien nomme
            if cible.exists():
                # eviter d'ecraser : supprimer l'ancien si doublon
                try:
                    f.unlink()
                except Exception:
                    pass
                continue
            try:
                f.rename(cible)
                print(f"[presets] Renomme: {f.name} -> {nom_cible}")
            except Exception as e:
                print(f"[presets] Erreur renommage {f.name}: {e}")


if __name__ == "__main__":
    for lang in ("fr", "en", "es"):
        print(f"=== {lang} ===")
        for bloc, path in list_presets(lang).items():
            print(f"  {bloc}: {path.name}")
