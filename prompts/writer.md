Tu dois générer exactement {num_posts} posts LinkedIn sur le sujet : "{topic}"

## Contexte complet

{context}

## Formats disponibles

{formats}

## Brief de recherche (données fraîches)

{research_brief}

## Posts récents (à ne PAS répéter)

{recent_posts}

## Consignes

1. Génère {num_posts} posts, chacun dans un FORMAT DIFFÉRENT parmi les formats disponibles
2. Chaque post doit respecter le ton, le style et les contraintes du contexte
3. Si un stage de funnel est spécifié, adapte la profondeur, le CTA et la longueur en conséquence
4. Utilise les données de recherche quand elles sont pertinentes (chiffres, tendances, faits)
5. Ne répète pas les angles ou hooks des posts récents
6. Chaque post doit pouvoir être publié tel quel sur LinkedIn

Réponds en JSON avec cette structure exacte :

```json
{{
  "posts": [
    {{
      "format": "Nom du format utilisé",
      "pillar": "Nom du pilier thématique",
      "hook": "La première ligne du post (le hook)",
      "body": "Le corps complet du post (sans le hook, sans le CTA, sans les hashtags)",
      "cta": "La question ou appel à l'action de fin",
      "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
    }}
  ]
}}
```

IMPORTANT :
- Le champ "hook" contient UNIQUEMENT la première ligne
- Le champ "body" contient le corps SANS le hook et SANS le CTA
- Le champ "cta" contient UNIQUEMENT la dernière phrase (question ou action)
- Les hashtags sont séparés du corps du post
- Respecte la longueur cible pour l'ensemble hook + body + cta
