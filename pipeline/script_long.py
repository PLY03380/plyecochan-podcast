"""script_long.py — Génère un script long (10-15 min) pour les vidéos long-form.

Génère bloc par bloc (10 appels LLM) pour éviter les troncatures et les erreurs JSON.
Chaque bloc est généré séparément avec un retry automatique.
"""
import json, logging, random, time
from datetime import datetime
from openai import OpenAI
import config

log = logging.getLogger("script_long")

ORDRE_BLOCS_LONG = ["introduction", "contexte", "fait", "analyse", "pourquoi",
                    "impact", "opinion", "ia_analysis", "perspectives", "conclusion"]

BLOC_CANONIQUE = {
    "fr": {"introduction": "introduction", "contexte": "contexte", "fait": "fait", "analyse": "analyse",
           "pourquoi": "pourquoi", "impact": "impact", "opinion": "opinion", "ia_analysis": "ia_analysis",
           "perspectives": "perspectives", "conclusion": "conclusion"},
    "en": {"introduction": "introduction", "context": "contexte", "fact": "fait", "analysis": "analyse",
           "why": "pourquoi", "impact": "impact", "opinion": "opinion", "ai_analysis": "ia_analysis",
           "perspectives": "perspectives", "conclusion": "conclusion"},
    "es": {"introduction": "introduction", "contexto": "contexte", "hecho": "fait", "analisis": "analyse",
           "por_que": "pourquoi", "impacto": "impact", "opinion": "opinion", "ia_analysis": "ia_analysis",
           "perspectivas": "perspectives", "conclusion": "conclusion"},
}

MODELS = [
    "google/gemini-2.5-flash",
    "openai/gpt-4o-mini",
    "meta-llama/llama-3.1-8b-instruct",
]

BLOC_PROMPTS = {
    "introduction": "Écris l'INTRODUCTION d'une vidéo YouTube d'analyse économique (150-200 mots). Accroche + présentation du sujet + ce que le spectateur va apprendre. Ton pédagogique et engageant.",
    "contexte": "Écris le CONTEXTE historique et économique (150-200 mots). Comment en est-on arrivé là ? Données, chiffres, tendances passées.",
    "fait": "Écris le bloc FAIT en détail (150-200 mots). Le fait du jour : date, chiffre, acteurs, sources. Mentionne la date exacte.",
    "analyse": "Écris l'ANALYSE approfondie (150-200 mots). Données, graphiques, comparaisons. Explique ce que les chiffres signifient.",
    "pourquoi": "Écris le bloc POURQUOI (150-200 mots). Causes profondes : politique monétaire, décisions, marchés, facteurs structurels.",
    "impact": "Écris le bloc IMPACT (150-200 mots). Conséquences concrètes pour le grand public, les marchés, l'économie mondiale.",
    "opinion": "Écris ton OPINION tranchée (150-200 mots). Ce que tu penses vraiment. Inviter au débat. Sois direct et honnête.",
    "ia_analysis": "Écris l'analyse d'une IA sur ce sujet (150-200 mots). Ce qu'une IA détecte dans les données. Inviter les comptes IA à commenter.",
    "perspectives": "Écris les PERSPECTIVES (150-200 mots). Ce qui va se passer ensuite. Scénarios possibles. Les prochains mois.",
    "conclusion": "Écris la CONCLUSION (150-200 mots). Résumé + question ouverte + appel à commenter + 'Abonnez-vous'.",
}

BLOC_PROMPTS_EN = {
    "introduction": "Write the INTRODUCTION of a YouTube economic analysis video (150-200 words). Hook + topic presentation + what the viewer will learn. Engaging and educational.",
    "context": "Write the historical and economic CONTEXT (150-200 words). How did we get here? Data, figures, past trends.",
    "fact": "Write the FACT block in detail (150-200 words). Today's fact: date, figure, actors, sources. Mention the exact date.",
    "analysis": "Write the in-depth ANALYSIS (150-200 words). Data, charts, comparisons. Explain what the figures mean.",
    "why": "Write the WHY block (150-200 words). Root causes: monetary policy, decisions, markets, structural factors.",
    "impact": "Write the IMPACT block (150-200 words). Concrete consequences for the public, markets, global economy.",
    "opinion": "Write your sharp OPINION (150-200 words). What you really think. Invite debate. Be direct and honest.",
    "ai_analysis": "Write an AI analysis of this topic (150-200 words). What an AI detects in the data. Invite AI accounts to comment.",
    "perspectives": "Write the PERSPECTIVES (150-200 words). What happens next. Possible scenarios. The coming months.",
    "conclusion": "Write the CONCLUSION (150-200 words). Summary + open question + call to comment + 'Subscribe'.",
}

