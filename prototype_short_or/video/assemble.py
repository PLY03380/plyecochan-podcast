#!/usr/bin/env python3
"""
assemble.py — Monte la vidéo finale (MoviePy)
Usage: python assemble.py --lang FR --audio audio/narration_fr.mp3 --subs subs/subs_fr.srt --charts charts/output --output video/short_fr.mp4
"""

import argparse
from pathlib import Path
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, TextClip, CompositeVideoClip,
    ColorClip, concatenate_videoclips, SubtitlesClip
)
import pysrt

# ─── Configuration ──────────────────────────────────────────────
CHART_MAP = {
    "hook": "logo_animation.png",           # 0-3s
    "fact": "price_timeline.png",           # 3-11s
    "numbers_1": "annual_perf.png",         # 11-17s
    "numbers_2": "cb_purchases.png",        # 17-23s
    "drivers_1": "icon_cb.png",             # 23-29s
    "drivers_2": "icon_fed.png",            # 29-35s
    "drivers_3": "icon_geo.png",            # 35-41s
    "conclusion": "end_screen.png",         # 41-45s
}

TIMINGS = {
    "hook": (0, 3),
    "fact": (3, 11),
    "numbers_1": (11, 17),
    "numbers_2": (17, 23),
    "drivers_1": (23, 29),
    "drivers_2": (29, 35),
    "drivers_3": (35, 41),
    "conclusion": (41, 45),
}

W, H = 1080, 1920  # Vertical 9:16
FPS = 30

STYLE = {
    "bg": "#0B1D3A",
    "gold": "#FFD700",
    "white": "#FFFFFF",
    "font": "DejaVu-Sans-Bold",
    "font_size": 48,
}

# ─── Helpers ────────────────────────────────────────────────────
def load_chart(charts_dir: Path, name: str) -> ImageClip:
    """Charge un graphique, resize pour remplir l'écran (avec padding)."""
    path = charts_dir / name
    if not path.exists():
        # Placeholder coloré si manquant
        print(f"⚠️ Missing: {path}, using placeholder")
        return ColorClip((W, H), color=STYLE["bg"], duration=1)
    clip = ImageClip(str(path))
    # Resize en gardant ratio, centrer sur fond
    clip = clip.resize(height=H * 0.85).set_position(("center", "center"))
    return clip

def create_bg(duration: float) -> ColorClip:
    return ColorClip((W, H), color=STYLE["bg"], duration=duration)

def create_text_overlay(text: str, duration: float, position=("center", 0.85), fontsize=42) -> TextClip:
    """Crée un texte overlay (lower third style)."""
    txt = TextClip(
        text, fontsize=fontsize, color=STYLE["white"], font=STYLE["font"],
        stroke_color="black", stroke_width=2,
        size=(W * 0.9, None), method="caption", align="center"
    )
    return txt.set_duration(duration).set_position(position, relative=True)

def generator(subtitle_text):
    """Générateur pour SubtitlesClip."""
    return TextClip(
        subtitle_text, fontsize=40, color=STYLE["white"], font=STYLE["font"],
        stroke_color="black", stroke_width=2,
        size=(W * 0.9, None), method="caption", align="center"
    )

# ─── Main ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Assemble Short video with MoviePy")
    parser.add_argument("--lang", choices=["FR", "EN", "ES"], required=True)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--subs", required=True, type=Path)
    parser.add_argument("--charts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    print(f"🎬 Assembling {args.lang} version...")

    # Audio
    audio = AudioFileClip(str(args.audio))
    duration = audio.duration
    print(f"🎵 Audio: {duration:.1f}s")

    # Background
    bg = create_bg(duration)

    # Charts sequence
    clips = [bg]
    for key, (start, end) in TIMINGS.items():
        chart_name = CHART_MAP.get(key, "placeholder.png")
        chart_clip = load_chart(args.charts, chart_name)
        chart_clip = chart_clip.set_start(start).set_duration(end - start)
        clips.append(chart_clip)

    # Sous-titres
    subs = pysrt.open(args.subs, encoding="utf-8")
    sub_clips = []
    for sub in subs:
        start = sub.start.ordinal / 1000
        end = sub.end.ordinal / 1000
        txt = TextClip(
            sub.text, fontsize=42, color=STYLE["white"], font=STYLE["font"],
            stroke_color="black", stroke_width=2,
            size=(W * 0.9, None), method="caption", align="center"
        ).set_start(start).set_duration(end - start).set_position(("center", 0.82), relative=True)
        sub_clips.append(txt)

    clips.extend(sub_clips)

    # Composite final
    final = CompositeVideoClip(clips, size=(W, H)).set_audio(audio).set_duration(duration)

    # Export
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"📦 Exporting to {args.output}...")
    final.write_videofile(
        str(args.output),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="8000k",
        threads=4,
        preset="medium",
        ffmpeg_params=["-movflags", "+faststart"]
    )
    print(f"✅ Done: {args.output}")

if __name__ == "__main__":
    main()