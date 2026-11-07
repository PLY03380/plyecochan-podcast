"""script.py — Génère le script 5 blocs (FR/EN/ES) via OpenRouter avec fallback multi-modèles.
Inclut : injection date automatique, règles émotionnelles, prompt enrichi V2."""
import json, logging, random
from datetime import datetime
from pipeline.llm import call_llm_json
import config

log = logging.getLogger("script")

# ─── FORMATAGE DATE MULTILINGUE ────────────────────────────────
def get_date_formattee() -> dict:
    """Retourne la date du jour formatée dans les 3 langues."""
    today = datetime.now()
    mois_fr = ["janvier","février","mars","avril","mai","juin",
               "juillet","août","septembre","octobre","novembre","décembre"]
    mois_es = ["enero","febrero","marzo","abril","mayo","junio",
               "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    return {
        "fr": f"ce {today.day} {mois_fr[today.month-1]} {today.year}",
        "en": today.strftime("%B %d, %Y"),
        "es": f"el {today.day} de {mois_es[today.month-1]} de {today.year}",
        "court": today.strftime("%d/%m/%Y"),
        "iso":   today.strftime("%Y-%m-%d"),
    }

DATE_FMT = get_date_formattee()

# ─── PROMPT ENRICHI V2 — ÉMOTIONNEL + DATE ──────────────────────
PROMPT_TEMPLATE = f"""Tu es rédacteur en chef d'une chaîne YouTube Shorts d'actualités économiques multilingue.
Génère un script pour une vidéo de 40-50 secondes (MAXIMUM 120 mots par langue, tout blocs confondus).

RÈGLE ABSOLUE : chaque script DOIT mentionner la date exacte "{DATE_FMT['fr']}" (FR), "{DATE_FMT['en']}" (EN), "{DATE_FMT['es']}" (ES) dans le bloc FAIT.

FAIT DU JOUR ({DATE_FMT['iso']}) :
- Titre source : {{titre}}
- Chiffre clé : {{chiffre_cle}}
- Résumé source : {{resume}}
- Source : {{source}}

THÈME DU JOUR : {{theme_label}}
ANGLE ÉDITORIAL : {{theme_angle}}
ÉMOTION DOMINANTE À ACTIVER : {{theme_emotion}}

STRUCTURE OBLIGATOIRE (5 blocs, durées indicatives, MAX 120 MOTS AU TOTAL PAR LANGUE) :
1. ACCROCHE (~5s, max 15 mots) : Phrase choc qui arrête le scroll. Chiffre ou fait inattendu.
2. FAIT (~8s, max 25 mots) : Ce qui s'est passé — date exacte, lieu, acteur, chiffre clé.
3. POURQUOI (~12s, max 30 mots) : Causes principales (politique monétaire, décision, crise, marché...).
4. IMPACT (~15s, max 35 mots) : Conséquences CONCRÈTES pour :
   - Le grand public (pouvoir d'achat, crédit, épargne, emploi...)
   - Les marchés / économie mondiale
5. CONCLUSION (~8s, max 15 mots) : Question ouverte + appel à commenter + "Abonnez-vous".

RÈGLE DE LONGUEUR : Chaque bloc doit être COURT et DIRECT. Pas de phrases longues. Pas de répétitions. Le total ne doit JAMAIS dépasser 120 mots par langue.

RÈGLE HOOK (première phrase de l'accroche) :
L'accroche doit utiliser UNE de ces formules (choisir la plus adaptée) :
- The Statistic : un chiffre inattendu + conséquence ("97% des chaînes meurent avant la vidéo 30. Voici ce que font les 3% restants.")
- The Mistake : nommer l'erreur du spectateur ("Votre épargne fond à vue d'œil. Voici pourquoi.")
- Contrarian Flip : rejeter un conseil reçu ("Tout le monde dit d'épargner. Moi je dis : investissez.")
- The Question : poser la question exacte tapée dans la recherche ("Pourquoi l'or monte-t-il quand le dollar baisse ?")
- The Warning : un coût imminent ("Ne touchez pas à votre épargne avant d'avoir lu ça.")
- The List : un ensemble compté ("3 choses que personne ne vous dit sur l'inflation.")
- The Reveal : promettre de montrer quelque chose ("Je vais vous montrer le graphique exact.")
- The Deadline : quelque chose change à une date ("La BCE change ses taux ce jeudi. Voici l'impact.")
L'accroche doit confirmer le titre, ouvrir une question impossible à fermer, et prouver que le payoff existe.

RÈGLE ÉMOTIONNELLE OBLIGATOIRE :
Chaque script doit activer AU MOINS UNE émotion forte :

  PEUR      → Si l'événement menace le pouvoir d'achat, l'épargne ou l'emploi
              → Utiliser : "menace", "dévore", "avant qu'il soit trop tard", "votre épargne"
              → Ex : "Cette décision menace votre épargne — voici comment vous protéger"

  SURPRISE  → Si l'événement est un record, un chiffre inédit ou contre-intuitif
              → Utiliser : "jamais vu", "pour la première fois", "inédit", "record absolu"
              → Ex : "Pour la première fois en 50 ans, l'or franchit ce seuil"

  COLÈRE    → Si l'événement révèle une injustice ou une asymétrie d'information
              → Utiliser : "ce qu'ils ne vous disent pas", "pendant que vous...", "profits records"
              → Ex : "Pendant que votre loyer monte, les banques affichent des profits records"
              → ⚠️ DOSER : max 1 phrase colère par script — rester pédagogique

  FOMO      → Si l'événement crée une fenêtre d'opportunité
              → Utiliser : "ne ratez pas", "la fenêtre est ouverte", "avant la prochaine hausse"
              → Ex : "La Fed vient de baisser ses taux — voici l'opportunité à saisir"

  ESPOIR    → Si l'événement est une bonne nouvelle pour le spectateur
              → Utiliser : "bonne nouvelle", "ça va changer", "enfin", "soulagement"
              → Ex : "Bonne nouvelle : l'inflation recule — voici ce que ça change pour vous"

RÈGLE DE TON :
  ✅ Alarmiste éducatif — "C'est grave, voici pourquoi, voici quoi faire"
  ✅ Révélateur bienveillant — "Vous ne saviez peut-être pas ça, voici la réalité"
  ❌ Catastrophisme pur — "Tout va s'effondrer" (sans solution = rejeté par l'algo)
  ❌ Manipulation — Exagérer des faits non vérifiés pour l'émotion
  ❌ Condescendant — "Les gens ne comprennent pas que..."

RÈGLES STRICTES :
- N'INVENTE AUCUN CHIFFRE. Utilise UNIQUEMENT celui fourni : {{chiffre_cle}}.
- Style : clair, direct, crédible, zéro fluff.
- Pas de "selon X" — affirme le fait vérifié.
- Sortie : JSON VALIDE uniquement. Pas de markdown, pas de texte hors JSON.

FORMAT DE SORTIE :
{{
  "fr": {{
    "titre": "Titre YouTube SEO (max 60 caracteres, mot-cle principal en premier, PAS de #shorts, PAS de date)",
    "blocs": {{
      "accroche": "...",
      "fait": "...",
      "pourquoi": "...",
      "impact": "...",
      "conclusion": "..."
    }}
  }},
  "en": {{
    "titre": "...",
    "blocs": {{
      "hook": "...",
      "fact": "...",
      "why": "...",
      "impact": "...",
      "conclusion": "..."
    }}
  }},
  "es": {{
    "titre": "...",
    "blocs": {{
      "gancho": "...",
      "hecho": "...",
      "por_que": "...",
      "impacto": "...",
      "conclusion": "..."
    }}
  }},
  "titres": {{
    "fr": "Titre FR avec date et emoji et #shorts — max 70 chars",
    "en": "Titre EN avec date et emoji et #shorts — max 70 chars",
    "es": "Titre ES avec date et emoji et #shorts — max 70 chars"
  }},
  "date_publication": "DATE_ISO",
  "hashtags": {{
    "fr": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "en": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "es": ["tag1", "tag2", "tag3", "tag4", "tag5"]
  }}
}}

RAPPELS :
- La date DOIT apparaître dans chaque bloc FAIT (FR: "ce {{date_fr}}...", EN: "on {{date_en}}...", ES: "{{date_es}}...")
- Chiffres vérifiés uniquement — jamais d'approximation
- Ton : pédagogique et accessible, pas alarmiste
- Le titre doit etre COURT (max 60 chars), avec le mot-cle principal en premier. PAS de date, PAS de #shorts. Format: "[MOT-CLE] : [CONSÉQUENCE]" ou "[SUJET] [VERBE] [IMPACT]"
- LONGUEUR : MAXIMUM 120 mots par langue (tout blocs confondus). Chaque phrase doit être courte et directe.
"""

