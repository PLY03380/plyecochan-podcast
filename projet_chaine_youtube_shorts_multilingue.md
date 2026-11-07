# Projet : chaîne YouTube Shorts d'actualités économiques multilingues

> **Version 2 — mise à jour le 12 octobre 2026**
> Intègre les décisions prises après la première production réelle.

---

## 1. L'idée principale

Créer une seule chaîne YouTube consacrée aux **actualités économiques du jour ou de la veille**, avec des vidéos courtes (YouTube Shorts) adaptées à plusieurs langues afin de toucher des publics de différents pays et d'augmenter les possibilités de monétisation.

> **Principe :** chaque jour → 1 fait marquant économique → 1 vidéo → déclinée en FR / EN / ES → publiée sur une seule chaîne.

### La question centrale de chaque vidéo

Chaque Short doit répondre à ces **3 questions** dans cet ordre :

| # | Question | Rôle dans le script |
|---|---|---|
| 1 | **Qu'est-ce qui s'est passé ?** | Accroche + fait daté |
| 2 | **Pourquoi c'est arrivé ?** | Contexte + causes |
| 3 | **Quel est l'impact ?** | Conséquences pour le spectateur / l'économie mondiale / Madagascar |

> C'est ce cadre qui distingue la chaîne d'un simple fil d'actualités : on explique, on contextualise, on relie l'info à la vie réelle.

---

## 2. Organisation de la chaîne

| Playlist | Langue | Public visé |
|---|---|---|
| **Economic News EN** | Anglais | États-Unis, Royaume-Uni, Canada, public anglophone international |
| **Actualités économiques FR** | Français | France, Belgique, Suisse, Québec, Afrique francophone |
| **Noticias Económicas ES** | Espagnol | Espagne et Amérique latine |

- **Option choisie :** une seule chaîne YouTube. La **même vidéo** est produite une seule fois (mêmes images, animations et montage), puis déclinée en **3 langues** (narration, sous-titres, titre et description adaptés).
- **Lancement :** français + anglais en priorité, espagnol ajouté dès que la production est stable.

---

## 3. Les sujets à couvrir

Critères de sélection : **fraîcheur (jour J ou J-1)** + **importance économique** + **impact visible pour le spectateur**.

- **Banques centrales** : décisions de la Fed, de la BCE, évolution des taux d'intérêt.
- **Inflation et économie** : prix, emploi, croissance, pouvoir d'achat.
- **Marchés financiers** : dollar, euro, or, pétrole, indices boursiers.
- **Commerce mondial** : droits de douane, exportations, importations, tensions commerciales.
- **Afrique et Madagascar** : matières premières, ariary, énergie, conséquences locales.

> **Objectif éditorial :** ne pas seulement raconter l'info, mais répondre à *Qu'est-ce qui s'est passé ? → Pourquoi ? → Quel impact ?*

---

## 4. Structure narrative de chaque Short (30–60 secondes)

Chaque script suit **5 blocs fixes** :

| Bloc | Durée cible | Contenu |
|---|---|---|
| **1. Accroche** | ~5s | La phrase qui arrête le scroll (chiffre choc, fait inattendu) |
| **2. Fait** | ~8s | Ce qui s'est passé — date, lieu, acteur principal |
| **3. Pourquoi** | ~12s | Causes : politique monétaire, crise, décision gouvernementale... |
| **4. Impact** | ~15s | Conséquences concrètes : pour le consommateur, les marchés, Madagascar |
| **5. Conclusion** | ~8s | Question ouverte + appel à commenter + abonnement |

---

## 5. Exemple de contenu

**Actualité du 12 octobre 2026 :** l'or franchit 2 700 $ l'once — record absolu.

| Bloc | Script FR |
|---|---|
| Accroche | *"L'or vient de franchir un seuil jamais atteint dans l'histoire."* |
| Fait | *"Ce 12 octobre 2026, le prix de l'or a dépassé 2 700 $ l'once pour la première fois."* |
| Pourquoi | *"La Fed a baissé ses taux. Les banques centrales mondiales achètent massivement de l'or depuis 2 ans."* |
| Impact | *"Pour vous : l'or protège contre l'inflation. Pour Madagascar : les exportations de minéraux précieux valent plus cher."* |
| Conclusion | *"L'or bat des records. Avez-vous de l'or dans votre épargne ? Dites-le en commentaire."* |

| Version | Titre YouTube |
|---|---|
| 🇫🇷 Français | Pourquoi le prix de l'or explose ? 2 700 $ — Record absolu #shorts |
| 🇬🇧 Anglais | Gold Hits $2,700 ALL TIME HIGH — Here's Why #shorts |
| 🇪🇸 Espagnol | El Oro supera los 2.700$ — RÉCORD HISTÓRICO #shorts |

