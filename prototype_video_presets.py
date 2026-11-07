"""Prototype : video Short avec presets auto-detectes + images + narration decoupee."""
import json, subprocess, tempfile, shutil, re
from pathlib import Path
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "images" / "manifest.json"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

from pipeline.presets import find_preset, PRESET_DIRS, LANG_CODES

script_fr = {
    "accroche": "L'or vient de pulvériser tous les records !",
    "fait": "Ce 19 octobre 2026, l'or franchit 2 710 dollars l'once — un seuil jamais atteint.",
    "pourquoi": "Baisse des taux Fed plus achats massifs banques centrales. L'or redevient valeur refuge numéro 1.",
    "impact": "Pour vous : protection contre l'inflation. Pour l'économie : les matières premières restent tendues.",
    "conclusion": "L'or tiendra-t-il ce niveau ? Réponse en commentaire. Abonnez-vous !",
}

CANDIDATS = {
    "accroche": ["t1_record", "t1_firsttime"],
    "fait": ["t2_cpi", "t2_inflationreport", "t2_jobsreport"],
    "pourquoi": ["t1_ratecut", "t1_ratehike", "t2_fed", "t2_bce"],
    "impact": ["t3_employment", "t3_wagegrowth", "t2_unemployment"],
    "conclusion": ["t2_dxy", "t1_alltimelow", "t1_record"],
}

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["concepts"]

def pick_image(cid, used):
    info = manifest.get(cid)
    if not info:
        return None
    p = ROOT / info["path"]
    if not p.exists() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp") or p in used:
        return None
    return p

def selectionner_images():
    chosen = []
    used = set()
    for bloc in ["accroche", "fait", "pourquoi", "impact", "conclusion"]:
        img_path = None
        for cid in CANDIDATS.get(bloc, []):
            p = pick_image(cid, used)
            if p:
                img_path = p
                break
        if img_path is None:
            for cid, info in manifest.items():
                p = ROOT / info["path"]
                if p.exists() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and p not in used:
                    img_path = p
                    break
        assert img_path is not None, f"Aucune image pour {bloc}"
        used.add(img_path)
        chosen.append((bloc, img_path))
        print(f"{bloc}: {img_path.name}")
    return chosen

def audio_duration(p):
    r = subprocess.run([FFMPEG, "-i", str(p), "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", r.stderr)
    if m:
        h, mm, s = m.groups()
        return int(h)*3600 + int(mm)*60 + float(s)
    return 30.0

def reencode_preset(src, out):
    cmd = [
        FFMPEG, "-y", "-i", str(src),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-pix_fmt", "yuv420p",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

def make_clip(img_path, dur, out_path):
    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-t", str(dur),
        "-i", str(img_path),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-r", "30", "-pix_fmt", "yuv420p",
        "-an",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

def cut_audio(src, start, dur, out):
    cmd = [
        FFMPEG, "-y", "-ss", str(start), "-t", str(dur),
        "-i", str(src),
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

def mux_video_audio(video, audio, out):
    cmd = [
        FFMPEG, "-y",
        "-i", str(video), "-i", str(audio),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

def main():
    lang = "fr"
    chosen = selectionner_images()

    from pipeline.voix import _synthesize_piper
    audio_path = ROOT / "output" / "audio" / "proto_presets2" / "narration_fr.mp3"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    texte = " ".join(script_fr[b] for b in ["accroche", "fait", "pourquoi", "impact", "conclusion"])
    _synthesize_piper(texte, lang, audio_path)
    adur = audio_duration(audio_path)
    print("Audio total:", round(adur, 2))

    blocs = [b for b, _ in chosen]
    lens = [max(1, len(script_fr[b])) for b in blocs]
    tot = sum(lens)
    durees = [max(2.0, adur * (l / tot)) for l in lens]
    durees[-1] = adur - sum(durees[:-1])
    print("Durees:", [(b, round(d, 2)) for b, d in zip(blocs, durees)])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        offset = 0.0
        all_segs = []
        for i, ((bloc, img), dur) in enumerate(zip(chosen, durees)):
            # Preset avant ce bloc (si present)
            pp = find_preset(bloc, lang)
            if pp:
                pp_out = tmp / f"preset_{bloc}.mp4"
                reencode_preset(pp, pp_out)
                all_segs.append(pp_out)
                print(f"Preset {bloc} OK:", pp.name)

            # Clip image
            clip_vid = tmp / f"clip_{i}_vid.mp4"
            make_clip(img, dur, clip_vid)
            audio_chunk = tmp / f"audio_{i}.aac"
            cut_audio(audio_path, offset, dur, audio_chunk)
            seg = tmp / f"seg_{i}.mp4"
            mux_video_audio(clip_vid, audio_chunk, seg)
            all_segs.append(seg)
            offset += dur
            print(f"seg {i} ({bloc}) OK ({round(dur,2)}s)")

        # Preset subscribe a la fin (si present)
        ps = find_preset("subscribe", lang)
        if ps:
            ps_out = tmp / "preset_subscribe.mp4"
            reencode_preset(ps, ps_out)
            all_segs.append(ps_out)
            print("Preset subscribe OK:", ps.name)

        list_file = tmp / "concat.txt"
        list_file.write_text("".join(f"file '{s.name}'\n" for s in all_segs), encoding="utf-8")
        out_tmp = tmp / "out.mp4"
        cmd = [
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy",
            "-movflags", "+faststart",
            str(out_tmp),
        ]
        subprocess.run(cmd, cwd=tmp, capture_output=True, check=True)

        out_final = ROOT / "output" / "videos" / "proto" / "proto_presets2_fr.mp4"
        out_final.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out_tmp), str(out_final))
        print("VIDEO FINALE:", out_final, out_final.stat().st_size)
        print("Duree finale:", round(audio_duration(out_final), 2))

if __name__ == "__main__":
    main()