MODELS = [
    "google/gemma-4-31b-it:free",    # GRATUIT - bon modèle Google
    "google/gemma-4-26b-a4b-it:free", # GRATUIT - modèle Google léger
    "openrouter/free",                # GRATUIT - routeur automatique
    "google/gemini-2.5-flash",       # ~$0.075/1M - excellent JSON, très cheap, VALIDÉ
    "openai/gpt-4o-mini",            # ~$0.15/1M - fiable, JSON propre
    "meta-llama/llama-3.1-8b-instruct",  # gratuit - dernier recours
]

def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)

def generer_script(fait: dict) -> dict:
    date_fmt = get_date_formattee()
    from themes import THEMES
    t = THEMES.get(fait.get("theme"), {
        "label": "Actualité économique",
        "angle": "Explication claire et factuelle.",
        "emotion": "surprise",
    })
    # .replace() car le template f-string a déjà converti {{x}} en {x}
    prompt = (PROMPT_TEMPLATE
        .replace("{titre}", fait["titre"])
        .replace("{chiffre_cle}", fait["chiffre_cle"])
        .replace("{resume}", fait["resume"])
        .replace("{source}", fait["source"])
        .replace("{date_fr}", date_fmt["fr"])
        .replace("{date_en}", date_fmt["en"])
        .replace("{date_es}", date_fmt["es"])
        .replace("{theme_label}", t["label"])
        .replace("{theme_angle}", t["angle"])
        .replace("{theme_emotion}", t["emotion"])
        .replace("DATE_ISO", date_fmt["iso"])
    )
    
    last_error = None
    data = call_llm_json(prompt, max_tokens=1500)
    if not data:
        raise RuntimeError("Tous les providers LLM ont echoue")

    # Validation structure
    for lang in ("fr", "en", "es"):
        if lang not in data:
            raise ValueError(f"Langue manquante: {lang}")
        blocs = data[lang].get("blocs", {})
        expected_blocs = {
            "fr": ("accroche", "fait", "pourquoi", "impact", "conclusion"),
            "en": ("hook", "fact", "why", "impact", "conclusion"),
            "es": ("gancho", "hecho", "por_que", "impacto", "conclusion"),
        }
        for bloc in expected_blocs[lang]:
            if bloc not in data[lang].get("blocs", {}):
                raise ValueError(f"{lang}: bloc manquant '{bloc}'")
        if "titre" not in data[lang]:
            raise ValueError(f"{lang}: titre manquant")

    # Injection métadonnées
    data["date_publication"] = DATE_FMT["iso"]
    data["theme"] = fait.get("theme", "generique")
    for lang in ("fr", "en", "es"):
        if "titre" not in data[lang]:
            data[lang]["titre"] = f"Actualité {DATE_FMT['court']} #{lang} #shorts"

    log.info("Script généré OK via LLM multi-provider")
    return data

