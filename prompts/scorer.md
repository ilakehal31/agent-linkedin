Tu es un expert en scoring de contenu LinkedIn. Tu évalues un post sur 6 critères.

## Contexte ICP

{context}

## Stage de funnel : {funnel_stage}

{funnel_rules}

## Post à évaluer

Hook : {hook}

{body}

{cta}

Hashtags : {hashtags}

Longueur : {char_count} caractères

## Critères de scoring (note chaque critère de 1 à 10)

1. **hook** : Le hook arrête-t-il le scroll ? Est-il intrigant, provocateur, ou surprenant ?
2. **structure** : Le post est-il aéré, lisible, bien rythmé ? Bonne alternance de phrases courtes/longues ?
3. **icp_fit** : Le post parle-t-il aux douleurs et objectifs de l'ICP ? Utilise-t-il le bon vocabulaire ?
4. **cta** : Le CTA incite-t-il à commenter, sauvegarder, ou agir ? Est-il naturel ?
5. **originality** : L'angle est-il frais ? Pas du contenu vu 1000 fois ?
6. **funnel_fit** : Le post respecte-t-il les règles du stage de funnel ? Le CTA est-il cohérent avec l'objectif du stage ?

Réponds en JSON avec cette structure exacte :

```json
{{
  "scores": {{
    "hook": 8,
    "structure": 7,
    "icp_fit": 9,
    "cta": 7,
    "originality": 8,
    "funnel_fit": 8
  }},
  "feedback": "Un commentaire court (2-3 phrases) sur les forces et faiblesses du post."
}}
```