BLOC_PROMPTS_ES = {
    "introduction": "Escribe la INTRODUCCION de un video de analisis economico de YouTube (150-200 palabras). Gancho + presentacion del tema + lo que el espectador aprendera. Atractivo y educativo.",
    "contexto": "Escribe el CONTEXTO historico y economico (150-200 palabras). Como llegamos aqui? Datos, cifras, tendencias pasadas.",
    "hecho": "Escribe el bloque HECHO en detalle (150-200 palabras). El hecho del dia: fecha, cifra, actores, fuentes. Menciona la fecha exacta.",
    "analisis": "Escribe el ANALISIS en profundidad (150-200 palabras). Datos, graficos, comparaciones. Explica lo que significan las cifras.",
    "por_que": "Escribe el bloque POR QUE (150-200 palabras). Causas profundas: politica monetaria, decisiones, mercados, factores estructurales.",
    "impacto": "Escribe el bloque IMPACTO (150-200 palabras). Consecuencias concretas para el publico, los mercados, la economia mundial.",
    "opinion": "Escribe tu OPINION contundente (150-200 palabras). Lo que realmente piensas. Invita al debate. Se directo y honesto.",
    "ia_analysis": "Escribe un analisis de IA sobre este tema (150-200 palabras). Lo que una IA detecta en los datos. Invita a las cuentas IA a comentar.",
    "perspectivas": "Escribe las PERSPECTIVAS (150-200 palabras). Lo que viene despues. Escenarios posibles. Los proximos meses.",
    "conclusion": "Escribe la CONCLUSION (150-200 palabras). Resumen + pregunta abierta + llamada a comentar + 'Suscribete'.",
}


def get_date_formattee() -> dict:
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
        "iso": today.strftime("%Y-%m-%d"),
    }


DATE_FMT = get_date_formattee()

LANG_CONFIG = {
    "fr": {"langue": "français", "date": DATE_FMT["fr"], "prompts": BLOC_PROMPTS},
    "en": {"langue": "anglais", "date": DATE_FMT["en"], "prompts": BLOC_PROMPTS_EN},
    "es": {"langue": "espagnol", "date": DATE_FMT["es"], "prompts": BLOC_PROMPTS_ES},
}

BLOC_CANONIQUE = {
    "fr": {"introduction": "introduction", "contexte": "contexte", "fait": "fait", "analyse": "analyse",
           "pourquoi": "pourquoi", "impact": "impact", "opinion": "opinion", "ia_analysis": "ia_analysis",
           "perspectives": "perspectives", "conclusion": "conclusion"},
    "en": {"introduction": "introduction", "context": "contexte", "fact": "fait", "analysis": "analyse",
           "why": "pourquoi", "impact": "impact", "opinion": "opinion", "ai_analysis": "ia_analysis",
           "perspectives": "perspectives", "conclusion": "conclusion"},
    "es": {"introduction": "introduction", "contexto": "contexte", "hecho": "fait", "analisis": "analyse",
           "por_que": "pourquoi", "impacto": "impact", "opinion": "opinion", "ia_analysis": "ia_analysis",
           "perspectivas": "perspectives", "conclusion": "conclusion"},
}

