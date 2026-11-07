# Journal — Étape 0 : Validation des sources (12 octobre 2026)

## Objectif
Vérifier que les sources de données (RSS + LLM) fonctionnent **vraiment** sur le serveur avant de coder le pipeline complet.

---

## 1. Test RSS — `test_flux.py`

**Commande :** `python test_flux.py` (via Python 3.11 uv env)

### Résultats

| Flux | Statut | Articles | Plus récent (UTC) | Notes |
|------|--------|----------|-------------------|-------|
| **BBC Business** | ✅ **OK** | 40 | 2026-10-12 06:11 | Tier-1, frais |
| **RFI Économie** | ✅ **OK** | 30 | 2026-10-12 04:45 | Tier-1 FR, frais |
| **Le Monde Économie** | ✅ **OK** | 20 | 2026-10-12 05:45 | Tier-1 FR, frais |
| CNBC Economy | ⚠️ **VIEUX** | 30 | 2026-10-10 12:00 | 2 jours de retard |
| Reuters Business | ❌ **ERR** | — | — | DNS fail (`feeds.reuters.com`) |
| Reuters Markets | ❌ **ERR** | — | — | DNS fail |
| AP Economics | ❌ **ERR** | — | — | DNS fail (`feeds.apnews.com`) |
| AP Business | ❌ **ERR** | — | — | DNS fail |

### Analyse RSS
- **3 flux exploitables** dès maintenant (BBC, RFI, Le Monde) — couvrent EN + FR
- **Reuters/AP** : échec DNS. Causes possibles : URLs changées, blocage géo/IP, firewall. À investiguer plus tard (URLs alternatives : `https://www.reuters.com/arc/outboundfeeds/rss/?outputType=xml` etc.)
- **Suffisant pour démarrer** : 3 sources tier-1 fraîches > 0 source.

---

## 2. Test OpenRouter — `test_openrouter.py`

**Commande :** `python test_openrouter.py` (modèle `anthropic/claude-sonnet-4`)

### Résultats

| Clé (prefix) | Statut | Crédits | Qualité JSON |
|--------------|--------|---------|--------------|
| `sk-or-v1-db83a8...` | ❌ **402** | 0 (jamais acheté) | — |
| `sk-or-v1-7db8a4...` | ✅ **OK** | ✅ | Valide, structure complète |
| `sk-or-v1-56755...` | ✅ **OK** | ✅ | Valide, structure complète |

### Exemple sortie (clé 2) — FR
```json
{
  "titre": "L'or explose à 2 700 $ l'once - Record historique !",
  "blocs": {
    "accroche": "L'or vient de pulvériser tous les records !",
    "fait": "Le 12 octobre 2026, l'or a franchi pour la première fois la barre des 2 700 dollars l'once...",
    "pourquoi": "Cette flambée s'explique par la baisse des taux d'intérêt de la Fed qui rend l'or plus attractif, et surtout par les achats massifs des banques centrales mondiales...",
    "impact": "Pour vous, c'est l'inflation qui grimpe et le pouvoir d'achat qui baisse. À Madagascar, les mines d'or locales voient leurs revenus exploser, mais les bijoux deviennent inabordables pour la population.",
    "conclusion": "Cette ruée vers l'or annonce-t-elle une crise majeure ? Abonnez-vous pour suivre l'évolution des marchés !"
  }
}
```
(+ EN et ES équivalents)

### Analyse OpenRouter
- **2 clés fonctionnelles** sur 3 → redondance OK
- **JSON valide** du premier coup (pas de markdown parasite)
- **Structure respectée** : 3 langues × 5 blocs (accroche, fait, pourquoi, impact, conclusion)
- **Pas d'hallucination** : chiffre unique (2 700 $/oz) respecté
- **Coût estimé** : ~2 500 tokens / appel ≈ 0,003 $ (Claude Sonnet 4 via OR)

---

## 3. Environnement technique validé

| Composant | Version | Statut |
|-----------|---------|--------|
| Python | 3.11.15 (uv) | ✅ |
| feedparser | 6.0.14 | ✅ |
| requests | 2.34.2 | ✅ |
| openai (SDK) | 3.29.0 | ✅ |
| matplotlib | 3.11.0 | ✅ |
| pandas | 3.0.3 | ✅ |
| pillow | 11.3.0 | ✅ |
| edge-tts | 7.2.8 | ✅ (pour Module Voix) |
| moviepy | 2.2.1 | ✅ (pour Module Montage) |
| ffmpeg | (système) | ✅ vérifié |

---

## 4. Fichiers générés

```
D:\Cahine youtube economique\
├── test_flux.py                 # Test RSS
├── test_openrouter.py           # Test LLM
├── test_openrouter_output.json  # Exemple script généré
├── projet_chaine_youtube_shorts_multilingue.md  # Spec v2
├── prototype_short_or/          # Prototype manuel complet
└── JOURNAL_ETAPE_0.md           # Ce fichier
```

---

## 5. Décisions validées pour la suite

| Choix | Validation |
|-------|------------|
| **Sources RSS principales** | BBC Business + RFI Économie + Le Monde Économie |
| **Backup RSS** | CNBC (si maj récent), Reuters/AP à corriger plus tard |
| **LLM principal** | OpenRouter (clé `sk-or-v1-7db8a4...` ou `sk-or-v1-56755...`) |
| **Modèle** | `anthropic/claude-sonnet-4` (ou `claude-3.5-sonnet` si dispo) |
| **Voix** | Edge-TTS (gratuit, 3 langues natives, WordBoundary pour SRT) |
| **Visuels** | Matplotlib + Pillow (1080×1920, charte graphique codée) |
| **Montage** | FFmpeg (slides + audio + SRT brûlé) |
| **Validation humaine** | Telegram Bot (aperçu + boutons) |
| **Publication** | YouTube Data API v3 |

---

## 6. Prochaine action (Étape 1)

**Coder `pipeline/veille.py`** — Version RSS-only (pas de LLM pour la veille, seulement pour le script) :
1. Fetch BBC + RFI + Le Monde
2. Extraction chiffre clé (regex)
3. Scoring mots-clés + fraîcheur + source
4. Déduplication vs SQLite
5. Retour `fact` structuré pour `script.py`

---

## 7. Commandes utiles pour reprendre

```bash
# Activer l'env Python 3.11 uv
cd "D:\Cahine youtube economique"
C:\Users\PLY\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe test_flux.py
C:\Users\PLY\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe test_openrouter.py
```

---

*Journal créé automatiquement le 12 octobre 2026 — Étape 0 validée ✅*