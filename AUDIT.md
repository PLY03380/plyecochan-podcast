# Audit technique — Projet Chaîne YouTube Économique

**Date :** 26 octobre 2026 (v3 — mise à jour)
**Périmètre :** code Python du pipeline, configuration, hygiène du dépôt, conformité à la spec v2.

---

## 1. Résumé exécutif

Le pipeline (veille → sélection → script → visuels → voix → montage) est **fonctionnel et a produit des vidéos de test**. Depuis l'audit du 16/10, l'orchestrateur `bot.py`, le fichier `requirements.txt` et le brûlage des sous-titres dans `montage.py` ont été ajoutés, puis **les sous-titres ont été retirés du pipeline** (3 versions linguistiques suffisent). Les clés de blocs fallback ont été harmonisées. Le projet reste néanmoins **non exploitable en production automatique** : secrets en clair, pas de validation/upload YouTube, données simulées présentées comme officielles.

| Verdict | Détail |
|---|---|
| ❌ Bloquant | Clés API OpenRouter en clair dans `config.py` |
| ❌ Bloquant | Dépôt Git = `D:\` (tout le disque), zéro commit, pas de `.gitignore` |
| ✅ Fait | `pipeline/upload.py` créé et testé (YouTube Data API v3, public) |
| ❌ Bloquant | `pipeline/notif.py` absent (validation Telegram) |
| ⚠️ Critique | TTS : Edge-TTS (WordBoundary) désactivé → SRT basique une seule entrée ; Piper désormais fonctionnel (modèles dans `.venv/voices`, code corrigé pour l'API 1.8) mais sans WordBoundary |
| ⚠️ Critique | Données simulées dans `make_budget()` étiquetées *Sources : ONS, OBR, FRED* |
| ⚠️ Critique | 7 templates visuels sur 8 = slides quasi vides |
| ⚠️ Critique | Matching encore en sous-chaîne dans `score_keywords_tier*` et `score_emotionnel` |
| ⚠️ Critique | `requirements.txt` incomplet (gTTS, pyttsx3, piper manquants) |
| ✅ OK | Orchestrateur `bot.py` câblé (veille → script → visuels → voix → montage → DB) |
| ✅ OK | Sous-titres désactivés et retirés du pipeline (génération SRT + brûlage supprimés) |
| ✅ OK | `db_save()` / `db_set_status()` appelés dans `bot.py` |
| ✅ OK | Clés de blocs fallback FR/EN/ES harmonisées avec `expected_blocs` |

---

## 2. État des modules

| Module | Statut | Notes |
|---|---|---|
| `pipeline/veille.py` | ⚠️ | RSS OK (BBC/RFI/Le Monde) ; scoring regex avec bornes de mots |
| `pipeline/selection.py` | ⚠️ | Scoring enrichi OK ; matching sous-chaîne résiduel (§3) ; shadowing `config` |
| `pipeline/script.py` | ✅ | LLM + fallbacks OK (3 modèles × 2 clés, fallback local) ; `DATE_FMT` figé à l'import ; coquilles ES/FR résiduelles mineures |
| `pipeline/script_long.py` | ⚠️ | Génération script long (10 blocs, FR/EN/ES) via LLM ; fallback long (500+ mots) ; mode `--long` dans bot.py ; **clés OpenRouter épuisées (402)** — créditer pour obtenir des scripts de 2000+ mots |
| `pipeline/visuels.py` | ✅ | Sélection d'images de la bibliothèque (~1 image toutes les 5s) ; Matplotlib supprimé ; données simulées retirées |
| `pipeline/voix.py` | ⚠️ | Piper (modèles `.venv/voices`, API 1.8 corrigée) / gTTS / pyttsx3 ; Edge-TTS désactivé (403) ; pas de WordBoundary ; SRT basique |
| `pipeline/montage.py` | ✅ | Intégré : clips par image + presets auto + audio découpé ; sans sous-titres ; `tempfile` importé |
| `pipeline/presets.py` | ✅ | Détection + auto-organisation des presets par bloc/langue |
| `pipeline/package.py` | ✅ | Validation titre (score, majuscules, mobile, vague) + thumbnail text + description/tags SEO |
| `pipeline/analyze_comments.py` | ✅ | Analyse commentaires YouTube + génération sujet de vidéo longue (LLM) |
| `pipeline/visual_builder.py` | ❌ | Fichier mort (contient `test`) |
| `db.py` | ✅ | Correct ; appelé par `bot.py` |
| `config.py` | ❌ | Clés OpenRouter en dur ; pas de `.env` ; `python-dotenv` non utilisé |
| `bot.py` | ✅ | Orchestrateur complet (veille → script → packaging → visuels → voix → montage → upload → sync) + verrou |
| `watchdog.py` | ✅ | Relance le bot si les vidéos du jour ne sont pas uploadées (max 5 tentatives) |
| `sync_uploads.py` | ✅ | Vérifie et upload les vidéos manquantes (idempotent, par titre) |
| `run_bot.bat` | ✅ | Script de lancement pour Task Scheduler |
11. (Fait) `pipeline/indexing.py` cr�� et test� � indexation Google via API (service account).
| `pipeline/notif.py` | ❌ | Absent — validation Telegram prévue par la spec |
| `pipeline/upload.py` | ✅ | Upload YouTube Data API v3 + métadonnées pipeline ; testé et fonctionnel ; privacy=public ; quota limité (~6 vidéos/jour) |
| `blogger_poster.py` | ✅ | Publication articles Blogger (OAuth, safe_publish, build_article_html, generer_article_blog) ; intégré dans bot.py (étape 9, is_draft=False, article riche avec IA, embed YouTube fonctionnel, 3 langues FR/EN/ES, video integree par langue) |
| `pipeline/indexing.py` | ✅ | Indexation Google via API (service account, 200/jour) ; testé et fonctionnel ; intégré dans bot.py |
| `pipeline/indexing_bing.py` | ✅ | Indexation Bing/DuckDuckGo/Yahoo/Ecosia via IndexNow (illimité) ; testé et fonctionnel ; intégré dans bot.py |
| `pipeline/llm.py` | ✅ | Appel LLM multi-provider (Ollama → Groq → Gemini → OpenRouter) avec fallback automatique |
| `pipeline/facebook_poster.py` | ✅ | Publication Facebook (post texte, vidéo, Reel) ; optionnel (FACEBOOK_PAGE_TOKEN) |
| `sync_uploads.py` | ✅ | Vérification + upload vidéos manquantes (Shorts + longues, idempotent, jour en cours uniquement) |
| `watchdog.py` | ✅ | Relance le bot si vidéos non uploadées (max 5 tentatives, 30 min) |
| `run_bot.bat` | ✅ | Script de lancement pour Task Scheduler |
| `requirements.txt` | ⚠️ | Présent mais incomplet (gTTS, pyttsx3, piper non déclarés) |
| `pipeline/__init__.py` | ❌ | Absent (namespace package, fragile) |

---

## 3. Bugs critiques

### 3.1 Clés API en clair — `config.py:29-32`
Trois clés OpenRouter hardcodées (1 épuisée, 2 fonctionnelles). Tout fichier commité/poussé expose le crédit.
**Fix :** lire via `os.getenv("OPENROUTER_KEY_1")` + `.env` (python-dotenv) + `.gitignore` + régénérer les clés exposées.

### 3.2 Sous-titres — désactivés (décision utilisateur)
La génération de SRT et le brûlage dans `montage.py` ont été retirés : 3 versions linguistiques (FR/EN/ES) suffisent. `voix.py` ne génère plus de SRT, `montage.py` assemble slides + audio uniquement. Edge-TTS reste désactivé (403 réseau) mais n'est plus nécessaire.
**Fix :** soit réactiver Edge-TTS via proxy, soit implémenter WordBoundary pour un autre moteur, soit accepter le SRT basique documenté.

### 3.3 Données simulées présentées comme officielles — `pipeline/visuels.py:288-293`
`make_budget()` dessine des courbes dette/déficit codées en dur tout en affichant *« Sources : IFS, ONS, OBR »* / *« ONS, OBR, FRED »*. Risque crédibilité/misinformation.
**Fix :** brancher de vraies séries (FRED/Banque mondiale) ou retirer la mention de source et marquer « illustration ».

### 3.4 Matching par sous-chaîne résiduel — `pipeline/selection.py`
`score_marketing_bonus` utilise bien `_contains_kw` (bornes de mots), mais :
- `score_keywords_tier1` / `score_keywords_tier2` : `kw in text` → faux positifs (`"change"` dans `"exchange"`, `"rate"` dans `"generate"`).
- `score_emotionnel` : `mot in text` → faux positifs.
- `geo_prioritaire` est correct côté marketing, mais `score_keywords_tier2` domaines incluent des termes courts.
**Fix :** réutiliser `_contains_kw` / regex `\b...\b` partout.

### 3.5 Score émotionnel dominant — `pipeline/selection.py:155-166`
Jusqu'à 130 pts (peur 40 + surprise 36 + colère 30 + fomo 24) vs fraîcheur max 50. Un titre putaclic peut battre une actu macro réelle.
**Fix :** plafonner le total émotionnel (~40) et le pondérer sous le score macro.

### 3.6 Shadowing du module `config` — `pipeline/selection.py:159`
`for emotion, config in TOUS_MOTS_EMOTIONNELS.items()` écrase l'import `config`. Inoffensif aujourd'hui (selection n'utilise pas config ensuite) mais fragile.
**Fix :** renommer en `cfg` / `emo_cfg`.

### 3.7 TTS fallbacks non déclarés — `requirements.txt`
`voix.py` utilise gTTS, pyttsx3 (et tente Piper) mais `requirements.txt` les commente ou les omet. Installation fraîche → gTTS/pyttsx3 absents → TTS échoue. Piper n'est pas installé dans l'environnement actuel (confirmé).
**Fix :** déclarer `gTTS>=2.3`, `pyttsx3>=2.90`, `piper-tts` (optionnel) dans `requirements.txt` ; unifier l'environnement (un seul venv avec toutes les dépendances) ; télécharger les modèles Piper (`piper --download-dir`) si on veut l'utiliser.

### 3.8 Sous-titres — retirés (voir 3.2)
Plus de SRT ni de brûlage : `montage.py` assemble slides + audio uniquement. La durée des slides reste uniforme (`audio_dur / n`).

---

## 4. Bugs mineurs / dette technique

| # | Fichier | Problème |
|---|---|---|
| 1 | `script.py:26` | `DATE_FMT` figé à l'import : un process long qui passe minuit produit de mauvaises dates |
| 2 | `script.py:202` | `DATE_FMT["iso"]` (module) vs `date_fmt` local (incohérent) |
| 3 | `voix.py` | `asyncio.get_event_loop()` déprécié en 3.11+ → utiliser `asyncio.run()` |
| 4 | `voix.py:_generate_basic_srt` | Appel direct `ffprobe` (pas sur le PATH avec imageio-ffmpeg) → tombe toujours dans l'estimation |
| 5 | `voix.py:generer_voix` | `__import__("datetime")` illisible |
| 6 | `montage.py` | Durées slides uniformes `audio/n` : pas de sync WordBoundary |
| 7 | `visuels.py` | 7 templates sur 8 dégradent vers `make_generique_with_assets` = 3 slides quasi vides |
| 8 | `test_full_pipeline.py:36-40` | Chemins/dates codés en dur (`2026-10-15`) |
| 9 | Racine | 12 fichiers `test_*.py` quasi identiques — à consolider dans `tests/` |
| 10 | Racine | `output.json` corrompu (UTF-16 + log d'erreur), `ffmpeg_stderr.txt`, `build_image_library.log`, `test_fr.mp3` / `test_quick.mp3` vides (0 octet) |
| 11 | Racine | `__pycache__/`, `images_backup/` (doublon de `images/`) — à ignorer/supprimer |
| 12 | Dépôt Git | Repo Git = `D:\` (tout le disque), zéro commit, pas de `.gitignore` |
| 13 | `pipeline/` | `__init__.py` absent (namespace package, fragile) |
| 14 | `pipeline/visual_builder.py` | Fichier mort (contient `test`) |
| 15 | `config.py` | `OPENROUTER_MODEL` déclaré mais `script.py` utilise sa propre liste `MODELS` |
| 16 | Environnement | `.venv` configuré avec `include-system-site-packages = true` pour unifier Piper + dépendances cœur ; à documenter dans le README / `requirements.txt` pour reproductibilité |

---

## 5. Écart avec la spec v2

| Spec (§7-§8) | Réalité |
|---|---|
| API Claude + web_search pour la veille | ❌ RSS seuls (acceptable, mais non documenté comme décision) |
| Recoupement ≥ 2 sources | ⚠️ `MIN_CONFIRMATIONS = 0` (désactivé, URLs Reuters/AP mortes) |
| Graphiques recréés depuis données officielles | ❌ Données simulées pour la plupart des templates (budget) |
| Sous-titres synchronisés brûlés (WordBoundary) | ✅ Retirés du périmètre (3 versions linguistiques suffisent) |
| Validation Telegram (Approuver/Rejeter) | ❌ `notif.py` absent |
| Upload YouTube API v3 | ❌ `upload.py` absent du pipeline (prototype existe) |
| Orchestrateur `bot.py` + cron 6h | ⚠️ `bot.py` présent, cron absent |
| Coût < 1 $/jour | ✅ cohérent (modèles cheap, TTS gratuit) |

Les vidéos de test font ~18 s alors que la spec vise 35–55 s : les blocs fallback sont trop courts et la durée des slides est uniforme. Point à corriger dès que la narration réelle est branchée.

---

## 6. Plan de remédiation priorisé

### P0 — Avant toute publication réelle
1. Sortir les clés de `config.py` → variables d'env + `.env` + `.gitignore` ; régénérer les clés OpenRouter exposées.
2. Créer un dépôt Git **dans** `D:\Cahine youtube economique\` (pas à la racine `D:\`) avec `.gitignore` (`__pycache__`, `output/`, `*.mp3`, `data/*.db`, `.env`, `.venv/`).
3. Corriger l'ordre TTS : réactiver Edge-TTS (proxy) ou documenter l'absence de WordBoundary ; sinon marquer SRT comme « basique ».
4. (Fait) Sous-titres retirés du pipeline — génération SRT et brûlage supprimés.
5. Retirer la mention de source sur `make_budget()` ou brancher de vraies séries.
6. (Fait) `pipeline/upload.py` créé et testé — upload YouTube Data API v3, public.
7. (Fait) `blogger_poster.py` créé et testé — publication articles Blogger.
8. (Fait) `sync_uploads.py` créé — vérification et upload des vidéos manquantes.
9. (Fait) `watchdog.py` créé — relance automatique du bot.
10. (Fait) `run_bot.bat` créé — script de lancement pour Task Scheduler.

### P1 — Chaîne de production fiable
6. Écrire `pipeline/notif.py` (Telegram Approuver/Rejeter) et `pipeline/upload.py` (réutiliser `prototype_short_or/publish/upload.py`).
7. Compléter `requirements.txt` (gTTS, pyttsx3, piper optionnel, python-dotenv déjà présent).
8. Ajouter `pipeline/__init__.py`.
9. Supprimer `pipeline/visual_builder.py` (mort).
10. Corriger le matching sous-chaîne dans `selection.py` (réutiliser regex bornes) + plafonner score émotionnel + renommer shadowing `config`.
11. Remplacer `asyncio.get_event_loop()` par `asyncio.run()` dans `voix.py`.
12. Utiliser `imageio_ffmpeg` pour ffprobe dans `voix.py` et `montage.py`.

### P2 — Qualité éditoriale
13. Enrichir les 7 templates génériques de `visuels.py` ou réduire à 3 types réellement supportés.
14. Brancher de vraies séries de données (FRED/Banque mondiale) pour `make_budget()`.
15. (Fait) Durée cible 40-50s : contrainte MAX 120 mots ajoutée au prompt LLM dans `script.py`.
16. Consolidation des `test_*.py` racine → un seul `tests/` avec asserts ; retirer les chemins/dates codés en dur.
17. Nettoyer la racine (`output.json` corrompu, logs, mp3 vides, `images_backup/`, `__pycache__/`).
18. Filtrer les vidéos test dans `sync_uploads.py` (ignorer les titres génériques "Video fr/en/es", "TEST").
19. Nettoyer les anciens fichiers de test dans `output/`.

### P3 — Fiabilité long terme
18. Planification cron/Task Scheduler à 6h (heure Madagascar) avec verrou anti-exécution concurrente. Script `run_bot.bat` créé. Verrou `bot.lock` dans `bot.py`.
19. `watchdog.py` créé : vérifie si les vidéos du jour sont uploadées, relance le bot si nécessaire (max 5 tentatives, 30 min entre chaque).
20. `MIN_CONFIRMATIONS = 1` une fois un 4e flux RSS ajouté (investiguer URLs alternatives Reuters/AP).
21. Journalier : rapport Telegram synthétique (sujet choisi, score, durée vidéo, erreurs).
22. Revalider Edge-TTS sur le réseau cible (403) et documenter la décision.

---

## 7. Architecture presets (décision utilisateur)

Des petits clips vidéo génériques (avec leur propre son) sont placés dans
`video/<Bloc>/` et insérés automatiquement avant le bloc correspondant :

| Dossier | Bloc | Position |
|---|---|---|
| `video/Impacte pour vous/` | accroche | début |
| `video/Fait/` | fait | avant le bloc fait |
| `video/Pourquoi/` | pourquoi | avant le bloc pourquoi (à venir) |
| `video/Impact/` | impact | avant le bloc impact (à venir) |
| `video/Conclusion/` | conclusion | avant le bloc conclusion (à venir) |
| `video/Suscribe/` | subscribe | fin |

- Détection automatique par langue via `pipeline/presets.py` (`find_preset`, `list_presets`).
- Nommage automatique : `organiser_presets()` renomme les fichiers en `<bloc> <lang>.mp4` (ex. `accroche fr.mp4`, `fait en.mp4`). L'utilisateur peut déposer des fichiers avec n'importe quel nom contenant le code langue — le pipeline les renomme au démarrage.
- Les presets sont réencodés à 1080×1920 30 fps et concaténés avec les clips d'images.
- La narration Piper est découpée par bloc pour muxer avec chaque clip.
- Les presets manquants sont ignorés sans erreur (pas de blocage).

## 8. Stratégie blog PlyChanEconomie (à implémenter point par point)

### Objectif
Le blog n'est pas un simple résumé d'article. C'est un **environnement d'engagement** qui :
- Attire du trafic Google (SEO) vers la chaîne YouTube.
- Invite les lecteurs à donner leur avis (commentaires, sondages).
- Invite l'IA et des **comptes générés par IA** à participer (analyse, opinion, débat).
- Génère des vidéos longues (10-15 min) avec la même structure que les Shorts, à partir des articles les plus demandés.

### Architecture de l'article (riche, pas un résumé)

1. **Titre SEO** : mots-clés + chiffre + date (en anglais US/UK).
2. **Snippet** (2 premières lignes) : ce que la vidéo donne + chiffre clé.
3. **Vidéo intégrée** (above the fold) : iframe YouTube.
4. **Analyse** : ce que le chiffre signifie pour le lecteur.
5. **Données** : graphiques, tableaux, sources.
6. **Opinion** : "Mon avis : ..." (tranché, engageant).
7. **Section IA** : l'avis d'une IA (Claude/ChatGPT) sur le sujet + avis de comptes générés par IA.
8. **Sondage** : Google Forms intégré ("Pensez-vous que... ?").
9. **CTA d'abonnement** : bouton + lien direct (`?sub_confirmation=1`).
10. **Lien vers l'article précédent** (série thématique).

### Stratégies d'engagement
- **Polls/sondages** : intégrer Google Forms, utiliser les résultats pour choisir le prochain sujet.
- **IA comme invité** : section "L'avis de l'IA" avec analyse d'une IA.
- **Comptes générés par IA** : des personnages IA qui participent aux commentaires et donnent leur avis.
- **Opinion et débat** : section "Mon avis" tranchée + invitation à commenter.
- **Vidéos longues** : même structure que les Shorts (presets + images + audio par bloc), mais avec plus de blocs et des blocs plus longs. Durée cible : 10-15 min. Générées à partir des articles les plus demandés (analyse des commentaires).

### SEO blog
- Titres en anglais US/UK (plus de trafic).
- URL slug court et descriptif.
- Meta description 155 chars max.
- Structure H1/H2 avec mots-clés.
- Liens internes entre articles (série).
- 1 article par jour (aligné avec la vidéo).

### Monétisation
- YouTube Partner Program (1000 abonnés + 4000h ou 10M Shorts views).
- AdSense sur le blog (trafic suffisant).
- Affiliation (liens vers produits/services économiques).
- Sponsoring (audience qualifiée).

### Plan d'implémentation (point par point)
1. Améliorer `build_article_html()` avec la nouvelle structure (analyse + opinion + sondage + CTA).
2. Ajouter une fonction `generer_article_blog()` qui utilise le LLM pour générer un article long et engageant.
3. Intégrer les sondages Google Forms dans les articles.
4. Ajouter une section "L'avis de l'IA" avec analyse automatique (inviter les comptes IA existants à participer).
5. Inviter les comptes gérés par des IA à commenter et donner leur avis (pas de création de comptes, juste une invitation).
6. Générer des vidéos longues (10-15 min) avec la même structure que les Shorts, à partir des articles les plus demandés (analyse des commentaires).
7. Intégrer `safe_publish` dans `bot.py` (brouillon d'abord, puis public).

### Ce qui est déjà fait
- ✅ `blogger_poster.py` créé (publish_post, update_post, build_article_html, safe_publish).
- ✅ Authentification OAuth fonctionnelle (token rafraîchi automatiquement).
- ✅ Brouillon de test créé avec succès.
- ❌ Intégration dans `bot.py` (pas encore fait).
- ❌ Structure d'article riche (pas encore implémentée).
- ❌ Sondages, IA invité, comptes IA (pas encore implémentés).

## 9. Points forts à conserver

- Architecture modulaire claire, une responsabilité par fichier.
- Stratégie de fallback systématique (multi-modèles LLM, multi-TTS) — seule la priorité/qualité est à ajuster.
- Asset library (219 concepts, manifest JSON) bien intégrée aux templates.
- Spécification et journaux (`JOURNAL_ETAPE_0.md`, `JOURNAL_PROGRESSION.md`) à jour — reprise de contexte facile.
- Stack 100 % gratuite cohérente avec l'objectif économique du projet.
- `bot.py` désormais présent et câblé de bout en bout (veille → DB → script → visuels → voix → montage).

---

*Audit réalisé le 19/10/2026 — revue statique du code + vérifications d'import/exécution (aucune exécution du pipeline complet ni appel réseau).*