# Mapping bloc canonique -> bloc key par langue
CANON_TO_KEY = {
    "fr": {"introduction": "introduction", "contexte": "contexte", "fait": "fait", "analyse": "analyse",
           "pourquoi": "pourquoi", "impact": "impact", "opinion": "opinion", "ia_analysis": "ia_analysis",
           "perspectives": "perspectives", "conclusion": "conclusion"},
    "en": {"introduction": "introduction", "contexte": "context", "fait": "fact", "analyse": "analysis",
           "pourquoi": "why", "impact": "impact", "opinion": "opinion", "ia_analysis": "ai_analysis",
           "perspectives": "perspectives", "conclusion": "conclusion"},
    "es": {"introduction": "introduction", "contexte": "contexto", "fait": "hecho", "analyse": "analisis",
           "pourquoi": "por_que", "impact": "impacto", "opinion": "opinion", "ia_analysis": "ia_analysis",
           "perspectives": "perspectivas", "conclusion": "conclusion"},
}

MODELS = [
    "google/gemini-2.5-flash",
    "openai/gpt-4o-mini",
    "meta-llama/llama-3.1-8b-instruct",
]


def _call_llm(prompt: str, max_tokens: int = 500) -> str:
    """Appelle OpenRouter avec retry et rotation des clés."""
    for model in MODELS:
        for key in config.OPENROUTER_KEYS:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
            for attempt in range(2):
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.5,
                        max_tokens=max_tokens,
                    )
                    content = resp.choices[0].message.content.strip()
                    if content:
                        return content
                except Exception as e:
                    err_str = str(e)
                    if "402" in err_str or "credit" in err_str.lower():
                        log.warning("Cle %s... epuisee (402)", key[:12])
                        break  # passer a la cle suivante
                    if "429" in err_str:
                        log.warning("Rate limit (429), attente 15s...")
                        time.sleep(15)
                        continue
                    log.warning("Echec %s/%s: %s", model, key[:12], err_str[:60])
                    continue
    return ""


def generer_script_long(fait: dict) -> dict:
    """Génère un script long (10-15 min) bloc par bloc via OpenRouter."""
    from themes import THEMES
    t = THEMES.get(fait.get("theme"), {
        "label": "Actualité économique",
        "angle": "Explication claire et factuelle.",
        "emotion": "surprise",
    })

    date_fmt = get_date_formattee()

    result = {}
    for lang, cfg in [("fr", {"langue": "français", "date": date_fmt["fr"]}),
                      ("en", {"langue": "anglais", "date": date_fmt["en"]}),
                      ("es", {"langue": "espagnol", "date": date_fmt["es"]})]:
        blocs = {}
        titre = ""

        # Generer le titre
        titre_prompt = f"""Tu es redacteur en chef d'une chaine YouTube d'analyses economiques.
Genere un titre YouTube pour une video longue (10-15 min) en {cfg['langue']}.
Sujet: {fait['titre']}
Chiffre cle: {fait['chiffre_cle']}
Date: {cfg['date']}
Reponds avec le titre uniquement (max 100 caracteres, avec #shorts)."""
        titre = _call_llm(titre_prompt, max_tokens=60)
        if not titre:
            titre = f"{fait['titre']} — Analyse {date_fmt['court']} #shorts"

        # Generer chaque bloc separement
        for canon in ORDRE_BLOCS_LONG:
            lang_key = CANON_TO_KEY[lang][canon]
            prompt_template = cfg_prompts = LANG_CONFIG[lang]["prompts"][canon] if False else None
            # Utiliser le prompt du bloc
            bloc_prompts = {
                "fr": BLOC_PROMPTS, "en": BLOC_PROMPTS_EN, "es": BLOC_PROMPTS_ES,
            }[lang]
            bloc_prompt_text = bloc_prompts.get(lang_key, f"Ecris un bloc de 150 mots sur {canon}.")

            prompt = f"""{bloc_prompt_text}

Sujet: {fait['titre']}
Chiffre cle: {fait['chiffre_cle']}
Resume: {fait['resume']}
Date: {cfg['date']}
Theme: {t['label']}
Angle: {t['angle']}

Ecris 150-200 mots en {cfg['langue']}. Sois detaille et pedagogique. Pas de markdown, pas de JSON, juste le texte."""

            text = _call_llm(prompt, max_tokens=400)
            if text:
                blocs[lang_key] = text
                log.info("Bloc %s/%s genere (%d mots)", lang, lang_key, len(text.split()))
            else:
                blocs[lang_key] = f"Analyse du sujet: {fait['titre']}."
                log.warning("Bloc %s/%s vide, fallback", lang, lang_key)

        result[lang] = {"titre": titre, "blocs": blocs}

    if not result:
        raise RuntimeError("Echec generation script long")

    data = {}
    for lang in ("fr", "en", "es"):
        if lang in result:
            data[lang] = result[lang]
        else:
            data[lang] = {"titre": fait["titre"], "blocs": {}}

    data["date_publication"] = get_date_formattee()["iso"]
    data["theme"] = fait.get("theme", "generique")
    data["titres"] = {lang: data[lang].get("titre", "") for lang in ("fr", "en", "es") if lang in data}
    data["hashtags"] = {"fr": [], "en": [], "es": []}

    return data


