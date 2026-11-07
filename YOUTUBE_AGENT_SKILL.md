# YouTube Agent Skill — installé dans OpenCode

## Ce que j'ai fait

J'ai installé le pack **youtube-agent-skill** (repo GitHub de Jake Schincariol, MIT, gratuit) dans ton environnement OpenCode, pour ta chaîne YouTube économique/shorts.

### Installé
- **11 skills** dans `~/.agents/skills/` : `yt-script`, `yt-package`, `yt-edit`, `yt-comment`, `yt-plan`, `yt-viral`, `yt-retention`, `yt-shorts`, `yt-seo`, `yt-chapters`, `yt-audit`.
- **11 commandes slash** dans `~/.config/opencode/commands/` : `/yt-script`, `/yt-package`, etc.
- **6 outils Python** (sans dépendance) présents dans chaque dossier de skill et testés : `hookscore.py`, `title.py`, `deadair.py`, `chapters.py`, `retention.py`, `swipe.py`.
- Template de voix copié dans `~/.claude/youtube/voice.template.md`.

### Vérifications faites
- `python3` disponible (3.13) — les scripts tournent.
- `hookscore.py` et `title.py` exécutés avec succès.
- Un skill (`yt-script`) chargé via l'outil `skill` d'OpenCode : OK, chemins et fichiers annexes bien résolus.

## À quoi ça sert

C'est un **assistant de production YouTube** qui couvre tout le flux d'une chaîne, de l'idée au diagnostic, **sans jamais publier à ta place**.

| Commande | Fonction |
|---|---|
| `/yt-script` | Idée → 5 hooks scorés (sur 21 formules) + script parlé avec beats de rétention |
| `/yt-package` | Titre + miniature comme une seule paire, lintés |
| `/yt-edit` | Transcript → liste de montage (silences, remplisseurs, retakes, timecodes) |
| `/yt-comment` | Triage des commentaires + réponses dans ta voix |
| `/yt-plan` | Plan semaine adapté à ta capacité réelle |
| `/yt-viral` | Ce qui marche dans ta niche, par multiple vs médiane de chaîne |
| `/yt-retention` | Lecture de l'export Studio : où les viewers partent et pourquoi |
| `/yt-shorts` | Shorts déjà cachés dans une longue vidéo |
| `/yt-seo` | Description, tags utiles, 3 requêtes à gagner |
| `/yt-chapters` | Chapitres validés selon les règles YouTube |
| `/yt-audit` | Audit complet → **un seul fix prioritaire** |

## Comment l'utiliser sur ce projet

- Invoquer un skill : `/yt-script`, ou `@yt-script`, ou laisser le modèle l'auto-invoquer selon la description.
- Remplir `~/.claude/youtube/voice.template.md` → renommer en `voice.md` (ou laisser le skill le créer à partir de 3 de tes vidéos). C'est le fichier le plus important : tout le pack s'adapte à ta voix.
- Les scripts Python se lancent depuis le dossier du skill (le chemin de base est fourni par OpenCode au chargement).

## Limites à connaître

- **Rien ne se publie automatiquement** — chaque sortie finit par un bloc à copier + « ship it, or change it ? ».
- `hookscore.py` est une heuristique, pas un prédicteur.
- `/yt-viral` lit des listings publics uniquement (pas de login, pas de credentials).
- Tags : le pack dit clairement qu'ils comptent peu.

## Fichiers liés

- Source clonée : `C:/Users/PLY/AppData/Local/Temp/opencode/yt-agent/`
- Skills installés : `C:/Users/PLY/.agents/skills/yt-*`
- Commandes : `C:/Users/PLY/.config/opencode/commands/yt-*.md`
- Profil de voix : `C:/Users/PLY/.claude/youtube/voice.template.md`