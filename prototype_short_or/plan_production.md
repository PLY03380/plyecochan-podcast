# Plan de production — Short Prototype : L'or à 5 595 $

**Objectif :** Produire une vidéo verticale 9:16 de ~45s, déclinée FR/EN/ES, même montage, voix et textes adaptés.

---

## 1. Visuels nécessaires (par segment)

| Timecode | Segment | Visuel recommandé | Source données / Note |
|----------|---------|-------------------|------------------------|
| 0:00-0:03 | Accroche | Animation logo chaîne + texte « RECORD HISTORIQUE » + icône lingot or qui brille | Habillage chaîne (créer template) |
| 0:03-0:11 | Fait | **Graphique 1** : Courbe prix or 2020-2026 avec pic marqué « 5 595 $ — 29 jan 2026 » | Données : TradingEconomics / NordFX / WGC — **Recréer le graphique** (Python/Matplotlib ou Canva template) |
| 0:11-0:23 | Chiffres | **Graphique 2** : Barres annuelles performance or (2020-2025) — 2025 en rouge/or +65% | Données : WGC Gold Demand Trends / TradingEconomics — Recréer |
| 0:11-0:23 | Chiffres | **Infographie** : 3 compteurs animés « +65% » « 244 t T1 2026 » « ~800 t/an » | Animation simple (After Effects / CapCut / template) |
| 0:23-0:38 | Conséquences | **Icônes animées** 3 moteurs :<br>1. Globe + flèches sortie $ (banques centrales)<br>2. Billet $ qui baisse + courbe taux qui baisse (Fed)<br>3. Carte monde avec points chauds (géopolitique) | Icônes libres de droits (FlatIcon, Icons8) ou créées |
| 0:23-0:38 | Conséquences | **Graphique 3** : Achats nets banques centrales 2010-2026 (barres) — explosion 2022-2026 | Données : WGC — **Recréer impératif** (données publiques, graphique original) |
| 0:38-0:45 | Conclusion | Écran final : logo chaîne + « ABONNEZ-VOUS » + icône cloche + handle @chaine | Template réutilisable |

---

## 2. Données à récupérer (pour graphiques recréés)

| Graphique | Données brutes nécessaires | Source officielle |
|-----------|---------------------------|-------------------|
| Prix or 2020-2026 | Série journalière/mensuelle XAU/USD | FRED (St. Louis Fed) : `GOLDAMGBD228NLBM` ou TradingEconomics API |
| Performance annuelle | % changement annuel 2015-2025 | WGC / FRED / Calculé depuis série prix |
| Achats banques centrales | Tonnes nettes par an 2010-2026 | **World Gold Council** — *Gold Demand Trends* (données publiques dans rapports) |

> ⚠️ **Règle d'or :** Récupérer la **donnée brute** (CSV, Excel, API), **recréer le graphique** dans notre charte graphique. Pas de capture d'écran WGC/TradingEconomics.

---

## 3. Charte graphique (à définir une fois)

| Élément | Spécification |
|---------|---------------|
| **Couleur principale** | Or (#FFD700 / #FFA500) + Bleu foncé (#0B1D3A) + Blanc |
| **Police titres** | Inter Bold / Montserrat Bold |
| **Police corps** | Inter Regular / Roboto |
| **Style graphiques** | Fond sombre, courbes or, grille discrète, annotations blanches |
| **Lower third** | Bandeau bas : « Source : World Gold Council / FRED » |
| **Logo animé** | 2s au début, 1s à la fin |

---

## 4. Audio / Narration

| Langue | Outil TTS recommandé | Voix suggérée |
|--------|---------------------|---------------|
| **FR** | ElevenLabs / PlayHT / Azure TTS | Voix masculine claire, débit ~150 mots/min |
| **EN** | ElevenLabs / PlayHT / Azure TTS | Voix masculine neutre (US), débit ~150 mots/min |
| **ES** | ElevenLabs / PlayHT / Azure TTS | Voix masculine neutre (ES/latam), débit ~150 mots/min |

> **Validation humaine obligatoire** : Vérifier prononciation « 5 595 », « once », « WGC », noms propres (Chine, Inde, Turquie, Fed, Moyen-Orient).

---

## 5. Sous-titres

- **Générés automatiquement** depuis le script (Whisper / script → SRT)
- **Synchronisés** manuellement sur CapCut / Premiere / DaVinci
- **Style** : Blanc, police Inter, contour noir, position safe zone (bas écran)
- **3 fichiers SRT** : `subs_fr.srt`, `subs_en.srt`, `subs_es.srt`

---

## 6. Montage (workflow)

```
1. Générer 3 graphiques (Python script → MP4/PNG séquences)
2. Créer projet vertical 1080x1920 dans CapCut / Premiere / DaVinci
3. Importer visuels + animations icônes
4. Générer 3 pistes audio TTS (FR/EN/ES)
5. Monter vidéo FR (référence) : caler visuels sur audio FR
6. Dupliquer projet → remplacer audio + sous-titres + textes affichés pour EN/ES
7. Exporter 3 versions : short_fr.mp4, short_en.mp4, short_es.mp4
```

---

## 7. Métadonnées publication (par langue)

| Champ | FR | EN | ES |
|-------|-----|-----|-----|
| **Titre** | Pourquoi l'or a-t-il battu son record à 5 595 $ ? | Why Did Gold Hit a Record $5,595? | ¿Por qué el oro rompió su récord en 5 595 $? |
| **Description** | Voir fichier `metadata_FR.md` | Voir `metadata_EN.md` | Voir `metadata_ES.md` |
| **Tags** | or, économie, banques centrales, inflation, record, actualité | gold, economy, central banks, inflation, record, news | oro, economía, bancos centrales, inflación, récord, noticias |
| **Playlist** | Actualités économiques FR | Economic News EN | Noticias Económicas ES |
| **Hashtags** | #Or #Économie #BanquesCentrales #Shorts | #Gold #Economy #CentralBanks #Shorts | #Oro #Economía #BancosCentrales #Shorts |

---

## 8. Checklist avant publication

- [ ] Scripts validés (faits, chiffres, prononciation)
- [ ] Graphiques recréés à partir de données brutes (pas de captures)
- [ ] Sources citées dans description + lower third vidéo
- [ ] 3 versions vidéo exportées (1080x1920, H.264, <60s)
- [ ] 3 fichiers SRT synchronisés
- [ ] Titres, descriptions, tags, playlists prêts
- [ ] Miniatures (thumbnails) créées si applicable (Shorts n'en utilisent pas toujours)

---

## 9. Fichiers à produire

```
prototype_short_or/
├── script_FR.md
├── script_EN.md
├── script_ES.md
├── plan_production.md          (ce fichier)
├── metadata_FR.md
├── metadata_EN.md
├── metadata_ES.md
├── data/
│   ├── gold_price_2020_2026.csv
│   ├── gold_annual_perf.csv
│   ├── cb_gold_purchases_2010_2026.csv
│   └── fetch_data.py           (script récupération données)
├── charts/
│   ├── chart_price_timeline.py
│   ├── chart_annual_perf.py
│   ├── chart_cb_purchases.py
│   └── output/                 (PNG/MP4 générés)
├── audio/
│   ├── narration_fr.mp3
│   ├── narration_en.mp3
│   └── narration_es.mp3
├── subs/
│   ├── subs_fr.srt
│   ├── subs_en.srt
│   └── subs_es.srt
└── video/
    ├── short_fr.mp4
    ├── short_en.mp4
    └── short_es.mp4
```