---

## 6. Sources fiables

### Sources de veille quotidienne (récupération des news)

| Source | Type | Usage |
|---|---|---|
| **API Claude (web search)** | IA avec recherche web | Source principale — recherche les faits marquants du jour, recoupement automatique |
| **RSS Reuters Business** | Flux RSS | Confirmation et titres bruts |
| **RSS AP Economics** | Flux RSS | Confirmation et titres bruts |
| **RSS BBC Business** | Flux RSS | Confirmation et titres bruts |
| **RSS RFI Économie** | Flux RSS | Version francophone |

### Sources de vérification des chiffres

- **FMI** (imf.org) et **Banque mondiale** (worldbank.org) : données macroéconomiques.
- **Communiqués officiels** des banques centrales (Fed, BCE, Banque centrale de Madagascar).
- **World Gold Council**, **OPEP**, **Eurostat**, **INSEE** selon le sujet.

### Règle sur les visuels

| Méthode | Conseil |
|---|---|
| **Graphiques recréés à partir de données officielles** | ✅ **Option recommandée** — données publiques, visuel propre, zéro risque |
| Capture d'écran d'un graphique officiel (FMI, Banque mondiale) | Acceptable au lancement avec mention claire de la source |
| Découpage d'une vidéo de chaîne TV | ❌ Licence ou autorisation nécessaire |

> **Règle d'or :** récupérer la *donnée*, recréer le *graphique*. Les données officielles sont publiques ; leur mise en page ne l'est pas.

---

## 7. Pipeline de production automatisé

### Module A — Veille quotidienne

**Source principale : API Claude avec web_search**
- Chaque matin (6h00), le bot envoie une requête à l'API Claude avec les outils de recherche web activés.
- Prompt : *"Quels sont les 3 faits économiques les plus marquants des dernières 24 heures ? Pour chacun : titre, date, chiffre clé, cause principale, impact pour le grand public."*
- Claude recherche, recroupe et retourne un JSON structuré.
- Les flux RSS (Reuters, AP, BBC, RFI) servent de confirmation et de source secondaire.

```python
# Appel API Claude avec web_search
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    messages=[{
        "role": "user",
        "content": (
            "Aujourd'hui c'est le {date}. "
            "Quels sont les 3 faits économiques les plus marquants "
            "des dernières 24 heures ? "
            "Pour chacun réponds en JSON : "
            "titre, date, chiffre_cle, pourquoi, impact, sources."
        )
    }]
)
```

**Critères de sélection automatique :**
1. Fraîcheur : publié dans les 24 dernières heures.
2. Importance : mots-clés détectés (Fed, BCE, inflation, récession, record, chute, hausse, pétrole, or, emploi…).
3. Impact mesurable : contient au moins un chiffre vérifiable.
4. Potentiel vidéo : peut se raconter en 45 secondes avec accroche + fait + pourquoi + impact.

### Module B — Vérification et sélection

- Recoupement d'au moins **2 sources indépendantes** par fait.
- Recherche de la **source originale** (communiqué officiel, donnée brute).
- Score automatique (0–100) : fraîcheur × importance × impact spectateur.
- Le fait avec le meilleur score est retenu pour la vidéo du jour.

### Module C — Extraction des données et visuels

- Extraction automatique des séries de données historiques liées au sujet (via API publiques : FRED, Eurostat, Banque mondiale, OPEP).
- Génération automatique du graphique Python (Matplotlib/Pillow) en 1080×1920.
- 3 slides minimum : titre accroche / graphique données / conséquences.

### Module D — Production vidéo

1. **Script** : généré par l'API Claude (structure en 5 blocs : accroche → fait → pourquoi → impact → conclusion).
2. **Adaptation** : script adapté (pas traduit mot à mot) en FR, EN, ES.
3. **Voix IA** : Edge-TTS (fr-FR-DeniseNeural / en-US-AriaNeural / es-ES-ElviraNeural) — gratuit, voix naturelles.
4. **Montage** : FFmpeg — slides verticales 1080×1920 + voix + sous-titres synchronisés (WordBoundary Edge-TTS).
5. **Durée cible** : 35–55 secondes.

### Module E — Validation et publication

- **Validation** : envoi de l'aperçu vidéo + script via Telegram (boutons Approuver / Corriger / Rejeter).
- **Publication** : upload YouTube API v3 avec titre, description, hashtags et playlist par langue.
- **Analyse** : mesure des vues, rétention, abonnés à J+2 (délai YouTube Analytics) → feedback sur la sélection des sujets.

---

## 8. Architecture technique

