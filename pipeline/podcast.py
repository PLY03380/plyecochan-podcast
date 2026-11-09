"""podcast.py — Generation de podcast audio a partir des videos.

Extrait l'audio des videos, cree un flux RSS, et prepare pour la distribution
sur Spotify, Apple Podcasts, Google Podcasts, etc.

Usage:
    python pipeline/podcast.py --extract 2026-11-09   # Extraire l'audio
    python pipeline/podcast.py --rss                  # Generer le flux RSS
    python pipeline/podcast.py --all                 # Tout
"""
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
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
        log.error(f"Pas de dossier videos pour {date_str}")
        return []

    PODCAST_DIR.mkdir(parents=True, exist_ok=True)
    audio_files = []

    for video_path in sorted(video_dir.glob("*long_*.mp4")):
        lang = video_path.stem.split("_")[-1]  # fr, en, es
        output_path = PODCAST_DIR / f"{date_str}_long_{lang}.mp3"

        if output_path.exists():
            log.info(f"Audio deja extrait: {output_path.name}")
            audio_files.append({"lang": lang, "path": str(output_path), "video": str(video_path)})
            continue

        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            # FFmpeg: extraire l'audio en MP3
            cmd = [
                ffmpeg_exe, "-y", "-i", str(video_path),
                "-vn",  # Pas de video
                "-acodec", "libmp3lame",
                "-ab", "128k",
                "-ar", "44100",
                "-ac", "2",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and output_path.exists():
                log.info(f"Audio extrait: {output_path.name} ({output_path.stat().st_size // 1024} KB)")
                audio_files.append({"lang": lang, "path": str(output_path), "video": str(video_path)})
            else:
                log.error(f"FFmpeg echoue pour {video_path.name}: {result.stderr[:200]}")
        except Exception as e:
            log.error(f"Extraction audio echouee: {e}")

    return audio_files


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

    # Ajouter les episodes (audio files)
    audio_files = list(PODCAST_DIR.glob("*.mp3"))
    for audio_path in sorted(audio_files, reverse=True)[:30]:  # 30 derniers episodes
        fe = fg.add_entry()
        # Extraire les infos du nom de fichier
        parts = audio_path.stem.split("_")
        lang = parts[-1] if parts else "fr"
        date = "_".join(parts[:3]) if len(parts) >= 3 else date_str

        fe.title(f"Analyse economique {date} ({lang.upper()})")
        fe.description(f"Analyse economique quotidienne en {lang.upper()}. Sujet du jour disponible sur PlyChan.")
        fe.link(href=podcast_url)

        # Enclosure (fichier audio)
        audio_url = f"{audio_base_url or 'https://plychaneconomie.blogspot.com/podcast'}/{audio_path.name}"
        fe.enclosure(url=audio_url, length=str(audio_path.stat().st_size), type="audio/mpeg")

        # iTunes tags
        fe.podcast.itunes_duration("600")  # 10 min par defaut
        fe.podcast.itunes_explicit("no")

        # Date de publication
        try:
            file_date = datetime.strptime(date, "%Y-%m-%d")
            from datetime import timezone
            fe.published(file_date.replace(tzinfo=timezone.utc))
        except ValueError:
            from datetime import timezone
            fe.published(datetime.now(timezone.utc))

    # Ecrire le fichier RSS
    fg.rss_str(pretty=True)
    fg.rss_file(str(RSS_FILE))
    log.info(f"Flux RSS genere: {RSS_FILE} ({len(audio_files)} episodes)")
    return str(RSS_FILE)


def upload_to_spotify_for_creators(audio_path: str, title: str, description: str) -> bool:
    """Upload un episode sur Spotify for Creators (anciennement Anchor).

    Note: Spotify for Creators n'a pas d'API publique pour l'upload automatique.
    Il faut uploader manuellement ou utiliser un service tiers (Ausha, Podbean, etc.)
    """
    log.warning("Spotify for Creators: pas d'API publique pour l'upload automatique")
    log.info(f"  Audio: {audio_path}")
    log.info(f"  Titre: {title}")
    log.info(f"  Description: {description[:80]}")
    log.info("  -> Uploader manuellement sur creators.spotify.com")
    return False


def run_all(date_str: str = None):
    """Execute tout le pipeline podcast."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    log.info("=== PODCAST PIPELINE ===")

    # 1. Extraire l'audio
    audio_files = extract_audio(date_str)
    log.info(f"Audio extraits: {len(audio_files)}")

    # 2. Generer le RSS
    rss_path = generate_rss(date_str)
    log.info(f"RSS genere: {rss_path}")

    # 3. Instructions pour la distribution
    log.info("")
    log.info("=== DISTRIBUTION ===")
    log.info("1. Hoster les fichiers MP3 sur un serveur public (GitHub, Google Drive, etc.)")
    log.info("2. Mettre a jour audio_base_url dans generate_rss()")
    log.info("3. Soumettre le RSS a:")
    log.info("   - Spotify for Creators: creators.spotify.com")
    log.info("   - Apple Podcasts: podcasts.apple.com/submit")
    log.info("   - Google Podcasts: podcasters.google.com")
    log.info("   - Amazon Music: podcasters.amazon.com")
    log.info("4. Ou utiliser Ausha (ausha.co) pour la distribution automatique sur 20+ plateformes")

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
            print(f"  {f['lang']}: {f['path']}")
    elif args.rss:
        path = generate_rss()
        print(f"RSS: {path}")
    elif args.all:
        run_all()
    else:
        print("Usage: python podcast.py --extract DATE | --rss | --all")