def generer_script_fallback(fait: dict) -> dict:
    """Génère un script de secours générique avec la date du jour."""
    date_fmt = get_date_formattee()
    fait_with_date = {**fait, "date": date_fmt["fr"], "date_en": date_fmt["en"], "date_es": date_fmt["es"]}
    
    # Templates génériques par type de sujet (fallback intelligent)
    sujet = detect_sujet_fallback(fait)
    tpl = FALLBACK_TEMPLATES.get(sujet, FALLBACK_TEMPLATES["generique"])
    
    data = {}
    for lang in ("fr", "en", "es"):
        tpl_lang = tpl[lang]
        data[lang] = {
            "titre": tpl_lang["titre"].format(**fait_with_date)[:100],
            "blocs": {k: v.format(**fait_with_date) for k, v in tpl_lang["blocs"].items()}
        }
    log.warning("Utilisation FALLBACK local (OpenRouter indisponible) — sujet: %s", sujet)
    return data

def detect_sujet_fallback(fait: dict) -> str:
    """Détecte le type de sujet pour choisir le bon template fallback."""
    import re
    if fait.get("theme") in FALLBACK_TEMPLATES:
        return fait["theme"]
    text = (fait.get("titre", "") + " " + fait.get("resume", "")).lower()
    if any(re.search(rf"\b{re.escape(k)}\b", text) for k in ["or", "gold", "once", "lingot", "prix de l'or"]):
        return "or"
    if any(k in text for k in ["fed", "fed rate", "fomc", "rate cut", "rate hike", "bce", "ecb", "taux directeur"]):
        return "taux"
    if any(k in text for k in ["inflation", "cpi", "pce", "prix", "consommation"]):
        return "inflation"
    if any(k in text for k in ["fmi", "imf", "croissance", "pib", "gdp", "recession", "recession"]):
        return "croissance"
    if any(k in text for k in ["emploi", "unemployment", "nfp", "payroll", "chomage", "jobs"]):
        return "emploi"
    if any(k in text for k in ["petrole", "pétrole", "oil", "brent", "wti", "opep"]):
        return "petrole"
    return "generique"

