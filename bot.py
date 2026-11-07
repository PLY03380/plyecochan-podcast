#!/usr/bin/env python3
"""bot.py — Orchestrateur : veille → script → visuels → voix → montage → upload → db."""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import config
from db import db_save, db_set_status
from themes import theme_du_jour

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("bot")

LOCK_FILE = Path("bot.lock")


def run_daily(theme: str = None) -> dict:
    """Exécute le pipeline complet pour le jour donné. Retourne un résumé."""
    # Verrou anti-execution concurrente
    if LOCK_FILE.exists():
        log.warning("Bot deja en cours (lock file present), sortie.")
        sys.exit(0)
    LOCK_FILE.touch()

    try:
        theme = theme or theme_du_jour()
        # Organiser les presets video (renommage automatique)
        try:
            from pipeline.presets import organiser_presets
            organiser_presets()
        except Exception as e:
            log.warning("organiser_presets a echoue: %s", e)
        log.info("=== DÉBUT PIPELINE — thème: %s ===", theme)

        # 1. Veille + sélection
        from pipeline.veille import fetch_all_rss
        from pipeline.selection import run_selection

        articles = fetch_all_rss(config.HOURS_BACK)
        log.info("Articles récupérés: %d", len(articles))
        if not articles:
            raise RuntimeError("Aucun article RSS récupéré.")

        selected = run_selection(articles, theme=theme)
        if not selected:
            raise RuntimeError("Aucun article sélectionné.")
        log.info("Sujet retenu: %s | score=%.1f | theme=%s",
                 selected["titre"][:60], selected.get("score_final", 0), selected.get("theme"))

        # Normaliser la date en string pour les modules aval
        if isinstance(selected.get("date"), datetime):
            selected["date"] = selected["date"].strftime("%d/%m/%Y")

        # Persister en base (statut: selectionne)
        try:
            db_save(selected, statut="selectionne")
        except Exception as e:
            log.warning("db_save a échoué: %s", e)

        # 2. Script LLM (FR/EN/ES)
        from pipeline.script import generer_script_safe
        script = generer_script_safe(selected)
        log.info("Script généré pour %d langues", len([k for k in ("fr", "en", "es") if k in script]))

        # 2b. Validation packaging (titres + thumbnails) + SEO + hooks
        from pipeline.package import ameliorer_titres, generer_seo, score_hooks_script
        script = ameliorer_titres(script)
        script = generer_seo(script)
        script = score_hooks_script(script)
        for lang in ("fr", "en", "es"):
            pkg = script.get("package", {}).get(lang, {})
            seo = script.get("seo", {}).get(lang, {})
            hook = script.get("hook_scores", {}).get(lang, {})
            if pkg:
                log.info("  %s: title=%d/100, thumb=%s, tags=%d, hook=%s",
                         lang, pkg["score"], pkg["thumbnail_text"], len(seo.get("tags", [])),
                         hook.get("verdict", "?"))

        # 3. Voix (generer l'audio AVANT les visuels pour connaitre les durees reelles)
        from pipeline.voix import generer_voix
        voice_result = generer_voix(script)
        log.info("Voix generee: %d langues", len(voice_result))

        # 4. Mesurer les durees reelles de l'audio par bloc
        from pipeline.montage import _audio_duration
        from pathlib import Path as _P
        audio_base = _P(config.OUTPUT_DIR) / "audio" / datetime.now().strftime("%Y-%m-%d")
        durees_reelles = {}
        for bloc in ("accroche", "fait", "pourquoi", "impact", "conclusion"):
            af = audio_base / f"{bloc}_fr.mp3"
            if af.exists():
                durees_reelles[bloc] = _audio_duration(af)
        log.info("Durees audio reelles: %s", {k: round(v, 1) for k, v in durees_reelles.items()})

        # 5. Visuels (images ~toutes les 5s, basees sur les durees reelles)
        from pipeline.visuels import generer_visuels
        slides = generer_visuels(selected, durees_blocs=durees_reelles)
        log.info("Images generees: %d blocs", len(slides))
        for bloc, paths in slides:
            log.info("  %s: %d images", bloc, len(paths))

        # Sauvegarder le script JSON pour sync_uploads.py
        try:
            scripts_dir = _P(config.OUTPUT_DIR) / "scripts" / date_str if False else _P(config.OUTPUT_DIR) / "scripts" / datetime.now().strftime("%Y-%m-%d")
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (scripts_dir / "script.json").write_text(
                json.dumps(script, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            log.warning("Sauvegarde script echouee: %s", e)

        # 6. Montage MP4 par langue (avec presets + audio par bloc)
        from pipeline.montage import generer_montage
        date_str = datetime.now().strftime("%Y-%m-%d")
        videos = generer_montage(date_str=date_str)
        log.info("Videos: %s", {k: str(v) for k, v in videos.items()})

        # Marquer comme produit
        try:
            db_set_status(selected["titre"], "produit")
        except Exception as e:
            log.warning("db_set_status a echoue: %s", e)

        summary = {
            "date": date_str,
            "theme": selected.get("theme", theme),
            "sujet": selected["titre"],
            "score": selected.get("score_final"),
            "slides": [str(p) for _, paths in slides for p in paths],
            "audio": voice_result,
            "videos": {k: str(v) for k, v in videos.items()},
        }

        # 7. Upload YouTube (optionnel — necessite config/client_secrets.json)
        from pathlib import Path
        secrets = Path("config") / "client_secrets.json"
        if secrets.exists():
            from pipeline.upload import upload_all
            try:
                video_ids = upload_all(videos, script)
                log.info("Uploads: %s", video_ids)
                summary["video_ids"] = video_ids
            except Exception as e:
                log.warning("Upload echoue: %s", e)
        else:
            log.info("Upload ignore (pas de client_secrets.json)")

        # 8. Verification upload (upload les videos manquantes)
        try:
            from sync_uploads import sync
            sync()
        except Exception as e:
            log.warning("sync_uploads a echoue: %s", e)

        # 9. Verification upload (upload les videos manquantes) — deja fait a l'etape 8

        # 10. Publication Blogger + Facebook + Indexation (a la fin, apres tous les uploads)
        #     Utilise publish_pending.py qui verifie ce qui manque et complete
        try:
            from publish_pending import publish_pending
            publish_pending(date_str=datetime.now().strftime("%Y-%m-%d"))
            log.info("Publication Blogger/Facebook/Indexation terminée")
        except Exception as e:
            log.warning("publish_pending echoue: %s", e)

        log.info("=== FIN PIPELINE OK ===")
        return summary

    finally:
        LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description="Bot YouTube Shorts + Long")
    parser.add_argument("--long-only", action="store_true", help="Generer uniquement une video longue (10-15 min)")
    parser.add_argument("--short-only", action="store_true", help="Generer uniquement les Shorts")
    args = parser.parse_args()

    if args.long_only:
        # Mode video longue uniquement
        from pipeline.script_long import generer_script_long_safe
        from pipeline.visuels import generer_visuels
        from pipeline.voix import generer_voix
        from pipeline.montage import generer_montage
        import config

        fait = {
            "titre": "Analyse economique approfondie",
            "chiffre_cle": "3.5%",
            "resume": "Analyse approfondie de l'actualite economique",
            "source": "manuel",
            "theme": "generique",
        }
        script = generer_script_long_safe(fait)
        durees = {}
        for lang in ('fr', 'en', 'es'):
            blocs = script.get(lang, {}).get('blocs', {})
            for bk, text in blocs.items():
                if not isinstance(text, str):
                    text = str(text)
                canon = bk
                words = len(text.split())
                dur = max(10.0, words / 2.5)
                if canon not in durees or dur > durees[canon]:
                    durees[canon] = dur

        date_str = datetime.now().strftime("%Y-%m-%d")
        out_base = Path(config.OUTPUT_DIR) / "visuels" / (date_str + "_long")
        out_base.mkdir(parents=True, exist_ok=True)
        slides = generer_visuels(fait, out_base=out_base, durees_blocs=durees, mode="long")
        voice_result = generer_voix(script, mode="long", out_base=Path(config.OUTPUT_DIR) / "audio" / (date_str + "_long"))
        audio_base = Path(config.OUTPUT_DIR) / "audio" / (date_str + "_long") / date_str
        videos = generer_montage(date_str=date_str, slides_base=out_base, audio_base=audio_base, mode="long")
        print(json.dumps({"mode": "long", "videos": {k: str(v) for k, v in videos.items()}}, indent=2, default=str))
    elif args.short_only:
        result = run_daily()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        # Mode complet : Shorts + video longue
        result = run_daily()
        # Video longue en plus
        try:
            from pipeline.script_long import generer_script_long_safe
            from pipeline.visuels import generer_visuels
            from pipeline.voix import generer_voix
            from pipeline.montage import generer_montage
            import config

            fait = {
                "titre": "Analyse economique approfondie",
                "chiffre_cle": "3.5%",
                "resume": "Analyse approfondie de l'actualite economique",
                "source": "manuel",
                "theme": "generique",
            }
            script_long = generer_script_long_safe(fait)
            # Detecter si le script a des blocs longs
            long_blocs = {"introduction", "contexte", "analyse", "opinion", "ia_analysis", "perspectives"}
            has_long = any(b in script_long.get("fr", {}).get("blocs", {}) for b in long_blocs)
            mode = "long" if has_long else "short"
            log.info("Mode video longue: %s (has_long=%s)", mode, has_long)

            durees = {}
            for lang in ('fr', 'en', 'es'):
                blocs = script_long.get(lang, {}).get('blocs', {})
                for bk, text in blocs.items():
                    if not isinstance(text, str):
                        text = str(text)
                    canon = bk
                    words = len(text.split())
                    dur = max(10.0, words / 2.5)
                    if canon not in durees or dur > durees[canon]:
                        durees[canon] = dur

            date_str = datetime.now().strftime("%Y-%m-%d")
            out_base = Path(config.OUTPUT_DIR) / "visuels" / (date_str + "_long")
            out_base.mkdir(parents=True, exist_ok=True)
            slides_long = generer_visuels(fait, out_base=out_base, durees_blocs=durees, mode=mode)
            voice_long = generer_voix(script_long, mode=mode, out_base=Path(config.OUTPUT_DIR) / "audio" / (date_str + "_long"))
            audio_base = Path(config.OUTPUT_DIR) / "audio" / (date_str + "_long") / date_str
            videos_long = generer_montage(date_str=date_str, slides_base=out_base, audio_base=audio_base, mode=mode)
            result["videos_long"] = {k: str(v) for k, v in videos_long.items()}
            log.info("Videos longues: %s", result["videos_long"])

            # Upload des videos longues (optionnel)
            from pathlib import Path
            secrets = Path("config") / "client_secrets.json"
            if secrets.exists():
                try:
                    from pipeline.upload import upload_all
                    long_ids = upload_all(videos_long, script_long, playlist_map={"fr": "Actualites economiques FR - Long", "en": "Economic News EN - Long", "es": "Noticias Economicas ES - Long"})
                    log.info("Uploads longs: %s", long_ids)
                    result["video_ids_long"] = long_ids
                except Exception as e:
                    log.warning("Upload videos longues echoue: %s", e)
        except Exception as e:
            log.warning("Video longue echouee: %s", e)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))