"""podcast_publish.py — Automatise la publication du podcast sur GitHub Pages.

Extrait l'audio, genere le RSS, copie dans docs/, commit et push sur GitHub.

Usage:
    python pipeline/podcast_publish.py 2026-11-09   # Pour une date
    python pipeline/podcast_publish.py               # Pour aujourd'hui
"""
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("podcast_publish")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def publish(date_str: str = None):
    """Publie le podcast sur GitHub Pages."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    log.info(f"=== PUBLICATION PODCAST - {date_str} ===")

    # 1. Extraire l'audio
    try:
        from pipeline.podcast import extract_audio, generate_rss
        audio_files = extract_audio(date_str)
        log.info(f"Audio extraits: {len(audio_files)}")
    except Exception as e:
        log.error(f"Extraction audio echouee: {e}")
        return False

    # 2. Generer le RSS
    try:
        rss_path = generate_rss(date_str, audio_base_url="https://PLY03380.github.io/plyecochan-podcast/episodes")
        log.info(f"RSS genere: {rss_path}")
    except Exception as e:
        log.error(f"Generation RSS echouee: {e}")
        return False

    # 3. Copier dans docs/
    import shutil
    docs_dir = ROOT / "docs"
    episodes_dir = docs_dir / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)

    podcast_dir = ROOT / "output" / "podcast"
    for mp3 in podcast_dir.glob("*.mp3"):
        dest = episodes_dir / mp3.name
        shutil.copy2(mp3, dest)
        log.info(f"Copie: {mp3.name}")

    # Copier le RSS
    rss_src = podcast_dir / "feed.xml"
    if rss_src.exists():
        shutil.copy2(rss_src, docs_dir / "feed.xml")
        log.info("RSS copie dans docs/feed.xml")

    # 4. Git commit + push
    try:
        subprocess.run(["git", "add", "docs/"], cwd=str(ROOT), check=True, capture_output=True)

        commit_msg = f"Update podcast {date_str}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(ROOT), capture_output=True, text=True
        )
        if "nothing to commit" in result.stdout + result.stderr:
            log.info("Rien a commiter (pas de changement)")
            return True

        # Push via token from env
        token = os.getenv("GITHUB_TOKEN", "")
        if token:
            url = f"https://{token}@github.com/PLY03380/plyecochan-podcast.git"
        else:
            url = "https://github.com/PLY03380/plyecochan-podcast.git"
        result = subprocess.run(
            ["git", "push", url, "master"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log.info("Push GitHub OK")
            return True
        else:
            log.error(f"Push echoue: {result.stderr[:200]}")
            return False
    except Exception as e:
        log.error(f"Git push echoue: {e}")
        return False


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    ok = publish(date_arg)
    print("OK" if ok else "ECHEC")