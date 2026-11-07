"""llm.py — Appel LLM multi-provider avec fallback automatique.

Providers (par ordre de priorite) :
1. Ollama (local, gratuit, pas de rate limit) — llama3.2, qwen2.5-coder
2. Groq (gratuit, 30 RPM, 1000-14400 RPD) — llama-3.3-70b, qwen
3. Google Gemini (gratuit, 5-15 RPM, 1500 RPD) — gemini-2.0-flash
4. OpenRouter (payant, fallback) — gemini-2.5-flash, gpt-4o-mini

Chaque provider est essaye en cas d'echec du precedent.
"""
import os
import logging
import time
from typing import Optional

log = logging.getLogger("llm")

# Configuration des providers
PROVIDERS = [
    {
        "name": "Ollama (cloud)",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "models": ["gpt-oss:20b-cloud", "gpt-oss:120b-cloud"],
        "max_tokens": 8000,
    },
    {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": None,  # utilise config.GROQ_API_KEY
        "models": ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"],
        "max_tokens": 4000,
    },
    {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "models": ["gemini-2.5-flash", "gemini-3.8-flash"],
        "max_tokens": 4000,
    },
    {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": None,  # utilise config.OPENROUTER_KEYS
        "models": ["google/gemini-2.5-flash", "openai/gpt-4o-mini"],
        "max_tokens": 4000,
    },
]


def _get_openrouter_keys() -> list:
    try:
        import config
        return config.OPENROUTER_KEYS
    except Exception:
        return []

def _get_groq_key() -> str:
    try:
        import config
        return getattr(config, "GROQ_API_KEY", "")
    except Exception:
        return ""

def _get_gemini_key() -> str:
    try:
        import config
        return getattr(config, "GEMINI_API_KEY", "")
    except Exception:
        return ""


def call_llm(prompt: str, max_tokens: int = 500, json_mode: bool = False) -> str:
    """Appelle un LLM avec fallback automatique entre providers.

    Retourne le contenu de la reponse (string) ou "" si tout echoue.
    """
    from openai import OpenAI

    for provider in PROVIDERS:
        # Determiner les cles a essayer
        if provider["name"] == "OpenRouter":
            keys = _get_openrouter_keys()
        elif provider["name"] == "Groq":
            key = _get_groq_key()
            if not key:
                continue
            keys = [key]
        elif provider["name"] == "Google Gemini":
            key = _get_gemini_key()
            if not key:
                continue
            keys = [key]
        else:
            key = provider["api_key"]
            if not key:
                continue
            keys = [key]

        for key in keys:
            for model in provider["models"]:
                for attempt in range(2):
                    try:
                        client = OpenAI(
                            base_url=provider["base_url"],
                            api_key=key,
                            timeout=120,
                        )
                        kwargs = {
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.4,
                            "max_tokens": min(max_tokens, provider["max_tokens"]),
                        }
                        if json_mode:
                            kwargs["response_format"] = {"type": "json_object"}

                        resp = client.chat.completions.create(**kwargs)
                        content = resp.choices[0].message.content
                        if content and content.strip():
                            log.info(f"LLM OK via {provider['name']}/{model}")
                            return content.strip()
                    except Exception as e:
                        err_str = str(e)
                        if "402" in err_str or "credit" in err_str.lower():
                            log.warning(f"{provider['name']}: cle epuisee (402)")
                            break  # passer a la cle suivante
                        if "429" in err_str:
                            log.warning(f"{provider['name']}: rate limit (429), attente 10s...")
                            time.sleep(10)
                            continue
                        if "404" in err_str or "not found" in err_str.lower():
                            log.warning(f"{provider['name']}: modele {model} non disponible")
                            break  # passer au modele suivant
                        log.warning(f"{provider['name']}/{model}: {err_str[:80]}")
                        continue
    log.error("Tous les providers LLM ont echoue")
    return ""


def call_llm_json(prompt: str, max_tokens: int = 500) -> dict:
    """Appelle un LLM et parse le JSON de la reponse."""
    import json
    content = call_llm(prompt, max_tokens=max_tokens)
    if not content:
        return {}
    # Nettoyer le contenu
    if "```" in content:
        parts = content.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                content = part
                break
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        content = content[start:end+1]
    content = content.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        log.warning(f"JSON parse error: {e}")
        return {}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Test
    result = call_llm("Dis bonjour en un mot.", max_tokens=10)
    print("Result:", result)
    result_json = call_llm_json('Reponds avec ce JSON: {"test": "ok"}', max_tokens=50)
    print("JSON:", result_json)