#!/usr/bin/env python3
"""
voix.py — Génération narration TTS multilingue (FR/EN/ES) via Piper + fallback gTTS/pyttsx3
Un fichier MP3 distinct par bloc narratif.
"""
import asyncio
import logging
import json
import tempfile
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import edge_tts

log = logging.getLogger("voix")

# ─── Configuration voix ──────────────────────────────────────────
TTS_VOICES = {
    "fr": "fr-FR-DeniseNeural",
    "en": "en-US-AriaNeural",
    "es": "es-ES-ElviraNeural",
}

GTTS_LANGS = {"fr": "fr", "en": "en", "es": "es"}

TTS_RATE = "+0%"
TTS_VOLUME = "+0%"

PYTTSX3_VOICES = {"fr": "french", "en": "english", "es": "spanish"}

HTTP_PROXY = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
HTTPS_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")

# Ordre des blocs par langue (Shorts)
ORDRE_BLOCS = {
    "fr": ["accroche", "fait", "pourquoi", "impact", "conclusion"],
    "en": ["hook", "fact", "why", "impact", "conclusion"],
    "es": ["gancho", "hecho", "por_que", "impacto", "conclusion"],
}

# Ordre des blocs par langue (videos longues)
ORDRE_BLOCS_LONG = {
    "fr": ["introduction", "contexte", "fait", "analyse", "pourquoi", "impact", "opinion", "ia_analysis", "perspectives", "conclusion"],
    "en": ["introduction", "context", "fact", "analysis", "why", "impact", "opinion", "ai_analysis", "perspectives", "conclusion"],
    "es": ["introduction", "contexto", "hecho", "analisis", "por_que", "impacto", "opinion", "ia_analysis", "perspectivas", "conclusion"],
}

# Mapping bloc language-specific -> nom canonique (francais, utilise pour les fichiers)
BLOC_CANONIQUE = {
    "fr": {"accroche": "accroche", "fait": "fait", "pourquoi": "pourquoi", "impact": "impact", "conclusion": "conclusion",
           "introduction": "introduction", "contexte": "contexte", "analyse": "analyse", "opinion": "opinion",
           "ia_analysis": "ia_analysis", "perspectives": "perspectives"},
    "en": {"hook": "accroche", "fact": "fait", "why": "pourquoi", "impact": "impact", "conclusion": "conclusion",
           "introduction": "introduction", "context": "contexte", "analysis": "analyse", "opinion": "opinion",
           "ai_analysis": "ia_analysis", "perspectives": "perspectives"},
    "es": {"gancho": "accroche", "hecho": "fait", "por_que": "pourquoi", "impacto": "impact", "conclusion": "conclusion",
           "introduction": "introduction", "contexto": "contexte", "analisis": "analyse", "opinion": "opinion",
           "ia_analysis": "ia_analysis", "perspectivas": "perspectives"},
}


# ─── Synthese TTS ────────────────────────────────────────────────
def _synthesize_piper(text: str, lang: str, output_path: Path) -> None:
    """Piper TTS offline (piper-tts 1.8+)."""
    from piper import PiperVoice
    import wave
    import subprocess
    from pathlib import Path as P

    PIPER_MODELS = {"fr": "fr_FR-siwis-medium", "en": "en_US-lessac-medium", "es": "es_ES-sharvard-medium"}
    model_name = PIPER_MODELS.get(lang, "fr_FR-siwis-medium")

    project_root = P(__file__).resolve().parent.parent
    candidate_dirs = [
        project_root / ".venv" / "voices",
        project_root / "voices",
        P.home() / ".cache" / "piper" / "voices",
    ]
    model_path = None
    for d in candidate_dirs:
        cand = d / f"{model_name}.onnx"
        if cand.exists() and cand.stat().st_size > 1000:
            model_path = cand
            break
    if model_path is None:
        raise FileNotFoundError(f"Modele Piper non trouve pour {model_name}")

    voice = PiperVoice.load(str(model_path))

    wav_path = output_path.with_suffix(".wav")
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(voice.config.sample_rate)
        for chunk in voice.synthesize(text):
            wav_file.writeframes(chunk.audio_int16_bytes)

    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ffmpeg, "-y", "-i", str(wav_path), "-ar", "48000", "-ac", "2", str(output_path)],
                      capture_output=True, timeout=120, check=True)
        wav_path.unlink(missing_ok=True)
    except Exception as e:
        log.warning(f"Conversion MP3 echouee, conservation WAV: {e}")
        wav_path.replace(output_path.with_suffix(".wav"))

    log.info(f"Piper OK: {output_path.name}")


def _synthesize_gtts(text: str, lang: str, output_path: Path) -> None:
    """Fallback gTTS."""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=GTTS_LANGS.get(lang, "fr"), slow=False, timeout=30)
        tts.save(str(output_path))
        # Normaliser le sample rate et les canaux
        import subprocess, imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        tmp = output_path.with_suffix(".tmp.mp3")
        subprocess.run([ffmpeg, "-y", "-i", str(output_path), "-ar", "48000", "-ac", "2", str(tmp)],
                      capture_output=True, timeout=60, check=True)
        tmp.replace(output_path)
        log.info(f"gTTS OK: {output_path.name}")
    except Exception as e:
        log.error(f"gTTS failed: {e}")
        raise


