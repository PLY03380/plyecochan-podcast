# Comment lancer le bot YouTube

## Lancement manuel

```cmd
cd /d "D:\Cahine youtube economique"
.venv\Scripts\python.exe bot.py
```

## Lancement via le script bat

Double-cliquer sur `run_bot.bat` ou l'exécuter en cmd :
```cmd
"D:\Cahine youtube economique\run_bot.bat"
```

## Lancement automatique (Task Scheduler)

1. Ouvrir **Planificateur de tâches** (Task Scheduler).
2. **Créer une tâche de base** :
   - Nom : `YouTube Bot Daily`
   - Déclencheur : **Quotidien** à **06:00**
   - Action : **Démarrer un programme** → `D:\Cahine youtube economique\run_bot.bat`
   - Cocher "Exécuter même si l'utilisateur n'est pas connecté"
3. Le bot s'exécute automatiquement chaque jour à 6h.

## Lancement avec watchdog (retries automatiques)

```cmd
cd /d "D:\Cahine youtube economique"
.venv\Scripts\python.exe watchdog.py
```

Le watchdog vérifie si les vidéos du jour sont uploadées et relance le bot si nécessaire (max 5 tentatives, 30 min entre chaque).

## Vérification des uploads manquants

```cmd
cd /d "D:\Cahine youtube economique"
.venv\Scripts\python.exe sync_uploads.py
```

## Durée d'exécution

Le bot prend environ **10-15 minutes** (RSS + LLM + TTS ×3 + montage ×3 + upload ×3).

## Prérequis

- Connexion internet active (RSS, OpenRouter, YouTube API)
- Token OAuth YouTube valide (`~/.youtube_token.pickle`)
- Token Blogger valide (`blogger_token.json`) si publication Blogger activée
- Pas de verrou `bot.lock` (sinon supprimer le fichier et relancer)

## Fichiers importants

| Fichier | Rôle |
|---|---|
| `bot.py` | Orchestrateur principal |
| `run_bot.bat` | Script de lancement pour Task Scheduler |
| `watchdog.py` | Relance automatique avec retries |
| `sync_uploads.py` | Vérification et upload des vidéos manquantes |
| `bot.lock` | Verrou anti-exécution concurrente (supprimer si bloqué) |
| `bot_log.txt` | Log de sortie du bot (créé par run_bot.bat) |
| `AUDIT.md` | Audit technique du projet |
