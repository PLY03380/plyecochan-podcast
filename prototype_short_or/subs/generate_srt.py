#!/usr/bin/env python3
"""
generate_srt.py — Génère fichier SRT depuis script markdown + audio (pour timing)
Usage: python generate_srt.py --script script_FR.md --audio audio/narration_fr.mp3 --output subs/subs_fr.srt
"""

import argparse
import re
import subprocess
import json
from pathlib import Path

# ─── Helpers ────────────────────────────────────────────────────
def get_audio_duration(audio_path: Path) -> float:
    """Retourne durée audio en secondes via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def parse_script(script_path: Path) -> list:
    """Extrait segments narratifs du script markdown."""
    content = script_path.read_text(encoding="utf-8")

    # Cherche la section "Script complet (version narration)"
    match = re.search(r"## Script complet.*?\n(.*?)(?:\n## |\Z)", content, re.DOTALL)
    if not match:
        # Fallback: tout le contenu après le tableau
        match = re.search(r"\| Étape \| Contenu.*?\n(.*?)(?:\n## |\Z)", content, re.DOTALL)

    if not match:
        raise ValueError("Impossible de trouver le script narratif dans le markdown")

    narration = match.group(1).strip()

    # Split par segments > **[Label — time]**
    segments = re.split(r">\s*\*\*([^—]+)—([^]]+)\*\*\s*\n", narration)

    # Format: [sep, label, time, text, label, time, text, ...]
    parsed = []
    if len(segments) > 1:
        for i in range(1, len(segments), 3):
            label = segments[i].strip()
            time_range = segments[i+1].strip()
            text = segments[i+2].strip() if i+2 < len(segments) else ""
            # Nettoyer time_range "0:00-0:03" -> (0, 3)
            m = re.match(r"(\d+):(\d+)-(\d+):(\d+)", time_range)
            if m:
                start = int(m.group(1))*60 + int(m.group(2))
                end = int(m.group(3))*60 + int(m.group(4))
            else:
                start, end = 0, 0
            parsed.append({"label": label, "start": start, "end": end, "text": text})

    return parsed

def estimate_timing(segments: list, total_duration: float) -> list:
    """Ajuste les timings basés sur la durée audio réelle."""
    # Si les timings du script sont cohérents, les utiliser
    script_total = sum(s["end"] - s["start"] for s in segments if s["end"] > s["start"])
    if script_total > 0 and abs(script_total - total_duration) < 10:
        return segments

    # Sinon, répartir proportionnellement au nombre de mots
    total_words = sum(len(s["text"].split()) for s in segments)
    current = 0.0
    for s in segments:
        words = len(s["text"].split())
        dur = (words / total_words) * total_duration if total_words > 0 else total_duration / len(segments)
        s["start"] = current
        s["end"] = current + dur
        current += dur
    return segments

def format_srt_time(seconds: float) -> str:
    """Convertit secondes -> format SRT HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

def write_srt(segments: list, output_path: Path):
    """Écrit fichier SRT."""
    lines = []
    for i, s in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{format_srt_time(s['start'])} --> {format_srt_time(s['end'])}")
        lines.append(s["text"])
        lines.append("")  # ligne vide
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ SRT written: {output_path} ({len(segments)} segments)")

# ─── Main ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate SRT from script + audio")
    parser.add_argument("--script", required=True, type=Path, help="Script markdown file")
    parser.add_argument("--audio", required=True, type=Path, help="Audio narration file")
    parser.add_argument("--output", required=True, type=Path, help="Output SRT file")
    args = parser.parse_args()

    # Durée audio
    duration = get_audio_duration(args.audio)
    print(f"🎵 Audio duration: {duration:.1f}s")

    # Parse script
    segments = parse_script(args.script)
    print(f"📝 Parsed {len(segments)} segments from script")

    # Ajuster timings
    segments = estimate_timing(segments, duration)

    # Écrire SRT
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_srt(segments, args.output)

if __name__ == "__main__":
    main()