#!/usr/bin/env python3
"""
montage.py — Assemblage video final avec FFmpeg (via imageio_ffmpeg)
Combine: images (changement toutes les ~5s) + presets video + audio par bloc -> MP4 1080x1920
"""
import logging
import subprocess
import json
import shutil
import re
import tempfile
import math
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger("montage")

import imageio_ffmpeg
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

log.debug("FFmpeg: %s", FFMPEG_EXE)


def _run_ffmpeg(cmd: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
    if cmd and cmd[0] in ("ffmpeg", "ffprobe"):
        cmd[0] = FFMPEG_EXE
    log.debug("FFmpeg: %s", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=cwd)
    if result.returncode != 0:
        log.error("FFmpeg failed: %s", result.stderr[-500:] if result.stderr else "no stderr")
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:] if result.stderr else 'no stderr'}")
    return result


def _audio_duration(audio_path: Path) -> float:
    result = _run_ffmpeg(["ffmpeg", "-i", str(audio_path), "-f", "null", "-"])
    m = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", result.stderr)
    if m:
        h, mm, s = m.groups()
        return int(h) * 3600 + int(mm) * 60 + float(s)
    size_kb = audio_path.stat().st_size / 1024
    return max(5, size_kb / 16)


def _reencode_preset(src: Path, out: Path) -> None:
    cmd = [
        FFMPEG_EXE, "-y", "-i", str(src),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-pix_fmt", "yuv420p",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=120)


def _make_clip(img_path: Path, dur: float, out_path: Path) -> None:
    cmd = [
        FFMPEG_EXE, "-y",
        "-loop", "1", "-t", str(dur),
        "-i", str(img_path),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-r", "30", "-pix_fmt", "yuv420p",
        "-an",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=120)


def _mux(video: Path, audio: Path, out: Path) -> None:
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", str(video), "-i", str(audio),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=120)


def _bloc_from_filename(name: str) -> str:
    stem = Path(name).stem.lower()
    all_blocs = ("accroche", "fait", "pourquoi", "impact", "conclusion",
                 "introduction", "contexte", "analyse", "opinion", "ia_analysis", "perspectives")
    for bloc in all_blocs:
        if bloc in stem:
            return bloc
    return "fait"


def assemble_all_langs(
    slides_base: Path,
    audio_base: Path,
    output_base: Path,
    date_str: str,
    langs: List[str] = None,
    mode: str = "short",
) -> Dict[str, Path]:
    """Assemble les versions linguistiques avec images + presets + audio par bloc."""
    from pipeline.presets import find_preset, organiser_presets

    if langs is None:
        langs = ["fr", "en", "es"]

    organiser_presets()

    out_dir = output_base / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for lang in langs:
        # Un seul temp dir par langue
        tmpdir = tempfile.mkdtemp()
        tmp = Path(tmpdir)

        # Trouver les images, groupees par bloc (tri numerique)
        def _sort_key(p):
            m = re.search(r"img_(\d+)_", p.name)
            return int(m.group(1)) if m else 9999

        images = sorted(slides_base.glob("img_*.*"), key=_sort_key)
        if not images:
            images = sorted(slides_base.glob("slide*.png"))
        if len(images) < 1:
            log.warning(f"Pas d'images pour {lang} dans {slides_base}")
            shutil.rmtree(tmpdir, ignore_errors=True)
            continue

        blocs_images = {}
        bloc_order = []
        for img in images:
            bloc = _bloc_from_filename(img.name)
            if bloc not in blocs_images:
                blocs_images[bloc] = []
                bloc_order.append(bloc)
            blocs_images[bloc].append(img)

        all_segs = []
        for bloc in bloc_order:
            imgs = blocs_images[bloc]

            audio_file = audio_base / f"{bloc}_{lang}.mp3"
            if not audio_file.exists():
                log.warning(f"Audio manquant pour {bloc}/{lang}: {audio_file}")
                continue

            adur = _audio_duration(audio_file)
            n = len(imgs)
            dur_par_img = adur / n

            # Preset avant ce bloc
            pp = find_preset(bloc, lang)
            if pp:
                pp_out = tmp / f"preset_{bloc}.mp4"
                try:
                    _reencode_preset(pp, pp_out)
                    all_segs.append(pp_out)
                    log.info(f"Preset {bloc} OK: {pp.name}")
                except Exception as e:
                    log.warning(f"Echec reencodage preset {bloc}: {e}")

            # Clips muets pour chaque image
            bloc_clips = []
            for j, img in enumerate(imgs):
                clip_vid = tmp / f"clip_{bloc}_{j}_vid.mp4"
                try:
                    _make_clip(img, dur_par_img, clip_vid)
                    bloc_clips.append(clip_vid)
                    log.info(f"clip {bloc}/{j} OK ({round(dur_par_img, 2)}s)")
                except Exception as e:
                    log.error(f"Echec clip {bloc}/{j}: {e}")

            if not bloc_clips:
                continue

            # Concatener les clips du bloc
            bloc_vid = tmp / f"bloc_{bloc}.mp4"
            list_file = tmp / f"concat_{bloc}.txt"
            list_file.write_text("".join(f"file '{c}'\n" for c in bloc_clips), encoding="utf-8")
            cmd = [
                FFMPEG_EXE, "-y",
                "-f", "concat", "-safe", "0", "-i", str(list_file),
                "-c", "copy",
                "-movflags", "+faststart",
                str(bloc_vid),
            ]
            try:
                _run_ffmpeg(cmd, cwd=None)
            except Exception as e:
                log.error(f"Echec concat bloc {bloc}: {e}")
                continue

            # Muxer le bloc video avec l'audio complet
            seg = tmp / f"seg_{bloc}.mp4"
            try:
                _mux(bloc_vid, audio_file, seg)
                all_segs.append(seg)
                log.info(f"seg {bloc} OK ({round(adur, 2)}s + audio)")
            except Exception as e:
                log.error(f"Echec mux {bloc}: {e}")
                continue

        # Preset subscribe a la fin
        ps = find_preset("subscribe", lang)
        if ps:
            ps_out = tmp / "preset_subscribe.mp4"
            try:
                _reencode_preset(ps, ps_out)
                all_segs.append(ps_out)
                log.info(f"Preset subscribe OK: {ps.name}")
            except Exception as e:
                log.warning(f"Echec reencodage preset subscribe: {e}")

        if not all_segs:
            log.warning(f"Aucun segment pour {lang}")
            shutil.rmtree(tmpdir, ignore_errors=True)
            continue

        # Concat final
        list_file = tmp / "concat_final.txt"
        list_file.write_text("".join(f"file '{s}'\n" for s in all_segs), encoding="utf-8")
        out_tmp = tmp / "out.mp4"
        cmd = [
            FFMPEG_EXE, "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy",
            "-movflags", "+faststart",
            str(out_tmp),
        ]
        try:
            _run_ffmpeg(cmd, cwd=None)
        except Exception as e:
            log.error(f"Echec concat {lang}: {e}")
            shutil.rmtree(tmpdir, ignore_errors=True)
            continue

        date_for_filename = "-".join(reversed(date_str.split("-")))
        suffix = "long" if mode == "long" else "short"
        output_file = out_dir / f"{date_for_filename}_{suffix}_{lang}.mp4"
        shutil.move(str(out_tmp), str(output_file))
        results[lang] = output_file
        log.info(f"✓ {output_file.name} cree")

        # Cleanup temp dir
        shutil.rmtree(tmpdir, ignore_errors=True)

    return results


def assemble_short(lang, slide_files, audio_path, srt_path=None, output_path=None, slide_duration=None):
    """Compatibilite arriere."""
    import tempfile
    images = list(slide_files) if slide_files else []
    if not images:
        raise FileNotFoundError("Aucune image fournie")
    adur = _audio_duration(audio_path)
    dur = slide_duration if slide_duration else adur / len(images)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        audio_dst = tmp / "audio.mp3"
        shutil.copy(audio_path, audio_dst)
        slide_videos = []
        for i, slide in enumerate(images):
            sv = tmp / f"slide_vid_{i}.mp4"
            cmd = [
                FFMPEG_EXE, "-y",
                "-loop", "1", "-t", str(dur),
                "-i", str(slide),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-vf", "fps=30",
                str(sv),
            ]
            _run_ffmpeg(cmd)
            slide_videos.append(sv)
        list_file = tmp / "concat_list.txt"
        list_file.write_text("".join(f"file '{v.name}'\n" for v in slide_videos), encoding="utf-8")
        out_tmp = tmp / "out.mp4"
        cmd = [
            FFMPEG_EXE, "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-i", str(audio_dst),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", "-pix_fmt", "yuv420p",
            str(out_tmp),
        ]
        _run_ffmpeg(cmd, cwd=tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out_tmp), str(output_path))
        return output_path


def generer_montage(date_str=None, slides_base=None, audio_base=None, output_base=None, langs=None, script=None, mode: str = "short"):
    from datetime import datetime
    from config import OUTPUT_DIR
    from pipeline.presets import organiser_presets

    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    if slides_base is None:
        slides_base = Path(OUTPUT_DIR) / "visuels" / date_str
    if audio_base is None:
        audio_base = Path(OUTPUT_DIR) / "audio" / date_str
    if output_base is None:
        output_base = Path(OUTPUT_DIR) / "videos"

    if not slides_base.exists():
        raise FileNotFoundError(f"Slides dir not found: {slides_base}")
    if not audio_base.exists():
        raise FileNotFoundError(f"Audio dir not found: {audio_base}")

    organiser_presets()

    return assemble_all_langs(slides_base, audio_base, output_base, date_str, langs, mode=mode)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        results = generer_montage()
        print(json.dumps({k: str(v) for k, v in results.items()}, indent=2))
    except Exception as e:
        log.error(f"Test montage failed: {e}")