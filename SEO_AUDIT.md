# Audit SEO — PlyChanBot (Chaine YouTube Economique)

## 1. Problèmes identifiés

### Titres YouTube
- **Encodage** : `�?"` au lieu de `—` (em dash) dans les titres
- **Longueur** : titres trop longs (> 100 chars), coupés sur mobile
- **Mots-clés** : titres génériques, pas de termes de recherche spécifiques
- **Format** : `IA & EMPLOI 5,5 % ce 6 novembre 2026 — Les métiers qui changent 🔥 #shorts`
  - Le `#shorts` est redondant (YouTube le détecte automatiquement)
  - La date dans le titre n'aide pas au SEO long terme
  - Le pourcentage `5,5 %` n'est pas un mot-clé recherché

### Tags YouTube
- Liste statique de termes économiques génériques
- Pas de termes spécifiques au sujet (ex: "midterms", "Wall Street", "automatisation")
- Pas de tags longue traîne (long-tail keywords)
- Maximum 15 tags, mais souvent moins de 10

### Descriptions YouTube
- Simple concaténation des blocs du script
- Pas de structure (pas de chapitres, pas de liens)
- Pas de mots-clés dans les 2 premières lignes (seul ce qui est visible avant "Voir plus")
- Pas de call-to-action SEO (abonnement, playlist)

### Articles Blogger
- Pas de balises meta (description, keywords)
- Pas de données structurées (Schema.org)
- Pas de liens internes entre articles
- Pas de sitemap
- URLs par défaut de Blogger (pas optimisées)

### Vidéos longues
- Pas de chapitres (timestamps) dans la description
- Pas de tags spécifiques
- Pas de playlist optimisée

## 2. Recommandations

### Titres
- Format court et percutant : `[SUJET] : [CONSÉQUENCE]`
- Exemple : `IA et emploi : les métiers qui disparaissent` (42 chars)
- Supprimer la date et `#shorts`
- Utiliser des mots-clés à fort volume de recherche

### Tags
- Ajouter des termes spécifiques au sujet (entités nommées)
- Ajouter des synonymes et variantes
- Utiliser des tags longue traîne (3-4 mots)
- Viser 15 tags pertinents par vidéo

### Descriptions
- Première ligne : résumé en 1 phrase avec le mot-clé principal
- Deuxième ligne : ce que le spectateur va apprendre
- Ajouter des timestamps (chapitres) pour les vidéos longues
- Ajouter des liens (abonnement, playlist, article blog)
- Ajouter des hashtags (3 max)

### Blogger
- Ajouter meta description et meta keywords
- Ajouter Schema.org (Article, VideoObject)
- Créer un sitemap XML
- Optimiser les URLs (slugs courts)

## 3. Plan d'action

### Priorité 1 (impact immédiat)
1. Corriger l'encodage des titres (em dash)
2. Raccourcir les titres (< 60 chars)
3. Améliorer les tags (termes spécifiques + longue traîne)
4. Optimiser les 2 premières lignes de la description

### Priorité 2 (impact moyen)
5. Ajouter des chapitres aux vidéos longues
6. Améliorer les meta tags Blogger
7. Ajouter des données structurées

### Priorité 3 (impact long terme)
8. Créer un sitemap XML
9. Ajouter des liens internes entre articles
10. Optimiser les URLs Blogger

## 4. Mots-clés cibles par langue

### Français (volume de recherche élevé)
- "économie actualité"
- "inflation France"
- "emploi IA"
- "bourse aujourd'hui"
- "or prix"
- "taux intérêt"
- "récession 2026"
- "marché du travail"

### Anglais
- "economy news today"
- "inflation rate"
- "AI jobs"
- "stock market"
- "gold price"
- "interest rates"
- "recession 2026"
- "job market"

### Espagnol
- "noticias economía"
- "inflación"
- "empleo IA"
- "bolsa hoy"
- "precio oro"
- "tasas interés"
- "recesión 2026"
- "mercado laboral"

## 5. Exemples de titres optimisés

### Avant (actuel)
- `IA & EMPLOI 5,5 % ce 6 novembre 2026 — Les métiers qui changent 🔥 #shorts`
- `AI & JOBS 5,5 % November 06, 2026 — The Jobs Changing Now 🔥 #shorts`

### Après (optimisé)
- `IA et emploi : les métiers qui disparaissent` (42 chars)
- `AI jobs : which careers are at risk` (35 chars)
- `IA y empleo : los trabajos que cambian` (38 chars)

## 6. Tags recommandés par vidéo

### Pour un sujet IA & Emploi
FR: ["IA emploi", "automatisation", "métiers avenir", "marché du travail", "intelligence artificielle", "chômage", "reconversion", "compétences", "productivité", "économie numérique", "travail 2026", "emplois futurs", "robotisation", "transformation digitale", "carrière"]
EN: ["AI jobs", "automation", "future of work", "job market", "artificial intelligence", "unemployment", "reskilling", "skills", "productivity", "digital economy", "work 2026", "future jobs", "robotization", "digital transformation", "career"]
ES: ["IA empleo", "automatización", "futuro del trabajo", "mercado laboral", "inteligencia artificial", "desempleo", "reconversión", "habilidades", "productividad", "economía digital", "trabajo 2026", "empleos futuros", "robotización", "transformación digital", "carrera"]
PYEOF
echo "Created SEO_AUDIT.md"