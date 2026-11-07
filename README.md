# PlyChanBot — Automated YouTube Shorts Pipeline

Automated YouTube Shorts and long video pipeline for the PlyChan channel.
Generates 3 Shorts + 3 long videos daily in FR/EN/ES, uploads to YouTube,
publishes Blogger articles, and indexes on Google/Bing.

## Stack
- Python 3.11
- Piper TTS (local text-to-speech)
- FFmpeg (video assembly)
- OpenRouter / Ollama Cloud / Groq / Gemini (LLM)
- YouTube Data API v3
- Blogger API
- Facebook Graph API

## Features
- Multi-language: French, English, Spanish
- Automated veille (RSS feeds) → selection → script → packaging → visuels → voix → montage → upload
- Blogger articles with rich HTML (analysis, opinion, AI section, CTA)
- Google Indexing + IndexNow (Bing/DuckDuckGo/Yahoo/Ecosia)
- Facebook page publication
- Promotion agent (YouTube comments, Reddit search, Twitter search)
- Watchdog with auto-restart
- Sync uploads (idempotent, current day only)

## Setup
1. Install Python 3.11 + FFmpeg + Piper TTS
2. `pip install -r requirements.txt`
3. Copy API keys to `config.py`
4. Place `client_secrets.json` in `config/` and `client_secret.json` in root
5. Run `python bot.py`

## Usage
```bash
python bot.py                    # Full pipeline (Shorts + longs)
python bot.py --short-only       # Shorts only
python bot.py --long-only        # Long video only
python sync_uploads.py           # Upload missing videos
python publish_pending.py        # Publish missing Blogger/Facebook
python promotion_agent.py        # Promote channel
python watchdog.py               # Auto-restart with retries
```

## Cost
Target: < $1/day (Ollama Cloud free, Groq free, Gemini free, OpenRouter ~$0.10/day)

## License
Private project.
PYEOF
echo "Created README.md"