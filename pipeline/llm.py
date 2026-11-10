"""llm.py — Appel LLM multi-provider avec fallback automatique.

Providers (par ordre de priorite) :
1. Google Gemini (gratuit, rapide, ~1500 requetes/jour) — gemini-2.5-flash
   [quota 429 epuise = on ignore vite et on passe au suivant]
2. Ollama LOCAL (gratuit, sans cle, sans rate limit) — llama3.2, qwen2.5-coder
   [CPU seul ici (~3 mots/s) : d'ou le timeout long de 600s]
   (les modeles "*-cloud" ne viennent qu'apres : ils passent par Ollama Cloud
    et renvoient 402 si le compte n'a pas de credit)
3. Groq (gratuit, 30 RPM) — qwen, gpt-oss-20b   [actuellement 403 : cle/IP bloquee]
4. OpenRouter (payant, dernier recours) — gemini-2.5-flash, gpt-4o-mini

Chaque provider est essaye en cas d'echec du precedent.
"""
import os
import logging
import time
from typing import Optional

log = logging.getLogger("llm")

# Configuration des providers (ordre = ordre d'essai)
PROVIDERS = [
    {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "models": ["gemini-2.5-flash", "gemini-3.8-flash"],
        "max_tokens": 8000,   # 4000 tronquait le JSON des scripts
        "timeout": 120,
    },
    {
        "name": "Ollama",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        # Modeles LOCAUX d'abord (gratuits, aucune cle requise),
        # ensuite les modeles cloud qui exigent un compte Ollama payant (402 sinon).
        # qwen2.5-coder:7b est volontairement retire : 0.2 mot/s sur CPU (inutilisable).
        "models": ["llama3.2:latest", "qwen2.5-coder:3b",
                   "gpt-oss:20b-cloud", "gpt-oss:120b-cloud"],
        # Plafond local : assez pour 200 mots (~350 tokens) ou un JSON de script,
        # sans risquer de faire tourner le CPU pendant des heures.
        "max_tokens": 1500,
        "timeout": 600,       # CPU seul (~3 mots/s) : un script de 1500 tokens prend ~8 min
    },
    {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": None,  # utilise config.GROQ_API_KEY
        "models": ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"],
        "max_tokens": 4000,
        "timeout": 40,
    },
    {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": None,  # utilise config.OPENROUTER_KEYS
        "models": ["google/gemini-2.5-flash", "openai/gpt-4o-mini"],
        "max_tokens": 4000,
        "timeout": 120,
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

        timeout = provider.get("timeout", 120)
        use_json = json_mode
        skip_provider = False
        for key in keys:
            if skip_provider:
                break
            for model in provider["models"]:
                if skip_provider:
                    break
                for attempt in range(2):
                    try:
                        client = OpenAI(
                            base_url=provider["base_url"],
                            api_key=key,
                            timeout=timeout,
                        )
                        kwargs = {
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.4,
                            "max_tokens": min(max_tokens, provider["max_tokens"]),
                        }
                        if use_json:
                            kwargs["response_format"] = {"type": "json_object"}

                        resp = client.chat.completions.create(**kwargs)
                        content = resp.choices[0].message.content
                        if content and content.strip():
                            log.info(f"LLM OK via {provider['name']}/{model}")
                            return content.strip()
                    except Exception as e:
                        err_str = str(e)
                        low = err_str.lower()
                        if "402" in err_str or "credit" in low:
                            log.warning(f"{provider['name']}: cle epuisee (402), provider ignore")
                            skip_provider = True
                            break
                        if "403" in err_str or "access denied" in low:
                            log.warning(f"{provider['name']}: acces refuse (403), provider ignore")
                            skip_provider = True
                            break
                        if "429" in err_str and "quota" in low:
                            log.warning(f"{provider['name']}: quota journalier epuise (429), provider ignore")
                            skip_provider = True
                            break
                        if "429" in err_str:
                            if attempt == 0:
                                log.warning(f"{provider['name']}: rate limit (429), attente 10s...")
                                time.sleep(10)
                                continue
                            log.warning(f"{provider['name']}: rate limit persistant, provider suivant")
                            skip_provider = True
                            break
                        if "404" in err_str or "not found" in low:
                            log.warning(f"{provider['name']}: modele {model} non disponible")
                            break  # passer au modele suivant
                        if "timed out" in low or "timeout" in low:
                            log.warning(f"{provider['name']}/{model}: timeout ({timeout}s), provider suivant")
                            skip_provider = True
                            break
                        if use_json and ("response_format" in low or "400" in err_str or "422" in err_str):
                            # Certains providers refusent response_format : on retente sans.
                            log.warning(f"{provider['name']}/{model}: json_mode refuse, retry sans response_format")
                            use_json = False
                            continue
                        log.warning(f"{provider['name']}/{model}: {err_str[:80]}")
                        continue
    log.error("Tous les providers LLM ont echoue")
    return ""


def call_llm_json(prompt: str, max_tokens: int = 500) -> dict:
    """Appelle un LLM (json_mode) et parse la reponse JSON.

    json_mode force response_format={"type":"json_object"} : sur Ollama cela
    garantit un JSON valide, sur Gemini cela evite les reponses hors-schema.
    Si un provider refuse response_format, call_llm retente automatiquement sans.
    """
    import json
    content = call_llm(prompt, max_tokens=max_tokens, json_mode=True)
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