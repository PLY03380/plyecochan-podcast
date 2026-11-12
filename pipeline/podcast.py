"""podcast.py - Generation de podcast audio a partir des videos.

Extrait l'audio des videos, cree un flux RSS, et prepare pour la distribution
sur Spotify, Apple Podcasts, Google Podcasts, etc.
"""
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("podcast")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PODCAST_DIR = ROOT / "output" / "podcast"
AUDIO_DIR = ROOT / "output" / "audio"
VIDEOS_DIR = ROOT / "output" / "videos"
RSS_FILE = PODCAST_DIR / "feed.xml"


def extract_audio(date_str: str = None) -> List[Dict]:
    """Extrait l'audio des videos longues en MP3."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    video_dir = VIDEOS_DIR / date_str
    if not video_dir.exists():
        log.error("Pas de dossier videos pour " + date_str)
        return []

    PODCAST_DIR.mkdir(parents=True, exist_ok=True)
    audio_files = []

    for video_path in sorted(video_dir.glob("*long_*.mp4")):
        lang = video_path.stem.split("_")[-1]
        output_path = PODCAST_DIR / (date_str + "_long_" + lang + ".mp3")

        if output_path.exists():
            log.info("Audio deja extrait: " + output_path.name)
            audio_files.append({"lang": lang, "path": str(output_path), "video": str(video_path)})
            continue

        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe, "-y", "-i", str(video_path),
                "-vn",
                "-acodec", "libmp3lame",
                "-ab", "128k",
                "-ar", "44100",
                "-ac", "2",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and output_path.exists():
                log.info("Audio extrait: " + output_path.name)
                audio_files.append({"lang": lang, "path": str(output_path), "video": str(video_path)})
            else:
                log.error("FFmpeg echoue pour " + video_path.name)
        except Exception as e:
            log.error("Extraction audio echouee: " + str(e))

    return audio_files


def generer_metadata_podcast(date_str: str, lang: str = "fr") -> dict:
    """Genere le titre et la description du podcast via LLM."""
    try:
        from llm import call_llm_json

        script_path = ROOT / "output" / "scripts" / date_str / "script.json"
        script = {}
        if script_path.exists():
            script = json.loads(script_path.read_text(encoding="utf-8"))

        blocs = script.get(lang, {}).get("blocs", {})
        ordre = {"fr": ["accroche", "fait", "pourquoi", "impact", "conclusion"],
                 "en": ["hook", "fact", "why", "impact", "conclusion"],
                 "es": ["gancho", "hecho", "por_que", "impacto", "conclusion"]}[lang]

        texte = "\n".join(k + ": " + str(blocs.get(k, "")) for k in ordre if blocs.get(k))
        titre_script = script.get(lang, {}).get("titre", "")

        prompt = 'Genere un JSON avec titre_podcast (max 60 chars), description (2-3 phrases), tags (5 strings), duree_estimee (minutes). Sujet: ' + texte[:500]

        result = call_llm_json(prompt, max_tokens=300)
        if result and result.get("titre_podcast"):
            log.info("Metadata podcast generee via LLM (" + lang + ")")
            return result
    except Exception as e:
        log.warning("Metadata podcast echouee (" + lang + "): " + str(e))

    return {
        "titre_podcast": "Analyse economique " + date_str + " (" + lang.upper() + ")",
        "description": "Analyse economique quotidienne.",
        "tags": ["economie", "finance", "actualite"],
        "duree_estimee": 10,
    }


def generate_rss(date_str: str = None, podcast_title: str = "PlyChan Economie",
                 podcast_desc: str = "Analyses economiques quotidiennes en 3 langues",
                 podcast_url: str = "https://plychaneconomie.blogspot.com",
                 audio_base_url: str = None) -> str:
    """Genere un flux RSS podcast."""
    from feedgen.feed import FeedGenerator

    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    PODCAST_DIR.mkdir(parents=True, exist_ok=True)

    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title(podcast_title)
    fg.description(podcast_desc)
    fg.link(href=podcast_url, rel="alternate")
    fg.language("fr")
    fg.podcast.itunes_category("Business", "Economics")
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_author("PlyChan")
    fg.podcast.itunes_summary(podcast_desc)
    fg.podcast.itunes_owner(name="PlyChan", email="plychan@gmail.com")
    fg.podcast.itunes_image("https://plychaneconomie.blogspot.com/favicon.ico")

    audio_files = list(PODCAST_DIR.glob("*.mp3"))
    for audio_path in sorted(audio_files, reverse=True)[:30]:
        fe = fg.add_entry()
        parts = audio_path.stem.split("_")
        lang = parts[-1] if parts else "fr"
        date = "_".join(parts[:3]) if len(parts) >= 3 else date_str

        meta = generer_metadata_podcast(date, lang)
        titre_ep = meta.get("titre_podcast", "Analyse economique " + date + " (" + lang.upper() + ")")
        desc_ep = meta.get("description", "Analyse economique quotidienne.")
        duree = meta.get("duree_estimee", 10)

        fe.title(titre_ep)
        fe.description(desc_ep)
        fe.link(href=podcast_url)

        audio_url = (audio_base_url or "https://PLY03380.github.io/plyecochan-podcast/episodes") + "/" + audio_path.name
        fe.enclosure(url=audio_url, length=str(audio_path.stat().st_size), type="audio/mpeg")

        fe.podcast.itunes_duration(str(duree * 60))
        fe.podcast.itunes_explicit("no")

        try:
            file_date = datetime.strptime(date, "%Y-%m-%d")
            fe.published(file_date.replace(tzinfo=timezone.utc))
        except ValueError:
            fe.published(datetime.now(timezone.utc))

    fg.rss_str(pretty=True)
    fg.rss_file(str(RSS_FILE))
    log.info("Flux RSS genere: " + str(RSS_FILE) + " (" + str(len(audio_files)) + " episodes)")
    return str(RSS_FILE)


def run_all(date_str: str = None):
    """Execute tout le pipeline podcast."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    log.info("=== PODCAST PIPELINE ===")

    audio_files = extract_audio(date_str)
    log.info("Audio extraits: " + str(len(audio_files)))

    rss_path = generate_rss(date_str)
    log.info("RSS genere: " + rss_path)

    log.info("")
    log.info("=== DISTRIBUTION ===")
    log.info("1. Hoster les fichiers MP3 sur GitHub Pages (deja fait)")
    log.info("2. Soumettre le RSS a:")
    log.info("   - Spotify: creators.spotify.com")
    log.info("   - Apple: podcasters.apple.com")
    log.info("   - Google: podcasters.google.com")
    log.info("   - Amazon: podcasters.amazon.com")
    log.info("3. URL RSS: https://PLY03380.github.io/plyecochan-podcast/feed.xml")

    return {"audio_files": len(audio_files), "rss_path": rss_path}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", type=str, help="Extraire l'audio pour une date")
    parser.add_argument("--rss", action="store_true", help="Generer le flux RSS")
    parser.add_argument("--all", action="store_true", help="Tout le pipeline")
    args = parser.parse_args()

    if args.extract:
        files = extract_audio(args.extract)
        for f in files:
            print("  " + f["lang"] + ": " + f["path"])
    elif args.rss:
        path = generate_rss()
        print("RSS: " + path)
    elif args.all:
        run_all()
    else:
        print("Usage: python podcast.py --extract DATE | --rss | --all")