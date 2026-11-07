"""Prototype : video Short avec images de la bibliotheque (durees variables par bloc)."""
import json, subprocess, tempfile, shutil
from pathlib import Path
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "images" / "manifest.json"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Script FR (blocs)
script_fr = {
    "accroche": "L'or vient de pulvériser tous les records !",
    "fait": "Ce 19 octobre 2026, l'or franchit 2 710 dollars l'once — un seuil jamais atteint.",
    "pourquoi": "Baisse des taux Fed plus achats massifs banques centrales. L'or redevient valeur refuge numéro 1.",
    "impact": "Pour vous : protection contre l'inflation. Pour l'économie : les matières premières restent tendues.",
    "conclusion": "L'or tiendra-t-il ce niveau ? Réponse en commentaire. Abonnez-vous !",
}

# Durees cibles par bloc (secondes)
DUREES = {"accroche": 5, "fait": 8, "pourquoi": 12, "impact": 15, "conclusion": 8}

# Candidats d'images par bloc (concept ids du manifest)
CANDIDATS = {
    "accroche": ["emo_surprise_shock", "emo_surprise_never", "t1_record", "t1_firsttime"],
    "fait": ["t2_cpi", "t2_inflationreport", "t2_jobsreport", "t2_nfp"],
    "pourquoi": ["t1_ratecut", "t1_ratehike", "t2_fed", "t2_bce", "t1_opec", "t2_opec"],
    "impact": ["t3_employment", "t3_wagegrowth", "t2_unemployment", "t2_jobs"],
    "conclusion": ["t2_dxy", "t3_employment", "t1_alltimelow", "t1_record"],
}

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["concepts"]

def pick_image(concept_id):
    info = manifest.get(concept_id)
    if not info:
        return None
    p = ROOT / info["path"]
    if not p.exists():
        return None
    if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
        return None
    return p

def selectionner_images():
    chosen = []
    used = set()
    for bloc, duree in DUREES.items():
        img_path = None
        for cid in CANDIDATS.get(bloc, []):
            p = pick_image(cid)
            if p and p not in used:
                img_path = p
                break
        if img_path is None:
            # fallback : premier jpg non utilisé
            for cid, info in manifest.items():
                p = ROOT / info["path"]
                if p.exists() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and p not in used:
                    img_path = p
                    break
        assert img_path is not None, f"Aucune image pour {bloc}"
        used.add(img_path)
        chosen.append((bloc, img_path, duree))
        print(f"{bloc}: {img_path.name} ({duree}s)")
    return chosen

def make_clip(img_path, dur, out_path):
    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-t", str(dur),
        "-i", str(img_path),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

def main():
    chosen = selectionner_images()

    # Generer audio via Piper
    from pipeline.voix import _synthesize_piper
    audio_path = ROOT / "output" / "audio" / "proto" / "narration_fr.mp3"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    texte = " ".join(script_fr[b] for b in ["accroche", "fait", "pourquoi", "impact", "conclusion"])
    _synthesize_piper(texte, "fr", audio_path)
    print("Audio:", audio_path, audio_path.stat().st_size)

    # Calculer les durees proportionnellement a la longueur de chaque bloc
    import re
    def audio_dur(p):
        r = subprocess.run([FFMPEG, "-i", str(p), "-f", "null", "-"], capture_output=True, text=True)
        m = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", r.stderr)
        if m:
            h, mm, s = m.groups()
            return int(h)*3600 + int(mm)*60 + float(s)
        return 30.0
    adur = audio_dur(audio_path)
    # proportion par longueur de texte (min 3s)
    blocs = list(script_fr.keys())
    lens = [max(1, len(script_fr[b])) for b in blocs]
    tot = sum(lens)
    durees_calc = [max(3.0, adur * (l / tot)) for l in lens]
    # ajuster la derniere pour matcher exactement
    durees_calc[-1] = adur - sum(durees_calc[:-1])
    # reconstruire chosen avec nouvelles durees
    new_chosen = []
    for (bloc, img, _), d in zip(chosen, durees_calc):
        new_chosen.append((bloc, img, round(d, 2)))
    chosen = new_chosen
    print("Durees:", [(b, d) for b, _, d in chosen], "total", round(sum(d for _, _, d in chosen),2), "audio", round(adur,2))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        clips = []
        for i, (bloc, img, dur) in enumerate(chosen):
            clip = tmp / f"clip_{i}.mp4"
            make_clip(img, dur, clip)
            clips.append(clip)
            print(f"clip {i} OK ({dur}s)")
        # concat list
        list_file = tmp / "concat.txt"
        list_file.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
        out_tmp = tmp / "out.mp4"
        cmd = [
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-i", str(audio_path),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", "-pix_fmt", "yuv420p",
            str(out_tmp),
        ]
        subprocess.run(cmd, cwd=tmp, capture_output=True, check=True)
        out_final = ROOT / "output" / "videos" / "proto" / "proto_images_fr.mp4"
        out_final.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out_tmp), str(out_final))
        print("VIDEO FINALE:", out_final, out_final.stat().st_size)

if __name__ == "__main__":
    main()
