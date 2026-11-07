# YouTube Shorts Image Downloader - Project Documentation

## Overview
Downloaded **215 images** across 5 categories for YouTube Shorts about economic concepts.

## Files Structure
```
D:\Cahine youtube economique\Slide\
├── download_assets.py          # Main downloader script
├── generate_emotional_svgs.py  # (Legacy - SVG generator, not used)
├── *.csv                       # 5 keyword CSV files
└── images/
    ├── tier1/          37 images  - Crisis/extreme events
    ├── tier2/          50 images  - Central banks, markets, commodities
    ├── tier3/          44 images  - Growth, employment, finance, energy
    ├── trend2026/      25 images  - 2026 trending topics
    └── emotional/      59 images  - Fear, surprise, anger, FOMO, anxiety, relief
```

## CSV Sources (5 files)
| File | Rows | Type | Folder |
|------|------|------|--------|
| tier1_keywords_complete.csv | 38 | Image Libre | tier1/ |
| tier2_keywords_complete.csv | 53 | Image Libre | tier2/ |
| tier3_keywords_complete.csv | 46 | Image Libre | tier3/ |
| trend2026_keywords_complete.csv | 26 | Image Libre | trend2026/ |
| emotional_keywords_complete.csv | 61 | Cartoon SVG → treated as Image Libre | emotional/ |

## Download Script: `download_assets.py`
- **APIs**: Unsplash (primary) + Pixabay (fallback, API key provided)
- **Rate limiting**: 0.3s between requests
- **Skips existing**: Won't re-download files already present
- **Error handling**: Logs misses, continues on failures

## Run Command
```bash
cd "D:\Cahine youtube economique\Slide"
python download_assets.py
```

## Results (Latest Run)
```
✅ tier1:       37/37 downloaded
✅ tier2:       50/52 downloaded (2 failed: malformed search terms in CSV)
✅ tier3:       44/45 downloaded (1 failed: malformed search term)
✅ trend2026:   25/25 downloaded
✅ emotional:   59/60 downloaded (1 failed: "Unprecedented" - too generic)

TOTAL: 215 images, 4 failed
```

## Failed Searches (CSV data issues)
1. `bank of japan, boj,tokyo"` - malformed quotes
2. `german bund bonds germany,https://pixabay.com/...` - URL in search term
3. `artificial intelligence technology,https://unsplash.com/...` - URL in search term
4. `Unprecedented` - too generic for search

## Usage in Bot
```python
import os

ASSETS = {}
for tier in ['tier1', 'tier2', 'tier3', 'trend2026', 'emotional']:
    folder = f'images/{tier}'
    for img in os.listdir(folder):
        concept = img.replace('.jpg', '').replace('.png', '')
        ASSETS[concept] = {
            'file': f'{folder}/{img}',
            'type': 'image',
            'tier': tier
        }
```

## Dependencies
```bash
pip install requests tqdm
```
(Pixabay API key embedded in script: `57829882-141429e0875fac4f38ecfdc6b`)

## Notes
- All images from Unsplash/Pixabay (CC0 - free for commercial use)
- 1080x1920 recommended for YouTube Shorts
- Emotional tier now uses real photos (not SVGs) for visual consistency