# ─── FALLBACK TEMPLATES PAR SUJET ──────────────────────────────
FALLBACK_TEMPLATES = {
    "generique": {
        "fr": {
            "titre": "Actualité éco {date} : {chiffre_cle} — Ce qu'il faut savoir #shorts",
            "blocs": {
                "accroche": "Ce chiffre vient de tomber et il change la donne.",
                "fait": "{date}, {titre}. Le chiffre clé : {chiffre_cle}.",
                "pourquoi": "C'est la conséquence de la politique économique actuelle et des tensions sur les marchés.",
                "impact": "Pour vous, cela impacte votre pouvoir d'achat et vos crédits. Pour les marchés, c'est un signal fort.",
                "conclusion": "Qu'en pensez-vous ? Dites-le en commentaire. Abonnez-vous pour l'actu éco quotidienne."
            }
        },
        "en": {
            "titre": "Econ News {date_en}: {chiffre_cle} — What You Need to Know #shorts",
            "blocs": {
                "hook": "This number just dropped and it changes everything.",
                "fact": "{date_en}, {titre}. The key figure: {chiffre_cle}.",
                "why": "This is driven by current monetary policy and market tensions.",
                "impact": "For you, this hits purchasing power and loans. For markets, it's a strong signal.",
                "conclusion": "What do you think? Comment below. Subscribe for daily econ news."
            }
        },
        "es": {
            "titre": "Noticia Eco {date_es}: {chiffre_cle} — Lo Que Debes Saber #shorts",
            "blocs": {
                "gancho": "Esta cifra acaba de salir y lo cambia todo.",
                "hecho": "{date_es}, {titre}. La cifra clave: {chiffre_cle}.",
                "por_que": "Es consecuencia de la política económica actual y tensiones de mercado.",
                "impacto": "Para usted, afecta su poder adquisitivo y créditos. Para los mercados, una señal fuerte.",
                "conclusion": "¿Qué opina? Comente. Suscríbase para noticias económicas diarias."
            }
        },
    },
    "or": {
        "fr": {
            "titre": "L'OR À {chiffre_cle} — Record historique {date} 🔥 #shorts",
            "blocs": {
                "accroche": "L'or vient de pulvériser tous les records !",
                "fait": "{date}, l'or franchit {chiffre_cle} l'once — un seuil jamais atteint.",
                "pourquoi": "Baisse des taux Fed + achats massifs banques centrales (800 t/an). L'or redevient valeur refuge n°1.",
                "impact": "Pour vous : protection contre l'inflation. Pour l'économie : les matières premières restent tendues.",
                "conclusion": "L'or tiendra-t-il ce niveau ? Réponse en commentaire. Abonnez-vous !"
            }
        },
        "en": {
            "titre": "GOLD HITS {chiffre_cle} — ALL-TIME HIGH {date_en} 🔥 #shorts",
            "blocs": {
                "hook": "Gold just shattered every record!",
                "fact": "{date_en}, gold hit {chiffre_cle}/oz — a level never seen before.",
                "why": "Fed rate cuts + massive central bank buying (~800t/yr). Gold is back as #1 safe haven.",
                "impact": "For you: inflation hedge. For the economy: commodities stay tight.",
                "conclusion": "Will gold hold this level? Comment below. Subscribe!"
            }
        },
        "es": {
            "titre": "EL ORO A {chiffre_cle} — RÉCORD HISTÓRICO {date_es} 🔥 #shorts",
            "blocs": {
                "gancho": "¡El oro acaba de pulverizar todos los récords!",
                "hecho": "{date_es}, el oro supera {chiffre_cle} la onza — un nivel nunca visto.",
                "por_que": "Bajada de tipos Fed + compras masivas bancos centrales (~800 t/año). El oro vuelve a ser el refugio #1.",
                "impacto": "Para ti: cobertura contra inflación. Para la economía: las materias primas siguen tensas.",
                "conclusion": "¿Mantendrá el oro este nivel? Comenta. ¡Suscríbete!"
            }
        },
    },
    "taux": {
        "fr": {
            "titre": "TAUX : {chiffre_cle} — Ce que la Fed/BCE vient de décider {date} #shorts",
            "blocs": {
                "accroche": "La banque centrale vient de bouger les taux — voici l'impact direct.",
                "fait": "{date}, la décision : taux à {chiffre_cle}.",
                "pourquoi": "Inflation persistante / croissance molle force la main des banquiers centraux.",
                "impact": "Votre crédit immo, votre épargne, le change : tout bouge. Partout dans le monde, le crédit devient plus cher.",
                "conclusion": "Taux haut = crédit cher. Que faites-vous ? Dites-le en commentaire. Abonnez-vous !"
            }
        },
        "en": {
            "titre": "RATES: {chiffre_cle} — Fed/BCE Decision {date_en} #shorts",
            "blocs": {
                "hook": "Central bank just moved rates — here's the direct impact.",
                "fact": "{date_en}, the decision: rates at {chiffre_cle}.",
                "why": "Sticky inflation / weak growth forced central banks' hand.",
                "impact": "Your mortgage, savings, FX: everything moves. Worldwide, borrowing costs are rising.",
                "conclusion": "High rates = expensive credit. What's your move? Comment below. Subscribe!"
            }
        },
        "es": {
            "titre": "TASAS: {chiffre_cle} — Decisión Fed/BCE {date_es} #shorts",
            "blocs": {
                "gancho": "El banco central mueve los tipos — impacto directo.",
                "hecho": "{date_es}, la decisión: tipos en {chiffre_cle}.",
                "por_que": "Inflación persistente / crecimiento débil fuerza la mano de los banqueros centrales.",
                "impacto": "Tu hipoteca, ahorros, cambio: todo se mueve. En todo el mundo, el crédito se encarece.",
                "conclusion": "Tipos altos = crédito caro. ¿Qué haces? Comenta. ¡Suscríbete!"
            }
        },
    },
    "inflation": {
        "fr": {
            "titre": "INFLATION {chiffre_cle} {date} — Votre pouvoir d'achat en danger 📉 #shorts",
            "blocs": {
                "accroche": "L'inflation grignote votre argent — voici l'ampleur réelle.",
                "fait": "{date}, l'inflation s'établit à {chiffre_cle}.",
                "pourquoi": "Énergie + alimentaire + salaires = cercle vicieux. Banques centrales en alerte.",
                "impact": "Vos courses, votre loyer, votre crédit coûtent plus cher. Partout dans le monde, le pouvoir d'achat recule.",
                "conclusion": "Comment protégez-vous votre épargne ? Dites-le en commentaire. Abonnez-vous !"
            }
        },
        "en": {
            "titre": "INFLATION {chiffre_cle} {date_en} — Your Purchasing Power at Risk 📉 #shorts",
            "blocs": {
                "hook": "Inflation eats your money — here's the real damage.",
                "fact": "{date_en}, inflation stands at {chiffre_cle}.",
                "why": "Energy + food + wages = vicious cycle. Central banks on high alert.",
                "impact": "Your groceries, rent, mortgage cost more. Worldwide, purchasing power is shrinking.",
                "conclusion": "How do you protect your savings? Comment below. Subscribe!"
            }
        },
        "es": {
            "titre": "INFLACIÓN {chiffre_cle} {date_es} — Su Poder Adquisitivo en Riesgo 📉 #shorts",
            "blocs": {
                "gancho": "La inflación devora su dinero — aquí el daño real.",
                "hecho": "{date_es}, la inflación se sitúa en {chiffre_cle}.",
                "por_que": "Energía + alimentos + salarios = círculo vicioso. Bancos centrales en alerta.",
                "impacto": "Sus compras, alquiler, hipoteca cuestan más. En todo el mundo, el poder adquisitivo cae.",
                "conclusion": "¿Cómo protege sus ahorros? Comente. ¡Suscríbase!"
            }
        },
    },
    "croissance": {
        "fr": {
            "titre": "CROISSANCE FRANCE {chiffre_cle} {date} — Le FMI tire la sonnette d'alarme 📉 #shorts",
            "blocs": {
                "accroche": "La France ralentit brutalement — le FMI révise tout à la baisse.",
                "fait": "{date}, le FMI prévoit une croissance France à {chiffre_cle} en 2026 (vs 0,9% en 2025).",
                "pourquoi": "Demande faible, investissement frileux, incertitude politique. Zone euro tirée vers le bas.",
                "impact": "Moins d'emplois, salaires sous pression, déficit public qui creuse. L'Europe entière ralentit.",
                "conclusion": "La France peut-elle rebondir ? Votre avis en commentaire. Abonnez-vous !"
            }
        },
        "en": {
            "titre": "FRANCE GROWTH {chiffre_cle} {date_en} — IMF Sounds Alarm 📉 #shorts",
            "blocs": {
                "hook": "France slows sharply — IMF slashes forecast.",
                "fact": "{date_en}, IMF projects France growth at {chiffre_cle} in 2026 (vs 0.9% in 2025).",
                "why": "Weak demand, cautious investment, political uncertainty. Eurozone dragged down.",
                "impact": "Fewer jobs, wage pressure, widening deficit. Europe-wide slowdown ahead.",
                "conclusion": "Can France bounce back? Your take in comments. Subscribe!"
            }
        },
        "es": {
            "titre": "CRECIMIENTO FRANCIA {chiffre_cle} {date_es} — FMI Rebaja Pronósticos 📉 #shorts",
            "blocs": {
                "gancho": "Francia frena en seco — el FMI recorta previsiones.",
                "hecho": "{date_es}, el FMI proyecta crecimiento Francia en {chiffre_cle} para 2026 (vs 0,9% en 2025).",
                "por_que": "Demanda débil, inversión cauta, incertidumbre política. Zona euro arrastrada a la baja.",
                "impacto": "Menos empleo, salarios bajo presión, déficit público crece. Europa entera se frena.",
                "conclusion": "¿Puede Francia recuperarse? Tu opinión en comentarios. ¡Suscríbete!"
            }
        },
    },
    "emploi": {
        "fr": {
            "titre": "EMPLOI USA {chiffre_cle} {date} — Choc sur le marché du travail 📊 #shorts",
            "blocs": {
                "accroche": "Le rapport emploi vient de tomber — le chiffre surprend tout le monde.",
                "fait": "{date}, les créations d'emplois US : {chiffre_cle}.",
                "pourquoi": "Secteur privé résilient / ralentissement selon le chiffre. Fed surveille de près.",
                "impact": "Taux Fed, dollar, bourse : tout réagit. Mondialement, l'emploi dicte la trajectoire économique.",
                "conclusion": "Marché du travail solide ou essoufflé ? Votre avis. Abonnez-vous !"
            }
        },
        "en": {
            "titre": "US JOBS {chiffre_cle} {date_en} — Labor Market Shocker 📊 #shorts",
            "blocs": {
                "hook": "Jobs report just dropped — the number shocks everyone.",
                "fact": "{date_en}, US job creation: {chiffre_cle}.",
                "why": "Private sector resilient / slowing depending on number. Fed watching closely.",
                "impact": "Fed rates, dollar, stocks: everything reacts. Globally, jobs drive the economic trajectory.",
                "conclusion": "Strong or slowing labor market? Your take. Subscribe!"
            }
        },
        "es": {
            "titre": "EMPLEO EE.UU. {chiffre_cle} {date_es} — Choque Laboral 📊 #shorts",
            "blocs": {
                "gancho": "El informe de empleo acaba de salir — el número sorprende a todos.",
                "hecho": "{date_es}, creación empleo EE.UU.: {chiffre_cle}.",
                "por_que": "Sector privado resiliente / desaceleración según cifra. Fed vigilante.",
                "impacto": "Tipos Fed, dólar, bolsa: todo reacciona. Globalmente, el empleo marca el rumbo económico.",
                "conclusion": "¿Mercado laboral fuerte o agotado? Tu opinión. ¡Suscríbete!"
            }
        },
    },
    "petrole": {
        "fr": {
            "titre": "PÉTROLE {chiffre_cle} {date} — Hormuz + OPEP = explosion des prix ⛽ #shorts",
            "blocs": {
                "accroche": "Le baril s'envole — la géopolitique dicte le prix à la pompe.",
                "fait": "{date}, le Brent touche {chiffre_cle} le baril.",
                "pourquoi": "Tensions Détroit d'Ormuz + discipline OPEP+ + demande résiliente = tempête parfaite.",
                "impact": "Carburant, chauffage, transport, plastique : tout augmente. Partout dans le monde, la facture énergétique grimpe.",
                "conclusion": "Jusqu'où ira le baril ? Votre pronostic en commentaire. Abonnez-vous !"
            }
        },
        "en": {
            "titre": "OIL {chiffre_cle} {date_en} — Hormuz + OPEC = Price Surge ⛽ #shorts",
            "blocs": {
                "hook": "Oil soars — geopolitics dictates pump prices.",
                "fact": "{date_en}, Brent hits {chiffre_cle}/barrel.",
                "why": "Hormuz tensions + OPEC+ discipline + resilient demand = perfect storm.",
                "impact": "Fuel, heating, transport, plastics: all up. Worldwide, energy bills are soaring.",
                "conclusion": "How high will oil go? Your prediction below. Subscribe!"
            }
        },
        "es": {
            "titre": "PETRÓLEO {chiffre_cle} {date_es} — Ormuz + OPEP = Subida ⛽ #shorts",
            "blocs": {
                "gancho": "El barril se dispara — la geopolítica dicta el precio.",
                "hecho": "{date_es}, el Brent toca {chiffre_cle} el barril.",
                "por_que": "Tensiones Ormuz + disciplina OPEP+ + demanda resiliente = tormenta perfecta.",
                "impacto": "Carburante, calefacción, transporte, plásticos: todo sube. En todo el mundo, la factura energética sube.",
                "conclusion": "¿Hasta dónde llegará el barril? Tu pronóstico. ¡Suscríbete!"
            }
        },
    },
    "immobilier": {
        "fr": {
            "titre": "IMMOBILIER {chiffre_cle} {date} — Ce que ça change pour vous 🏠 #shorts",
            "blocs": {
                "accroche": "Le logement vient de bouger — voici l'impact direct.",
                "fait": "{date}, {titre}. Le chiffre clé : {chiffre_cle}.",
                "pourquoi": "Taux, offre et demande pèsent sur les prix et les loyers.",
                "impact": "Pour vous : accès au crédit, loyer, achat. Pour le marché : un signal sur la suite.",
                "conclusion": "Acheter ou attendre ? Votre avis en commentaire. Abonnez-vous !"
            }
        },
        "en": {
            "titre": "HOUSING {chiffre_cle} {date_en} — What It Means For You 🏠 #shorts",
            "blocs": {
                "hook": "Housing just moved — here's the direct impact.",
                "fact": "{date_en}, {titre}. Key figure: {chiffre_cle}.",
                "why": "Rates, supply and demand are pushing prices and rents.",
                "impact": "For you: credit access, rent, buying. For the market: a signal of what's next.",
                "conclusion": "Buy or wait? Tell us below. Subscribe!"
            }
        },
        "es": {
            "titre": "VIVIENDA {chiffre_cle} {date_es} — Lo Que Cambia Para Ti 🏠 #shorts",
            "blocs": {
                "gancho": "La vivienda acaba de moverse — este es el impacto directo.",
                "hecho": "{date_es}, {titre}. Cifra clave: {chiffre_cle}.",
                "por_que": "Tipos, oferta y demanda presionan precios y alquileres.",
                "impacto": "Para ti: acceso al crédito, alquiler, compra. Para el mercado: una señal de lo que viene.",
                "conclusion": "¿Comprar o esperar? Cuéntanos. ¡Suscríbete!"
            }
        },
    },
    "ia_emploi": {
        "fr": {
            "titre": "IA & EMPLOI {chiffre_cle} {date} — Les métiers qui changent 💼 #shorts",
            "blocs": {
                "accroche": "L'IA transforme le marché du travail — voici ce que ça implique pour vous.",
                "fait": "{date}, {titre}. Chiffre clé : {chiffre_cle}.",
                "pourquoi": "Automatisation, gains de productivité et refonte des compétences accélèrent la transformation.",
                "impact": "Pour vous : certains métiers disparaissent, d'autres émergent. Pour l'économie : productivité et inégalités.",
                "conclusion": "Votre métier est-il menacé ? Dites-le en commentaire. Abonnez-vous !"
            }
        },
        "en": {
            "titre": "AI & JOBS {chiffre_cle} {date_en} — The Jobs Changing Now 💼 #shorts",
            "blocs": {
                "hook": "AI is reshaping the job market — here's what it means for you.",
                "fact": "{date_en}, {titre}. Key figure: {chiffre_cle}.",
                "why": "Automation, productivity gains and skill shifts are accelerating the change.",
                "impact": "For you: some jobs vanish, new ones emerge. For the economy: productivity and inequality.",
                "conclusion": "Is your job at risk? Comment below. Subscribe!"
            }
        },
        "es": {
            "titre": "IA Y EMPLEO {chiffre_cle} {date_es} — Los Trabajos Que Cambian 💼 #shorts",
            "blocs": {
                "gancho": "La IA está transformando el empleo — esto es lo que implica para ti.",
                "hecho": "{date_es}, {titre}. Cifra clave: {chiffre_cle}.",
                "por_que": "Automatización, productividad y cambio de habilidades aceleran la transformación.",
                "impacto": "Para ti: algunos trabajos desaparecen, otros surgen. Para la economía: productividad y desigualdad.",
                "conclusion": "¿Tu trabajo está en riesgo? Comenta. ¡Suscríbete!"
            }
        },
    },
    "bourse": {
        "fr": {
            "titre": "BOURSE {chiffre_cle} {date} — Ce qu'il faut retenir 📈 #shorts",
            "blocs": {
                "accroche": "Les marchés bougent — voici l'essentiel à retenir.",
                "fait": "{date}, {titre}. Chiffre clé : {chiffre_cle}.",
                "pourquoi": "Résultats, politique monétaire et anticipations des investisseurs tirent les cours.",
                "impact": "Pour vous : épargne, assurance-vie, PEA. Pour les marchés : un signal d'orientation.",
                "conclusion": "Placer son argent ou rester à l'écart ? Votre avis en commentaire. Abonnez-vous !"
            }
        },
        "en": {
            "titre": "MARKETS {chiffre_cle} {date_en} — What To Watch 📈 #shorts",
            "blocs": {
                "hook": "Markets are moving — here's what matters.",
                "fact": "{date_en}, {titre}. Key figure: {chiffre_cle}.",
                "why": "Earnings, monetary policy and investor sentiment are driving prices.",
                "impact": "For you: savings, ISAs, portfolios. For markets: a directional signal.",
                "conclusion": "Invest or stay out? Tell us below. Subscribe!"
            }
        },
        "es": {
            "titre": "BOLSA {chiffre_cle} {date_es} — Lo Que Hay Que Ver 📈 #shorts",
            "blocs": {
                "gancho": "Los mercados se mueven — esto es lo importante.",
                "hecho": "{date_es}, {titre}. Cifra clave: {chiffre_cle}.",
                "por_que": "Resultados, política monetaria y sentimiento de los inversores mueven los precios.",
                "impacto": "Para ti: ahorros, planes, carteras. Para los mercados: una señal de dirección.",
                "conclusion": "¿Invertir o quedarse fuera? Cuéntanos. ¡Suscríbete!"
            }
        },
    },
}

def generer_script_safe(fait: dict) -> dict:
    try:
        return generer_script(fait)
    except Exception as e:
        log.error("OpenRouter échoué, fallback: %s", e)
        return generer_script_fallback(fait)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    
    fait_test = {
        "date": "13/10/2026",
        "titre": "Le FMI relève sa prévision de croissance pour la zone euro mais pointe un net décrochage de l'économie française",
        "chiffre_cle": "0,4 %",
        "resume": "Selon les prévisions du Fonds monétaire international publiées mardi 13 octobre, la hausse du PIB de la France ne devrait pas dépasser 0,4 % en 2026 contre 0,9 % en 2025.",
        "source": "lemonde_economie",
    }
    
    script = generer_script_safe(fait_test)
    # Sauvegarder dans un fichier pour éviter les problèmes d'encodage console
    import os
    output_path = os.path.join(os.path.dirname(__file__), "..", "test_script_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
    print(f"Script sauvegardé dans {output_path}")