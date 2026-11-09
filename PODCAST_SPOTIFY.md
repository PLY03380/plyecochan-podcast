# Spotify Podcast — Publication & Automatisation RSS

## Fichiers audio generes
Les fichiers MP3 sont dans `output/podcast/` :
- `YYYY-MM-DD_long_fr.mp3` (audio francais)
- `YYYY-MM-DD_long_en.mp3` (audio anglais)
- `YYYY-MM-DD_long_es.mp3` (audio espagnol)

## Option 1 : RSS.com (Recommande - Distribution automatique)

### Configuration initiale (1 fois)
1. Creer un compte sur https://rss.com (gratuit)
2. Creer un nouveau podcast :
   - Title: `PlyChan Economie`
   - Description: `Analyses economiques quotidiennes en 3 langues`
   - Author: `Rado Tsanta RASOLONJATOVO`
   - Copyright: `© 2026 Rado Tsanta RASOLONJATOVO - PlyChan`
   - Language: `English` (pour cibler l'audience anglophone)
   - Category: `Business > Economics`
3. RSS.com distribue automatiquement sur :
   - Spotify, Apple Podcasts, Google Podcasts, Amazon Music
   - Pocket Casts, Overcast, Castbox, et 15+ autres

### Upload quotidien (manuel)
1. Va sur rss.com → ton podcast → "New Episode"
2. Upload le fichier MP3 depuis `output/podcast/`
3. Remplis le titre et la description
4. Publie

### Upload automatique (API)
RSS.com a une API pour l'upload automatique. A integrer dans `pipeline/podcast.py`.

## Option 2 : Spotify for Creators (Manuel)

### Configuration initiale
1. Va sur https://creators.spotify.com
2. Connecte-toi avec ton compte Spotify
3. Cree un nouveau show
4. Remplis les metadonnees (titre, description, categorie)

### Upload quotidien (manuel)
1. Va dans "Your Episodes" → "Upload"
2. Upload le fichier MP3 depuis `output/podcast/`
3. Remplis le titre et la description
4. Publie

### Distribution sur d'autres plateformes
Spotify for Creators ne distribue PAS automatiquement. Il faut soumettre manuellement :
- Apple Podcasts : podcasters.apple.com
- Amazon Music : podcasters.amazon.com
- Google Podcasts : podcasters.google.com

## Option 3 : Ausha (Distribution automatique payante)

### Configuration
1. Creer un compte sur https://ausha.co
2. Connecter les plateformes (Spotify, Apple, Google, Amazon, etc.)
3. Uploader les MP3
4. Ausha distribue automatiquement sur 20+ plateformes

## Automatisation dans le bot

### Ajouter dans bot.py (apres le montage des videos longues)

```python
# Extraction audio pour podcast
try:
    from pipeline.podcast import extract_audio, generate_rss
    extract_audio(date_str)
    generate_rss(date_str)
    log.info("Podcast: audio extrait + RSS genere")
except Exception as e:
    log.warning("Podcast echoue: %s", e)
```

### Flux RSS genere
- Fichier: `output/podcast/feed.xml`
- Format: RSS 2.0 avec extensions iTunes
- Compatible avec toutes les plateformes de podcast

### Hebergement des fichiers audio
Les fichiers MP3 sont locaux. Pour les distribuer, il faut les heberger sur un serveur public :
1. **GitHub Pages** (gratuit) - uploader les MP3 dans un repo GitHub
2. **Google Drive** (gratuit) - partager les fichiers publiquement
3. **AWS S3 / Cloudflare R2** (payant mais cheap) - pour la production
4. **RSS.com / Ausha** (hebergement inclus) - le plus simple

## Revenus potentiels

| Source | Mois 1-3 | Mois 4-6 | Mois 7-12 |
|--------|----------|----------|-----------|
| Podcast sponsoring | 0$ | 50-200$/mois | 200-500$/mois |
| YouTube AdSense | 0$ | 20-80$/mois | 100-400$/mois |
| Blog Ads | 0$ | 10-30$/mois | 50-200$/mois |
| **Total** | **0$** | **80-310$/mois** | **350-1100$/mois** |

## Commandes

```bash
# Extraire l'audio des videos longues
python pipeline/podcast.py --extract 2026-11-09

# Generer le flux RSS
python pipeline/podcast.py --rss

# Tout le pipeline podcast
python pipeline/podcast.py --all
```

## Fichiers generes

output/podcast/
├── feed.xml                          # Flux RSS podcast
├── 2026-11-09_long_fr.mp3           # Audio francais
├── 2026-11-09_long_en.mp3           # Audio anglais
└── 2026-11-09_long_es.mp3           # Audio espagnol