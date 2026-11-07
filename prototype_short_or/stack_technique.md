# Stack technique — Prototype Short (et base pour automatisation)

## 1. Récupération données (Module A/C)

| Besoin | Outil / API | Coût | Note |
|--------|-------------|------|------|
| Prix or historique (quotidien/mensuel) | **FRED API** (St. Louis Fed) — `GOLDAMGBD228NLBM` | Gratuit (clé API) | Série officielle, mensuelle |
| Prix or temps réel | **TradingEconomics API** / **Alpha Vantage** / **Twelve Data** | Freemium / Payant | Pour prix du jour |
| Achats banques centrales | **World Gold Council** — rapports PDF/Excel | Gratuit (public) | Télécharger *Gold Demand Trends* |
| Inflation, taux, change | **FRED** / **ECB SDW** / **INSEE API** | Gratuit | Données officielles |
| Actualités (RSS) | **Reuters RSS** / **AP RSS** / **Banques centrales RSS** | Gratuit | Veille automatisée |

**Script Python recommandé :** `fetch_data.py` (voir ci-dessous)

---

## 2. Génération graphiques (Module C)

| Outil | Avantages | Inconvénients |
|-------|-----------|---------------|
| **Python + Matplotlib/Plotly** | Programmable, reproductible, charte graphique code, gratuit | Courbe d'apprentissage |
| **Canva (template + API)** | Visuel pro rapide, pas de code | Moins flexible, API limitée |
| **After Effects + expressions** | Animation pro, template réutilisable | Payant, plus lourd |
| **Flourish / Datawrapper** | Embeddable, interactif | Pas pour vidéo verticale native |

**Recommandation prototype :** **Python + Matplotlib** → export PNG/MP4 → import montage.
- Charte graphique codée une fois (couleurs, polices, style)
- Génération batch pour chaque Short
- Zéro risque copyright (graphiques originaux)

---

## 3. Narration TTS (Module D)

| Outil | Qualité | Coût | Langues | API |
|-------|---------|------|---------|-----|
| **ElevenLabs** | ⭐⭐⭐⭐⭐ | ~22$/mois (Creator) | 29+ | ✅ |
| **PlayHT** | ⭐⭐⭐⭐ | ~39$/mois | 140+ | ✅ |
| **Azure TTS (Neural)** | ⭐⭐⭐⭐ | Pay-as-you-go | 100+ | ✅ |
| **Google Cloud TTS** | ⭐⭐⭐⭐ | Pay-as-you-go | 50+ | ✅ |
| **Coqui TTS (local)** | ⭐⭐⭐ | Gratuit (GPU) | 16 | Local |

**Recommandation prototype :** **ElevenLabs** (meilleur rapport qualité/prix/voix naturelles multilingues).
- Voix cohérentes FR/EN/ES (même "personnage")
- API simple, réglage stabilité/similarité
- Clonage voix possible plus tard

---

## 4. Montage vidéo (Module D)

| Outil | Type | Automatisable | Coût |
|-------|------|---------------|------|
| **CapCut (Desktop)** | GUI + templates | Partiel (macro/shortcuts) | Gratuit |
| **DaVinci Resolve** | Pro NLE | Fusion + Python API | Gratuit / Studio 295$ |
| **Premiere Pro** | Pro NLE | ExtendScript / UXP | Abonnement |
| **MoviePy (Python)** | Code only | ✅ Total | Gratuit |
| **FFmpeg (CLI)** | Code only | ✅ Total | Gratuit |
| **Shotstack / JSON2Video** | Cloud API | ✅ Total | Payant |

**Recommandation prototype :** **CapCut Desktop** (rapide pour premier test) → **MoviePy + FFmpeg** pour automatisation future.
- CapCut : glisser-déposer, sous-titres auto, keyframes faciles
- MoviePy : script Python qui assemble (vidéo + audio + SRT) → MP4 final

---

## 5. Sous-titres

| Outil | Usage |
|-------|-------|
| **Whisper (OpenAI)** | Audio → SRT (si pas de script) |
| **Script → SRT direct** | Depuis nos scripts (timing précis) — **recommandé** |
| **CapCut / Premiere** | Sync manuel + style |
| **pysrt / srt (Python)** | Génération programmatique SRT |

---

## 6. Publication (Module E)

| Outil | Note |
|-------|------|
| **YouTube Data API v3** | Upload programmatique, playlist, métadonnées |
| **youtube-upload (CLI)** | Simple pour tests |
| **Social media schedulers** | Plus tard (Buffer, Later, Hootsuite) |

---

## 7. Architecture complète (prototype → automatisation)

```
┌─────────────────────────────────────────────────────────────┐
│  ORCHESTRATEUR (Python script / Airflow / n8n / Make)      │
└─────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
    ┌──────────┐         ┌──────────┐         ┌──────────┐
    │  MODULE A│         │  MODULE B│         │  MODULE C│
    │  VEILLE  │────────▶│  SELECT  │────────▶│  DATA/VIZ│
    │  (RSS)   │         │  (score) │         │ (charts) │
    └──────────┘         └──────────┘         └──────────┘
                                                          │
                                                          ▼
    ┌──────────┐         ┌──────────┐         ┌──────────┐
    │ MODULE E │◀────────│ MODULE D │◀────────│  SCRIPT  │
    │ PUBLISH  │         │  VIDEO   │         │  (LLM)   │
    └──────────┘         └──────────┘         └──────────┘
```

---

## 8. Fichiers de config suggérés

```
config/
├── channels.yaml          # Chain playlists, langues, branding
├── sources.yaml           # RSS feeds, API keys, endpoints
├── style.yaml             # Couleurs, polices, templates graphiques
├── tts.yaml               # Voix par langue, paramètres ElevenLabs
└── schedule.yaml          # Fréquence, heures publication par langue
```

---

## 9. Commandes utiles (prototype)

```bash
# 1. Récupérer données or
python fetch_data.py --series gold --start 2020-01-01 --end 2026-10-12

# 2. Générer graphiques
python charts/chart_price_timeline.py --input data/gold_price.csv --output charts/output/price_timeline.png
python charts/chart_cb_purchases.py --input data/cb_purchases.csv --output charts/output/cb_purchases.png

# 3. Générer audio TTS (ElevenLabs API)
python tts/generate.py --script script_FR.md --voice "pNInz6obpgDQGcFmaJgB" --output audio/narration_fr.mp3

# 4. Générer SRT depuis script
python subs/generate_srt.py --script script_FR.md --audio audio/narration_fr.mp3 --output subs/subs_fr.srt

# 5. Monter vidéo (MoviePy)
python video/assemble.py --template video/template_fr.py --audio audio/narration_fr.mp3 --subs subs/subs_fr.srt --charts charts/output/ --output video/short_fr.mp4

# 6. Upload YouTube
python publish/upload.py --video video/short_fr.mp4 --metadata metadata_FR.md --playlist "Actualités économiques FR"
```

---

## 10. Prochaines étapes immédiates

1. [ ] Créer clé API FRED (gratuit, 2 min)
2. [ ] Créer compte ElevenLabs (essai gratuit)
3. [ ] Télécharger données WGC *Gold Demand Trends Q1 2026* (PDF → Excel)
4. [ ] Écrire `fetch_data.py` pour séries FRED + WGC
5. [ ] Écrire scripts graphiques Matplotlib (charte graphique)
6. [ ] Générer 3 audios TTS (FR/EN/ES)
7. [ ] Monter 1er Short sur CapCut (validation visuelle)
8. [ ] Publier test (privé) → vérifier qualité
9. [ ] Itérer → puis automatiser avec MoviePy