def _synthesize_pyttsx3(text: str, lang: str, output_path: Path) -> None:
    """Fallback pyttsx3."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        target_lang = PYTTSX3_VOICES.get(lang, "english")
        for voice in voices:
            if target_lang.lower() in voice.name.lower() or target_lang.lower() in voice.id.lower():
                engine.setProperty('voice', voice.id)
                break
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 1.0)
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
        log.info(f"pyttsx3 OK: {output_path.name}")
    except Exception as e:
        log.error(f"pyttsx3 failed: {e}")
        raise


def _synthesize_one(text: str, lang: str, output_path: Path) -> None:
    """Synthese TTS pour un bloc : Piper -> gTTS -> pyttsx3."""
    try:
        _synthesize_piper(text, lang, output_path)
    except Exception as e:
        log.warning(f"Piper failed for {lang}: {e} — fallback gTTS")
        try:
            _synthesize_gtts(text, lang, output_path)
        except Exception as e2:
            log.warning(f"gTTS failed for {lang}: {e2} — fallback pyttsx3")
            try:
                _synthesize_pyttsx3(text, lang, output_path)
            except Exception as e3:
                log.error(f"All TTS failed for {lang}: {e3}")
                raise


# ─── Generation par langue ───────────────────────────────────────
async def generer_voix_langue(script: Dict, output_dir: Path, lang: str, mode: str = "short") -> Dict[str, Path]:
    """Genere un MP3 par bloc pour une langue. Retourne {bloc_canonique: audio_path}."""
    blocs = script.get(lang, {}).get("blocs", {})
    if mode == "long":
        ordre = ORDRE_BLOCS_LONG.get(lang, [])
    else:
        ordre = ORDRE_BLOCS.get(lang, [])
    canonique = BLOC_CANONIQUE.get(lang, {})
    result = {}

    output_dir.mkdir(parents=True, exist_ok=True)

    for bloc_key in ordre:
        text = blocs.get(bloc_key, "").strip()
        if not text:
            continue
        canon = canonique.get(bloc_key, bloc_key)
        audio_path = output_dir / f"{canon}_{lang}.mp3"
        try:
            _synthesize_one(text, lang, audio_path)
            result[canon] = audio_path
            log.info(f"✓ {lang}/{canon}: {audio_path.name}")
        except Exception as e:
            log.error(f"Erreur TTS {lang}/{canon}: {e}")

    return result


async def generer_toutes_langues(script: Dict, output_dir: Path, mode: str = "short") -> Dict[str, Dict[str, Path]]:
    """Genere les MP3 par bloc pour FR, EN, ES."""
    results = {}
    for lang in ("fr", "en", "es"):
        try:
            result = await generer_voix_langue(script, output_dir, lang, mode=mode)
            results[lang] = result
        except Exception as e:
            log.error(f"Erreur TTS {lang}: {e}")
            results[lang] = {}
    return results


# ─── Point d'entree synchrone ────────────────────────────────────
def generer_voix(script: Dict, out_base: Path = None, mode: str = "short") -> Dict:
    """Fonction wrapper synchrone. Retourne {lang: {bloc: audio_path}}."""
    if out_base is None:
        from config import OUTPUT_DIR
        out_base = Path(OUTPUT_DIR) / "audio"

    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    out_dir = out_base / today
    out_dir.mkdir(parents=True, exist_ok=True)

    # Nettoyer les anciens fichiers audio du jour (une seule fois)
    for old in out_dir.glob("*.mp3"):
        try:
            old.unlink()
        except Exception:
            pass

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    results = loop.run_until_complete(generer_toutes_langues(script, out_dir, mode=mode))

    return {
        lang: {bloc: str(path) for bloc, path in blocs.items()}
        for lang, blocs in results.items()
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    test_script = {
        "fr": {"blocs": {"accroche": "L'or vient de pulvériser tous les records !",
                         "fait": "Ce 12 octobre 2026, l'or franchit 2 710 dollars l'once.",
                         "pourquoi": "Baisse des taux Fed plus achats massifs banques centrales.",
                         "impact": "Pour vous : protection contre l'inflation.",
                         "conclusion": "L'or tiendra-t-il ce niveau ? Abonnez-vous !"}},
        "en": {"blocs": {"hook": "Gold just shattered every record!",
                         "fact": "October 12, 2026, gold hit 2,710 dollars per ounce.",
                         "why": "Fed rate cuts plus massive central bank buying.",
                         "impact": "For you: inflation hedge.",
                         "conclusion": "Will gold hold this level? Subscribe!"}},
        "es": {"blocs": {"gancho": "¡El oro acaba de pulverizar todos los récords!",
                         "hecho": "El 12 de octubre de 2026, el oro supera 2.710 dólares la onza.",
                         "por_que": "Bajada de tipos Fed más compras masivas bancos centrales.",
                         "impacto": "Para ti: cobertura contra inflación.",
                         "conclusion": "¿Mantendrá el oro este nivel? ¡Suscríbete!"}},
    }

    result = generer_voix(test_script)
    print(json.dumps(result, indent=2, ensure_ascii=False))