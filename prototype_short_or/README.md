# Prototype Short : L'or à 5 595 $ — Record historique

## 🎯 Objectif
Produire un **premier Short vertical (9:16, ~45s)** sur le record historique de l'or (5 595 $/oz, 29 jan 2026), décliné en **3 langues (FR/EN/ES)**, avec graphiques originaux recréés à partir de données publiques.

---

## 📁 Structure

```
prototype_short_or/
├── script_FR.md           # Script FR (structure accroche→fait→chiffre→conséquence→question)
├── script_EN.md           # Script EN (adapté, pas traduit mot à mot)
├── script_ES.md           # Script ES (adapté)
├── plan_production.md     # Plan détaillé visuels, graphiques, charte, workflow
├── metadata_FR.md         # Titre, description, tags, playlist FR
├── metadata_EN.md         # Métadonnées EN
├── metadata_ES.md         # Métadonnées ES
├── stack_technique.md     # Stack complète (data, viz, TTS, montage, publish)
├── data/
│   ├── fetch_data.py      # Récupération FRED (prix or, inflation, taux) + WGC (achats BC)
│   ├── gold_daily.csv     # Prix or quotidien (FRED)
│   ├── gold.csv           # Prix or mensuel (FRED)
│   └── cb_gold_purchases.csv  # Achats nets banques centrales 2010-2026 (WGC)
├── charts/
│   ├── chart_price_timeline.py      # Courbe prix or 2020-2026 + pic annoté
│   ├── chart_cb_purchases.py        # Barres horizontales achats BC 2010-2026
│   ├── chart_annual_perf.py         # Performance annuelle % 2015-2025
│   └── output/                      # PNG générés (1080x1920)
├── subs/
│   ├── generate_srt.py    # Script → SRT (timing depuis audio)
│   └── subs_fr.srt / _en.srt / _es.srt
├── audio/
│   ├── narration_fr.mp3   # TTS ElevenLabs / Azure / PlayHT
│   ├── narration_en.mp3
│   └── narration_es.mp3
└── video/
    ├── assemble.py        # Montage MoviePy (charts + audio + SRT → MP4)
    ├── short_fr.mp4
    ├── short_en.mp4
    └── short_es.mp4
publish/
└── upload.py              # Upload YouTube Data API v3 (privé pour test)
```

---

## 🚀 Lancement rapide (prototype manuel)

### 1. Prérequis
```bash
# Python 3.10+
pip install pandas requests matplotlib moviepy pysrt google-api-python-client google-auth-oauthlib ffmpeg-python

# ffmpeg installé (Windows: winget install ffmpeg / chocolately / scoop)
```

### 2. Clés API
- **FRED** : gratuit sur https://fred.stlouisfed.org/docs/api/api_key.html → `export FRED_API_KEY=your_key`
- **ElevenLabs** : essai gratuit sur https://elevenlabs.io → compte pour TTS
- **YouTube Data API v3** : Google Cloud Console → activer API → OAuth 2.0 client → sauver `config/client_secrets.json`

### 3. Données
```bash
cd prototype_short_or/data
python fetch_data.py --series gold_daily --start 2020-01-01 --end 2026-10-12
python fetch_data.py --series cb_gold  # génère cb_gold_purchases.csv (vérifier chiffres WGC)
```

### 4. Graphiques
```bash
cd ../charts
python chart_price_timeline.py
python chart_cb_purchases.py
python chart_annual_perf.py
# → Vérifier PNG dans charts/output/
```

### 5. Audio (TTS)
- Copier scripts FR/EN/ES dans ElevenLabs (ou PlayHT/Azure)
- Choisir voix cohérente multilingue
- Exporter 3 MP3 dans `audio/`

### 6. Sous-titres
```bash
cd ../subs
python generate_srt.py --script ../script_FR.md --audio ../audio/narration_fr.mp3 --output subs_fr.srt
python generate_srt.py --script ../script_EN.md --audio ../audio/narration_en.mp3 --output subs_en.srt
python generate_srt.py --script ../script_ES.md --audio ../audio/narration_es.mp3 --output subs_es.srt
```

### 7. Montage
```bash
cd ../video
python assemble.py --lang FR --audio ../audio/narration_fr.mp3 --subs ../subs/subs_fr.srt --charts ../charts/output --output short_fr.mp4
python assemble.py --lang EN --audio ../audio/narration_en.mp3 --subs ../subs/subs_en.srt --charts ../charts/output --output short_en.mp4
python assemble.py --lang ES --audio ../audio/narration_es.mp3 --subs ../subs/subs_es.srt --charts ../charts/output --output short_es.mp4
```

### 8. Test upload (privé)
```bash
cd ../../publish
python upload.py --video ../prototype_short_or/video/short_fr.mp4 --metadata ../prototype_short_or/metadata_FR.md --playlist "Actualités économiques FR"
```

---

## ✅ Checklist validation prototype

- [ ] Données récupérées (FRED + WGC)
- [ ] 3 graphiques générés (PNG 1080x1920, charte graphique respectée)
- [ ] 3 audios TTS générés (voix naturelle, prononciation vérifiée)
- [ ] 3 SRT synchronisés
- [ ] 3 vidéos montées (MP4, <60s, 9:16, H.264)
- [ ] Upload test privé → vérifier qualité, sous-titres, métadonnées
- [ ] Itérer si nötig (timing, taille police, couleurs)

---

## 🔄 Prochaines étapes (automatisation)

1. **Orchestrateur** : script unique qui lance tout (fetch → charts → TTS → SRT → assemble → upload)
2. **Veille RSS** : Module A (Reuters, AP, banques centrales)
3. **Sélection auto** : Module B (scoring importance/fraîcheur/audience)
4. **Script LLM** : Module D (génération script structuré depuis faits bruts)
5. **Planification** : Publication quotidienne/hebdomadaire selon rythme choisi

---

## 📝 Notes importantes

- **Graphiques recréés** = 0 risque copyright, monétisation favorisée
- **Validation humaine** obligatoire avant publish (chiffres, prononciation, ton)
- **Mêmes visuels, langues différentes** = 1 montage, 3 exports
- **Playlists séparées** = algorithme YouTube comprend l'audience par langue