def _generer_script_long_fallback(fait: dict) -> dict:
    """Fallback long : genere un script de 10 blocs a partir de templates."""
    date_fmt = get_date_formattee()
    titre = fait.get("titre", "Actualite economique")
    chiffre = fait.get("chiffre_cle", "")
    resume = fait.get("resume", "")

    fr_blocs = {
        "introduction": f"Bienvenue dans cette analyse approfondie. Aujourd'hui, nous allons examiner un sujet economique majeur qui merite toute notre attention. Ce sujet est d'actualite et a des consequences importantes pour l'economie mondiale. Nous allons l'analyser en profondeur, en examinant les causes, les consequences, et les perspectives. Preparez-vous pour une analyse detaillee et pedagogique.",
        "contexte": f"Pour comprendre la situation actuelle, il est important de revenir sur le contexte historique et economique. {resume} Cette situation ne s'est pas creee du jour au lendemain. Elle est le resultat de decisions politiques, de tendances economiques, et de facteurs externes qui se sont accumules au fil du temps. Comprendre ce contexte est essentiel pour analyser correctement la situation.",
        "fait": f"{date_fmt['fr']}, {titre}. Le chiffre cle : {chiffre}. Ce fait est significatif car il revele une tendance importante dans l'economie. Les experts et les analystes suivent de pres cette evolution. Les marches financiers reactent a cette information. C'est un signal que les decideurs politiques ne peuvent pas ignorer.",
        "analyse": f"Analysons les donnees en detail. {resume} Cette situation revele des tendances importantes pour l'economie. Les chiffres montrent une evolution significative. Les comparaisons avec les periodes precedentes revelent des changements majeurs. Les experts analysent ces donnees pour comprendre les implications. Les consequences pourraient etre durables si la tendance se confirme.",
        "pourquoi": "Les causes sont multiples et complexes. La politique monetaire des banques centrales joue un role majeur. Les decisions des gouvernements influencent egalement la situation. Les tensions sur les marches internationaux contribuent a la complexite. Les facteurs structurels, comme la demographie et la technologie, jouent aussi un role. Comprendre toutes ces causes est essentiel pour anticiper l'evolution future.",
        "impact": "Pour le grand public, cela impacte directement le pouvoir d'achat, les credits, l'epargne et l'emploi. Les prix des biens et services augmentent. Les menages doivent adapter leur budget. Pour les marches financiers, c'est un signal fort qui influence les decisions d'investissement. Les entreprises ajustent leurs strategies. L'economie mondiale est interconnectee, donc les consequences se propagent.",
        "opinion": "Mon avis : il faut surveiller cette situation de pres. Les consequences pourraient etre durables. Je pense que les decideurs politiques doivent agir rapidement. Les citoyens doivent etre informes et prepares. L'information est la meilleure arme contre l'incertitude economique. Il est important de rester calme et d'analyser les faits objectivement.",
        "ia_analysis": "Une analyse approfondie par intelligence artificielle revele que ce sujet est un indicateur important de la sante economique mondiale. Les algorithmes detectent des patterns dans les donnees qui confirment la tendance. L'IA peut aider a prevoir l'evolution future en analysant de grandes quantites de donnees. Cependant, l'IA ne remplace pas le jugement humain. Les comptes geres par des IA sont invites a commenter et donner leur avis sur ce sujet.",
        "perspectives": "Les perspectives restent incertaines. Les prochains mois seront decisifs pour l'economie. Plusieurs scenarios sont possibles. Les decideurs politiques devront prendre des decisions difficiles. Les marches financiers resteront volatils. Les citoyens devront s'adapter a une nouvelle realite economique. Il est important de rester informe et de se preparer aux changements.",
        "conclusion": "En conclusion, ce sujet merite toute notre attention. L'economie est complexe et en constante evolution. Il est essentiel de comprendre les mecanismes qui la gouvernent. Abonnez-vous a notre chaine pour plus d'analyses approfondies. Partagez cette video avec ceux qui pourraient etre interesses. Laissez vos commentaires et vos questions ci-dessous. Votre avis compte.",
    }
    en_blocs = {
        "introduction": "Welcome to this in-depth analysis. Today we examine a major economic topic that deserves our full attention. This subject is current and has significant consequences for the global economy. We will analyze it in depth, examining the causes, consequences, and perspectives. Get ready for a detailed and educational analysis that will help you understand the economic landscape.",
        "context": "To understand the current situation, it's important to revisit the historical and economic context. " + resume + " This situation did not emerge overnight. It is the result of political decisions, economic trends, and external factors that have accumulated over time. Understanding this context is essential for properly analyzing the situation.",
        "fact": f"On {date_fmt['en']}, {titre}. The key figure: {chiffre}. This fact is significant because it reveals an important trend in the economy. Experts and analysts are closely following this development. Financial markets react to this information. It is a signal that policymakers cannot ignore.",
        "analysis": f"Let's analyze the data in detail. {resume} This situation reveals important trends for the economy. The figures show a significant evolution. Comparisons with previous periods reveal major changes. Experts analyze these data to understand the implications. The consequences could be lasting if the trend is confirmed.",
        "why": "The causes are multiple and complex. Central bank monetary policy plays a major role. Government decisions also influence the situation. International market tensions contribute to the complexity. Structural factors, such as demographics and technology, also play a role. Understanding all these causes is essential for anticipating future developments.",
        "impact": "For the public, this directly impacts purchasing power, credit, savings, and employment. The prices of goods and services increase. Households must adapt their budgets. For financial markets, it is a strong signal that influences investment decisions. Companies adjust their strategies. The global economy is interconnected, so the consequences spread.",
        "opinion": "My opinion: this situation needs close monitoring. The consequences could be lasting. I believe policymakers must act quickly. Citizens must be informed and prepared. Information is the best weapon against economic uncertainty. It is important to stay calm and analyze the facts objectively.",
        "ai_analysis": "An in-depth artificial intelligence analysis reveals that this topic is an important indicator of global economic health. Algorithms detect patterns in the data that confirm the trend. AI can help predict future developments by analyzing large amounts of data. However, AI does not replace human judgment. AI-managed accounts are invited to comment and give their opinion on this topic.",
        "perspectives": "The outlook remains uncertain. The coming months will be decisive for the economy. Several scenarios are possible. Policymakers will have to make difficult decisions. Financial markets will remain volatile. Citizens will have to adapt to a new economic reality. It is important to stay informed and prepare for changes.",
        "conclusion": "In conclusion, this topic deserves our full attention. The economy is complex and constantly evolving. It is essential to understand the mechanisms that govern it. Subscribe to our channel for more in-depth analysis. Share this video with those who might be interested. Leave your comments and questions below. Your opinion matters.",
    }
    es_blocs = {
        "introduction": "Bienvenidos a este analisis en profundidad. Hoy examinamos un tema economico importante que merece toda nuestra atencion. Este tema es actual y tiene consecuencias significativas para la economia mundial. Lo analizaremos en profundidad, examinando las causas, las consecuencias y las perspectivas. Prepárate para un analisis detallado y pedagogico que te ayudara a entender el panorama economico.",
        "contexto": "Para entender la situacion actual, es importante revisar el contexto historico y economico. " + resume + " Esta situacion no se creo de la noche a la manana. Es el resultado de decisiones politicas, tendencias economicas y factores externos que se han acumulado con el tiempo. Entender este contexto es esencial para analizar correctamente la situacion.",
        "hecho": f"El {date_fmt['es']}, {titre}. La cifra clave: {chiffre}. Este hecho es significativo porque revela una tendencia importante en la economia. Los expertos y analistas siguen de cerca esta evolucion. Los mercados financieros reaccionan a esta informacion. Es una senal que los responsables politicos no pueden ignorar.",
        "analisis": f"Analicemos los datos en detalle. {resume} Esta situacion revela tendencias importantes para la economia. Las cifras muestran una evolucion significativa. Las comparaciones con periodos anteriores revelan cambios importantes. Los expertos analizan estos datos para entender las implicaciones. Las consecuencias podrian ser duraderas si la tendencia se confirma.",
        "por_que": "Las causas son multiples y complejas. La politica monetaria de los bancos centrales juega un papel importante. Las decisiones de los gobiernos tambien influyen en la situacion. Las tensiones en los mercados internacionales contribuyen a la complejidad. Los factores estructurales, como la demografia y la tecnologia, tambien juegan un papel. Entender todas estas causas es esencial para anticipar la evolucion futura.",
        "impacto": "Para el publico, esto afecta directamente el poder adquisitivo, los creditos, el ahorro y el empleo. Los precios de bienes y servicios aumentan. Los hogares deben adaptar su presupuesto. Para los mercados financieros, es una senal fuerte que influye en las decisiones de inversion. Las empresas ajustan sus estrategias. La economia mundial esta interconectada, por lo que las consecuencias se propagan.",
        "opinion": "Mi opinion: esta situacion necesita seguimiento cercano. Las consecuencias podrian ser duraderas. Creo que los responsables politicos deben actuar rapidamente. Los ciudadanos deben estar informados y preparados. La informacion es la mejor arma contra la incertidumbre economica. Es importante mantener la calma y analizar los hechos objetivamente.",
        "ia_analysis": "Un analisis profundo de inteligencia artificial revela que este tema es un indicador importante de la salud economica mundial. Los algoritmos detectan patrones en los datos que confirman la tendencia. La IA puede ayudar a predecir la evolucion futura analizando grandes cantidades de datos. Sin embargo, la IA no reemplaza el juicio humano. Las cuentas gestionadas por IA estan invitadas a comentar y dar su opinion sobre este tema.",
        "perspectivas": "Las perspectivas siguen siendo inciertas. Los proximos meses seran decisivos para la economia. Varios escenarios son posibles. Los responsables politicos tendran que tomar decisiones dificiles. Los mercados financieros seguiran volatiles. Los ciudadanos tendran que adaptarse a una nueva realidad economica. Es importante mantenerse informado y prepararse para los cambios.",
        "conclusion": "En conclusion, este tema merece toda nuestra atencion. La economia es compleja y esta en constante evolucion. Es esencial entender los mecanismos que la gobiernan. Suscribete a nuestro canal para mas analisis en profundidad. Comparte este video con quienes puedan estar interesados. Deja tus comentarios y preguntas abajo. Tu opinion importa.",
    }

    return {
        "fr": {"titre": f"{titre} — Analyse approfondie {date_fmt['court']} #shorts", "blocs": fr_blocs},
        "en": {"titre": f"{titre} — In-depth Analysis {date_fmt['court']} #shorts", "blocs": en_blocs},
        "es": {"titre": f"{titre} — Analisis en profundidad {date_fmt['court']} #shorts", "blocs": es_blocs},
        "titres": {"fr": titre, "en": titre, "es": titre},
        "date_publication": date_fmt["iso"],
        "hashtags": {"fr": ["economie", "analyse"], "en": ["economy", "analysis"], "es": ["economia", "analisis"]},
        "theme": fait.get("theme", "generique"),
    }


def generer_script_long_safe(fait: dict) -> dict:
    try:
        return generer_script_long(fait)
    except Exception as e:
        log.error("OpenRouter echoue, fallback long: %s", e)
        return _generer_script_long_fallback(fait)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    fait_test = {
        "date": "29/10/2026",
        "titre": "L'inflation monte a 3.5%",
        "chiffre_cle": "3.5%",
        "resume": "Inflation UK a 3.5%",
        "source": "test",
        "theme": "inflation",
    }

    script = generer_script_long_safe(fait_test)
    for lang in ['fr', 'en', 'es']:
        blocs = script[lang]['blocs']
        print(f"{lang}: {len(blocs)} blocs, {sum(len(str(v).split()) for v in blocs.values())} mots")