```
youtube_eco/
├── bot.py                  # Point d'entrée — lance le pipeline quotidien
├── config.py               # Clés API, chemins, paramètres
├── db.py                   # SQLite — statuts, historique, analytics
├── pipeline/
│   ├── veille.py           # Module A — API Claude web_search + RSS
│   ├── selection.py        # Module B — scoring, déduplication, vérification
│   ├── donnees.py          # Module C — extraction données publiques
│   ├── visuels.py          # Module C — génération graphiques Matplotlib/Pillow
│   ├── script.py           # Module D — génération script FR/EN/ES via Claude API
│   ├── voix.py             # Module D — Edge-TTS par langue
│   ├── montage.py          # Module D — FFmpeg 1080x1920
│   ├── notif.py            # Module E — Telegram validation
│   └── upload.py           # Module E — YouTube API v3
├── output/
│   ├── visuels/            # PNG slides générés
│   ├── audio/              # MP3 voix par langue
│   └── videos/             # MP4 finaux par langue
└── data/
    └── eco_news.db         # Base SQLite
```

### Stack technique

| Composant | Outil | Coût |
|---|---|---|
| Recherche news | API Claude + web_search | Gratuit (inclus) |
| RSS backup | feedparser | Gratuit |
| Script narratif | API Claude (claude-sonnet-4-6) | ~0,01 $/vidéo |
| Voix IA | Edge-TTS (Microsoft) | Gratuit |
| Visuels | Matplotlib + Pillow | Gratuit |
| Montage | FFmpeg | Gratuit |
| Base de données | SQLite | Gratuit |
| Validation | Telegram Bot API | Gratuit |
| Publication | YouTube Data API v3 | Gratuit (quota 10 000 u/j) |

**Coût total estimé : < 1 $ / jour pour 3 vidéos (FR + EN + ES)**

---

## 9. Objectif économique

- **Revenus publicitaires YouTube** : éligibilité à 1 000 abonnés + 10 M de vues Shorts en 90 jours, ou 4 000 h de visionnage long en 12 mois.
- **Sponsoring et partenariats** quand l'audience le permet.
- **Affiliation et produits numériques** éventuellement.

> ⚠️ Publier dans plusieurs langues ne garantit pas plus de revenus — les résultats dépendent du pays des spectateurs, de leur engagement et de la qualité.

---

## 10. Décisions prises ✅

- ✅ Une seule chaîne YouTube, 3 playlists par langue (FR / EN / ES)
- ✅ Une vidéo par jour — le **fait marquant économique du jour ou de la veille**
- ✅ Structure narrative fixe : Accroche → Fait → **Pourquoi** → **Impact** → Conclusion
- ✅ Source principale de veille : **API Claude avec web_search** (recherche + recoupement automatique)
- ✅ Sources secondaires : RSS Reuters / AP / BBC / RFI en confirmation
- ✅ Voix IA : **Edge-TTS** (gratuit, voix naturelles, 3 langues)
- ✅ Validation humaine : **Telegram** (aperçu + boutons Approuver/Rejeter)
- ✅ Stack 100% gratuite ou quasi-gratuite (< 1 $/jour)
- ✅ Visuels : graphiques recréés en Python (Matplotlib + Pillow), format 1080×1920
- ✅ Montage : FFmpeg local

## 11. Prochaines étapes

- [ ] **Coder `veille.py`** : appel API Claude + web_search → JSON structuré du fait du jour
- [ ] **Coder `script.py`** : génération script 5 blocs en FR/EN/ES via Claude API
- [ ] **Coder `visuels.py`** : templates graphiques dynamiques selon le sujet (cours, inflation, emploi...)
- [ ] **Coder `voix.py`** : Edge-TTS avec WordBoundary pour synchronisation sous-titres
- [ ] **Coder `montage.py`** : pipeline FFmpeg complet avec sous-titres .ASS brûlés
- [ ] **Coder `notif.py`** : Telegram avec aperçu vidéo + boutons validation
- [ ] **Coder `upload.py`** : YouTube API v3 avec titre/description/playlist par langue
- [ ] **Tester** un cycle complet en local (veille → vidéo → validation → upload)
- [ ] **Planifier** l'exécution quotidienne (cron job à 6h00 heure Madagascar)

---

## 12. Calendrier de lancement recommandé

| Semaine | Objectif |
|---|---|
| **S1** | Coder et tester veille.py + script.py (pipeline texte seul) |
| **S2** | Ajouter visuels.py + voix.py + montage.py (première vidéo locale) |
| **S3** | Ajouter notif.py + upload.py — premier upload réel sur YouTube |
| **S4** | 7 vidéos publiées, analyser les résultats, ajuster le pipeline |
| **M2+** | Passer à la cadence quotidienne automatique FR + EN |
| **M3+** | Ajouter la version ES |

> **Règle de lancement :** publier une vidéo par jour pendant 30 jours avant d'analyser les tendances. La régularité est plus importante que la perfection au départ.