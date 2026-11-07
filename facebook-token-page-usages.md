# Token de page Facebook : à quoi il sert

Ce token (permission `pages_manage_posts`) permet à PlyChanBot d'agir sur la page **Plychaneco** comme un administrateur.

## Ce que le bot pourra faire

- **Publier du texte avec un lien** : l'article du blog est partagé automatiquement dès qu'il est indexé.
- **Publier des photos** (image à la une de l'article).
- **Publier des vidéos** classiques sur la page.
- **Publier des Reels** (vidéos verticales 9:16), le format le plus utile pour la portée organique. L'envoi se fait en 3 phases (démarrer, envoyer, finaliser).
- **Lire les commentaires et les statistiques** de la page (`pages_read_engagement`), pour répondre ou suivre les performances.

## Configuration (.env)

```
FACEBOOK_PAGE_ID=1389261604274221
FACEBOOK_PAGE_TOKEN=le_token_de_page
```

Ne jamais versionner ce fichier : ajoute `.env` au `.gitignore`.

## Publier une vidéo (exemple Python)

```python
import os, requests

GRAPH = "https://graph.facebook.com/v21.0"
PAGE_ID = os.environ["FACEBOOK_PAGE_ID"]
PAGE_TOKEN = os.environ["FACEBOOK_PAGE_TOKEN"]


def publier_video(chemin_mp4, description):
    with open(chemin_mp4, "rb") as f:
        r = requests.post(
            f"{GRAPH}/{PAGE_ID}/videos",
            data={"description": description, "access_token": PAGE_TOKEN},
            files={"source": f},
            timeout=600,
        )
    r.raise_for_status()
    return r.json()["id"]
```

Cet exemple convient pour des fichiers de taille modérée. Pour de gros fichiers ou pour les Reels, il faut passer par l'envoi en plusieurs phases (`/{PAGE_ID}/video_reels`).

## Points à vérifier

- Les Reels ont des contraintes de format et de durée qui évoluent : vérifier les specs actuelles de Meta avant d'automatiser.
- Instagram (Reels inclus) utilise un autre jeu de permissions et un compte Instagram professionnel lié à la page.
- Tant que l'app est en mode développement, tout fonctionne sur ta propre page, ce qui suffit pour le bot.

## Idée : un même fichier, plusieurs plateformes

Les Shorts produits avec FFmpeg (projet de bot YouTube) peuvent partir sur YouTube, Facebook et Instagram à partir du même fichier vidéo.

## Prochaines étapes

1. Vérifier le token de page dans le débogueur (type **Page**, expiration **Jamais**).
2. Intégrer le module de publication des articles (flux Blogger vers la page).
3. Ajouter le module vidéo / Reels.
4. Ajouter Instagram (compte professionnel lié + permissions dédiées).
