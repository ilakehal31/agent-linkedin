# LinkedIn Ghost Writer Agent — Plan Technique V2

> Agent IA éditorial LinkedIn — recherche, rédaction, scoring, publication.
> Contexte/ICP interchangeable — pas limité à une niche.
> Stack : OpenRouter (multi-LLM) + Python + Firecrawl + SQLite
> Interface : CLI (Click + Rich)
> Date : Mars 2026

---

## 1. Vision produit

### Ce que fait l'agent

Un assistant éditorial LinkedIn qui :
- **Comprend ton ICP** à partir d'un fichier de contexte (swappable par client/niche)
- **Recherche** les tendances, news et contenus viraux en temps réel (Firecrawl)
- **Génère** plusieurs versions de posts LinkedIn optimisés
- **Score et rank** chaque version sur des critères objectifs
- **Apprend** de tes feedbacks et de tes meilleurs posts
- **Copie dans le presse-papier** — zéro friction entre génération et publication

### Ce qui le rend puissant

- **Contexte swappable** : change de fichier ICP → l'agent s'adapte instantanément
- **Multi-LLM via OpenRouter** : le meilleur modèle pour chaque tâche (pas un seul modèle pour tout)
- **Exemples réels** : tes meilleurs posts servent de référence de style (pas de ChromaDB, juste des fichiers)
- **Recherche intégrée** : s'appuie sur des données fraîches, pas de génération dans le vide
- **Feedback loop** : les posts bien notés enrichissent la mémoire, les mauvais patterns sont évités

---

## 2. Stratégie multi-LLM (OpenRouter)

L'idée : chaque tâche a un modèle optimal. OpenRouter permet de switcher sans changer de SDK.

| Tâche | Modèle | Pourquoi ce modèle |
|-------|--------|-------------------|
| **Rédaction de posts** | `anthropic/claude-sonnet-4-6` | Meilleur en écriture créative structurée, suit les contraintes de style |
| **Scoring** | `anthropic/claude-haiku-4-5` | Rapide, pas cher, suffisant pour évaluer sur des critères définis |
| **Synthèse recherche** | `anthropic/claude-sonnet-4-6` | Bon pour extraire l'essentiel de longs contenus |
| **Génération de queries** | `anthropic/claude-haiku-4-5` | Tâche simple, pas besoin d'un gros modèle |
| **Suggestions de topics** | `google/gemini-2.5-flash` | Rapide, créatif pour le brainstorming, très bon en français |

Chaque modèle est configurable dans `config.yaml`. Tu peux tester et swapper à volonté.

```yaml
# config.yaml — section modèles
openrouter:
  models:
    writer: "anthropic/claude-sonnet-4-6"
    scorer: "anthropic/claude-haiku-4-5"
    research_synth: "anthropic/claude-sonnet-4-6"
    query_gen: "anthropic/claude-haiku-4-5"
    suggest: "google/gemini-2.5-flash"
```

**Coût estimé** : ~0.02-0.05$ par session `generate` (recherche + 3 posts + scoring). Soit 1-2€/mois pour un usage quotidien.

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    LINKEDIN GHOST WRITER                          │
│                                                                   │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │                CLI (Click + Rich)                        │    │
│   │  generate | quick | suggest | feedback | history         │    │
│   └────────────────────────┬────────────────────────────────┘    │
│                             ▼                                     │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │                   ORCHESTRATOR                            │    │
│   │  Contexte → Research → Write → Score → Clipboard          │    │
│   └────┬──────────┬──────────┬──────────┬───────────────────┘    │
│        ▼          ▼          ▼          ▼                         │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│   │ MEMORY  │ │RESEARCH │ │ WRITER  │ │ SCORER  │              │
│   │         │ │         │ │         │ │         │              │
│   │ Loader: │ │Firecrawl│ │Sonnet   │ │Haiku    │              │
│   │ - YAML  │ │/search  │ │4.6      │ │4.5      │              │
│   │ - Ex.   │ │/scrape  │ │         │ │         │              │
│   │ - SQLite│ │         │ │3 vers.  │ │5 crit.  │              │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘              │
│                                                                   │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │              LLM CLIENT (OpenRouter)                      │    │
│   │  openai SDK → api.openrouter.ai → Claude/Gemini/etc.     │    │
│   └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│   ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐    │
│   │          UNIPILE (V1.5 — post + analytics)              │    │
│   │  Publish → LinkedIn    Stats → feedback auto             │    │
│   └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Structure du projet

```
linkedin-agent/
│
├── main.py                         # Entry point CLI (Click + Rich)
├── config.yaml                     # Settings (modèles, paramètres)
├── requirements.txt
├── .env                            # API keys (pas commité)
│
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py             # Pipeline principal
│   ├── llm.py                      # Client OpenRouter (multi-modèle)
│   ├── researcher.py               # Recherche web (Firecrawl)
│   ├── writer.py                   # Génération de posts
│   └── scorer.py                   # Scoring + ranking
│
├── memory/
│   ├── __init__.py
│   ├── loader.py                   # Charge et fusionne contexte + exemples
│   ├── history.py                  # SQLite — posts + feedback + cache recherche
│   └── contexts/
│       ├── _template/              # Template vide à dupliquer
│       │   ├── icp.yaml
│       │   ├── voice.yaml
│       │   ├── templates.yaml
│       │   ├── pillars.yaml
│       │   ├── funnel.yaml
│       │   └── examples/           # Posts de référence (fichiers .txt)
│       │       └── README.txt      # "Colle tes meilleurs posts ici, 1 par fichier"
│       └── hyring-agency/          # Premier contexte réel
│           ├── icp.yaml
│           ├── voice.yaml
│           ├── templates.yaml
│           ├── pillars.yaml
│           ├── funnel.yaml
│           └── examples/
│               ├── post-recrutement-ia.txt
│               └── post-automatisation.txt
│
├── prompts/
│   ├── system.md                   # System prompt (injecte le contexte)
│   ├── writer.md                   # Prompt génération
│   ├── scorer.md                   # Prompt scoring
│   ├── research.md                 # Prompt synthèse recherche
│   └── suggest.md                  # Prompt suggestion de topics
│
└── output/                         # Posts générés (archive markdown)
    └── hyring-agency/
        └── 2026-03-03_automatisation.md
```

---

## 5. Le système de contexte interchangeable

### Principe

Chaque sous-dossier dans `memory/contexts/` = un client/niche. Même structure, 4 fichiers YAML + un dossier d'exemples. Switch instantané via `--context`.

```bash
python main.py generate --context hyring-agency --topic "automatisation"
python main.py generate --context coach-fitness --topic "transformation"
python main.py generate --context saas-fintech --topic "levée de fonds"
```

### Fichiers de contexte

#### `icp.yaml` — Profil ICP

```yaml
name: "Hyring Agency"
description: "Cabinet de recrutement tech-forward à Dubai et Paris"

persona:
  titre: "Directeur de cabinet de recrutement"
  secteur: "Recrutement / RH"
  taille_entreprise: "5-50 employés"
  localisation: "France / MENA"
  age_range: "30-50 ans"
  niveau_tech: "Moyen — utilise LinkedIn, ATS, mais pas dev"

douleurs:
  - "Passe 80% de son temps sur des tâches répétitives"
  - "Manque de candidats qualifiés"
  - "Clients impatients, délais de recrutement trop longs"
  - "Difficulté à se différencier des autres cabinets"

objectifs:
  - "Automatiser le screening et le tri de CVs"
  - "Réduire le time-to-hire"
  - "Se positionner comme innovant"
  - "Scaler sans recruter"

objections:
  - "C'est trop cher pour mon cabinet"
  - "L'IA va remplacer mes recruteurs"
  - "Je n'ai pas le temps d'implémenter ça"
  - "Mes candidats n'aimeront pas parler à un robot"

vocabulaire:
  utilise: ["pipeline", "sourcing", "brief client", "short-list", "closing"]
  evite: ["machine learning", "API", "cloud native", "disruptif"]

linkedin:
  temps_lecture: "Scroll entre 2 appels, matin et midi"
  reagit_a: ["cas concrets", "chiffres", "avant/après", "controverses métier"]
  ignore: ["contenu trop corporate", "posts trop longs sans hook", "motivation générique"]
```

#### `voice.yaml` — Ton et style

```yaml
tutoiement: false
registre: "professionnel-accessible"
longueur_cible: "800-1300 caractères"

style:
  - "Phrases courtes, percutantes"
  - "Une idée par ligne"
  - "Alterner faits/chiffres et anecdotes"
  - "Finir par une question ou un CTA"

emojis:
  utiliser: true
  frequence: "1-3 par post, jamais dans le hook"
  exemples: ["→", "✅", "📊", "💡"]

interdit:
  - "Pas de hashtags dans le corps du texte"
  - "Pas de 'Je suis ravi de vous annoncer'"
  - "Pas de lien dans le post (mettre en commentaire)"
  - "Pas de texte tout en majuscules"

signature: ""
```

#### `templates.yaml` — Formats LinkedIn

```yaml
formats:
  - name: "Storytelling"
    description: "Histoire personnelle ou client avec une leçon"
    structure: |
      Hook provocateur ou intrigant (1 ligne)
      Contexte rapide (2-3 lignes)
      Le problème / la tension (3-4 lignes)
      Le tournant / la solution (3-4 lignes)
      La leçon / le takeaway (2-3 lignes)
      CTA question ou action
    exemple_hook: "J'ai perdu un client à 15 000€ à cause d'un email."
    performance: "Fort en engagement (commentaires + saves)"

  - name: "How-To / Listicle"
    description: "Liste actionnable de conseils / étapes"
    structure: |
      Hook avec la promesse (1 ligne)
      Contexte court (2 lignes)
      Point 1 — titre + explication (2 lignes)
      Point 2 — titre + explication (2 lignes)
      Point 3 — titre + explication (2 lignes)
      Récap ou takeaway (1-2 lignes)
      CTA
    exemple_hook: "5 automations IA que tout recruteur devrait avoir en 2026 :"
    performance: "Fort en saves et partages"

  - name: "Controversial Take"
    description: "Opinion forte qui divise et génère du débat"
    structure: |
      Affirmation provocante (1 ligne)
      Développement du point de vue (4-6 lignes)
      Nuance / contre-argument anticipé (2-3 lignes)
      Position finale (1-2 lignes)
      Question ouverte au débat
    exemple_hook: "Les cabinets de recrutement qui n'utilisent pas l'IA en 2026 n'existeront plus en 2028."
    performance: "Fort en commentaires et reach"

  - name: "Avant / Après"
    description: "Montrer une transformation concrète"
    structure: |
      Hook avec le résultat (1 ligne)
      AVANT : situation initiale (3-4 lignes)
      Ce qui a changé (2-3 lignes)
      APRÈS : résultats concrets avec chiffres (3-4 lignes)
      Leçon + CTA
    exemple_hook: "Il y a 6 mois, il passait 6h/jour à trier des CVs. Aujourd'hui : 20 minutes."
    performance: "Fort en crédibilité et conversion"

  - name: "Chiffres / Data"
    description: "Post basé sur des données et statistiques"
    structure: |
      Chiffre choc en hook (1 ligne)
      Source et contexte (2 lignes)
      Ce que ça implique concrètement (3-4 lignes)
      Ce que tu recommandes (2-3 lignes)
      CTA
    exemple_hook: "72% des recruteurs disent manquer de temps. Voici ce que font les 28% restants."
    performance: "Fort en crédibilité et partages"

  - name: "Question / Débat"
    description: "Poser une question qui fait réagir"
    structure: |
      Question principale (1-2 lignes)
      Contexte / pourquoi cette question (3-4 lignes)
      2-3 pistes contradictoires (4-6 lignes)
      "Et vous, qu'en pensez-vous ?"
    exemple_hook: "Faut-il automatiser 100% du recrutement ?"
    performance: "Fort en commentaires et reach organique"
```

#### `pillars.yaml` — Sujets piliers

```yaml
description: "Les thèmes récurrents autour desquels tourne le contenu"

pillars:
  - name: "Expertise métier"
    description: "Montrer la maîtrise du domaine"
    exemples_sujets:
      - "Les erreurs courantes dans le process de recrutement"
      - "Comment bien briefer un recruteur"

  - name: "IA & Automatisation"
    description: "Éduquer sur l'IA appliquée au métier"
    exemples_sujets:
      - "Ce que l'IA peut (et ne peut pas) faire en recrutement"
      - "Les outils IA qui changent le métier"

  - name: "Coulisses & Authenticité"
    description: "Humaniser la marque"
    exemples_sujets:
      - "Notre premier client et ce qu'on a appris"
      - "Un projet qui a foiré et ce qu'on en a tiré"

  - name: "Résultats & Case studies"
    description: "Prouver avec des résultats concrets"
    exemples_sujets:
      - "Comment [client] a réduit son time-to-hire de 60%"
      - "Avant/après d'un pipeline automatisé"

  - name: "Tendances & Veille"
    description: "Se positionner comme veilleur du secteur"
    exemples_sujets:
      - "Les 3 tendances recrutement 2026"
      - "Ce que dit la dernière étude sur l'IA en RH"

  - name: "Mindset & Entrepreneuriat"
    description: "Partager la vision, les valeurs"
    exemples_sujets:
      - "Pourquoi on a lancé cette boîte à 2"
      - "Ce que Dubai nous a appris sur le business"

frequence_recommandee:
  posts_par_semaine: 4
  distribution: "2 expertise + 1 coulisses + 1 tendances (alterner les autres)"
```

#### `examples/` — Posts de référence

Tes meilleurs posts LinkedIn, copiés-collés dans des fichiers `.txt` (1 post par fichier). Le loader les lit et les injecte dans le prompt du writer comme référence de style.

**Pourquoi c'est puissant :** le LLM comprend ton style réel à partir d'exemples concrets. Pas besoin d'embeddings — 5-10 exemples suffisent pour calibrer le ton.

---

## 6. Funnel TOFU / MOFU / BOFU

### Principe

Chaque post LinkedIn a une **intention** dans un funnel. L'agent adapte automatiquement le ton, la profondeur, le CTA et le format selon l'étape du funnel choisie.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FUNNEL LINKEDIN                          │
│                                                                  │
│   TOFU ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  (large)     │
│   Visibilité · Reach · Nouveaux abonnés                         │
│   "Faire découvrir"                                              │
│                                                                  │
│      MOFU ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  (moyen)              │
│      Confiance · Expertise · Engagement                          │
│      "Faire comprendre"                                          │
│                                                                  │
│         BOFU ━━━━━━━━━━━━━━━━━━━━━  (ciblé)                     │
│         Conversion · Leads · Prise de RDV                        │
│         "Faire agir"                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Fichier `funnel.yaml` — ajouté dans chaque contexte

```yaml
# memory/contexts/hyring-agency/funnel.yaml

funnel:
  tofu:
    label: "Awareness — haut de funnel"
    objectif: "Maximiser le reach et attirer de nouveaux abonnés"
    ton: "Accessible, curieux, légèrement provocateur"
    profondeur: "Surface — une idée forte, pas de détails techniques"
    longueur: "600-900 caractères (court, snackable)"
    cta_style: "Question ouverte qui fait réagir ('Et vous ?', 'D'accord ou pas ?')"
    formats_preferes: ["Controversial Take", "Question / Débat", "Chiffres / Data"]
    piliers_preferes: ["Tendances & Veille", "Mindset & Entrepreneuriat"]
    kpis: ["impressions", "nouveaux abonnés", "partages"]
    exemples_hooks:
      - "90% des recruteurs font cette erreur en 2026."
      - "L'IA va-t-elle tuer le recrutement ? Ma réponse va vous surprendre."
      - "Faut-il automatiser 100% du recrutement ?"
    regles:
      - "Pas de mention de service ou offre"
      - "Pas de jargon technique"
      - "Rester généraliste — parler au plus grand nombre"
      - "Hook ultra-court (< 10 mots)"
      - "Favoriser l'émotion et l'opinion"

  mofu:
    label: "Consideration — milieu de funnel"
    objectif: "Démontrer l'expertise et construire la confiance"
    ton: "Expert-accessible, pédagogique, concret"
    profondeur: "Moyenne — montrer le comment, pas juste le quoi"
    longueur: "900-1500 caractères (développé, riche)"
    cta_style: "Inciter à sauvegarder ou commenter avec son expérience ('Sauvegardez ce post', 'Partagez votre méthode')"
    formats_preferes: ["How-To / Listicle", "Avant / Après", "Storytelling"]
    piliers_preferes: ["Expertise métier", "IA & Automatisation", "Résultats & Case studies"]
    kpis: ["saves", "commentaires détaillés", "DMs", "temps de lecture"]
    exemples_hooks:
      - "Voici les 3 étapes que j'utilise pour trier 200 CVs en 15 minutes :"
      - "Il y a 6 mois, on passait 6h/jour sur le sourcing. Voici ce qu'on a changé."
      - "Le framework exact que j'utilise pour qualifier un candidat en 5 min :"
    regles:
      - "Inclure des éléments actionnables (étapes, frameworks, méthodes)"
      - "Utiliser des chiffres concrets et des résultats"
      - "Montrer l'expertise sans vendre"
      - "OK de mentionner son domaine d'activité, pas son offre"
      - "Favoriser les preuves : screenshots, données, avant/après"

  bofu:
    label: "Decision — bas de funnel"
    objectif: "Générer des leads qualifiés et des prises de contact"
    ton: "Direct, confiant, orienté résultat"
    profondeur: "Profonde — cas client détaillé, preuve sociale, résultat chiffré"
    longueur: "1000-1800 caractères (complet, convaincant)"
    cta_style: "Action directe ('Envoyez-moi un DM', 'Lien en commentaire', 'On en parle ? Réservez un créneau')"
    formats_preferes: ["Avant / Après", "Storytelling", "Chiffres / Data"]
    piliers_preferes: ["Résultats & Case studies", "Expertise métier"]
    kpis: ["DMs reçus", "clics lien", "leads générés", "calls bookés"]
    exemples_hooks:
      - "Un cabinet de recrutement a doublé ses placements en 3 mois. Voici comment."
      - "Mon client dépensait 4 000€/mois en sourcing manuel. Aujourd'hui : 0€."
      - "3 résultats concrets qu'on a obtenus pour nos clients ce trimestre :"
    regles:
      - "Toujours inclure un résultat chiffré"
      - "Preuve sociale obligatoire (client, témoignage, data)"
      - "CTA explicite vers une action de conversion"
      - "OK de mentionner son offre/service (subtilement)"
      - "Finir sur l'urgence ou la rareté si pertinent"

# Distribution recommandée par semaine (4 posts)
distribution_hebdo:
  tofu: 2       # 50% — alimenter le reach
  mofu: 1       # 25% — construire l'autorité
  bofu: 1       # 25% — convertir

# Distribution recommandée par semaine (5 posts)
distribution_hebdo_5:
  tofu: 2
  mofu: 2
  bofu: 1
```

### Intégration dans le CLI

```bash
# Spécifier l'étape du funnel
python main.py generate --context hyring-agency --topic "IA recrutement" --funnel tofu
python main.py generate --context hyring-agency --topic "IA recrutement" --funnel mofu
python main.py generate --context hyring-agency --topic "IA recrutement" --funnel bofu

# Auto-funnel : l'agent choisit selon l'historique et la distribution recommandée
python main.py generate --context hyring-agency --topic "IA recrutement"
# → Analyse la distribution des 7 derniers jours
# → Choisit le stage manquant (ex: "Tu as 3 TOFU cette semaine, je passe en MOFU")

# Suggestions filtrées par funnel
python main.py suggest --context hyring-agency --funnel bofu
# → "Voici 5 sujets BOFU pour convertir cette semaine"

# Voir la distribution dans l'historique
python main.py history --context hyring-agency --funnel-stats
# → TOFU: 12 (48%) | MOFU: 8 (32%) | BOFU: 5 (20%) — sur 30 jours
```

### Impact sur les modules existants

**`agent/writer.py`** — Le funnel modifie le prompt :
- Injecte les règles du stage (`funnel.yaml → tofu.regles`)
- Force les formats préférés du stage
- Adapte la longueur cible
- Modifie le style de CTA

**`agent/scorer.py`** — Nouveau critère de scoring :

| Critère | Poids | Ce qu'on évalue |
|---------|-------|-----------------|
| **Funnel Fit** | ×2 | Le post respecte les règles du stage ? Le CTA est cohérent ? |

Le scoring vérifie :
- TOFU : pas de mention de service → OK ✓ / sinon malus -2
- MOFU : contient des éléments actionnables → OK ✓ / sinon malus -1
- BOFU : contient un résultat chiffré + CTA direct → OK ✓ / sinon malus -2

**`memory/history.py`** — Nouvelle colonne dans la table `posts` :

```sql
ALTER TABLE posts ADD COLUMN funnel_stage TEXT; -- "tofu" | "mofu" | "bofu"
```

Permet les requêtes de distribution :
```sql
SELECT funnel_stage, COUNT(*) FROM posts
WHERE context = ? AND created_at > datetime('now', '-7 days')
GROUP BY funnel_stage;
```

**`agent/orchestrator.py`** — Auto-funnel :
```
1. Si --funnel spécifié → utilise ce stage
2. Sinon → requête distribution des 7 derniers jours
3. Compare avec distribution_hebdo recommandée
4. Choisit le stage le plus sous-représenté
5. Affiche : "📊 Auto-funnel : MOFU (0 cette semaine, cible : 1)"
```

### Structure du contexte mise à jour

```
memory/contexts/hyring-agency/
├── icp.yaml
├── voice.yaml
├── templates.yaml
├── pillars.yaml
├── funnel.yaml            # ← NOUVEAU
└── examples/
    ├── tofu/              # ← Organisation optionnelle par stage
    │   └── post-debat-ia.txt
    ├── mofu/
    │   └── post-framework-recrutement.txt
    ├── bofu/
    │   └── post-case-study-client.txt
    └── post-recrutement-ia.txt   # Posts sans stage (rétro-compatible)
```

### Mapping Piliers × Funnel

Les piliers et le funnel sont orthogonaux — on peut combiner n'importe quel pilier avec n'importe quel stage, mais certaines combinaisons sont plus naturelles :

```
                    TOFU          MOFU              BOFU
                    ─────────────────────────────────────
Expertise métier    ●○○           ●●●               ●●○
IA & Auto           ●●○           ●●●               ●●○
Coulisses            ●●●           ●●○               ○○○
Résultats            ○○○           ●●○               ●●●
Tendances            ●●●           ●●○               ○○○
Mindset              ●●●           ●○○               ○○○

●●● = combinaison naturelle
●●○ = fonctionne bien
●○○ = possible mais rare
○○○ = à éviter
```

Le writer utilise cette matrice pour choisir le pilier optimal quand il n'est pas spécifié.

---

## 7. Mémoire — 2 couches (pas 3)

### Couche 1 — Mémoire statique (fichiers)

**Quoi :** Contexte YAML + exemples de posts
**Quand :** Chargée au démarrage de chaque commande
**Swap :** `--context nom-du-dossier`

### Couche 2 — Mémoire persistante (SQLite)

Une seule base `data/history.sqlite` avec 3 tables :

```sql
-- Posts générés
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    context TEXT NOT NULL,          -- "hyring-agency"
    topic TEXT NOT NULL,
    format TEXT NOT NULL,           -- "Storytelling"
    pillar TEXT,                    -- "IA & Automatisation"
    funnel_stage TEXT,              -- "tofu" | "mofu" | "bofu"
    hook TEXT NOT NULL,
    body TEXT NOT NULL,
    cta TEXT,
    hashtags TEXT,                  -- JSON array
    score_total REAL,
    score_details TEXT,             -- JSON {hook: 9, structure: 8, ...}
    char_count INTEGER,
    status TEXT DEFAULT 'draft',    -- draft | published | archived
    user_score INTEGER,             -- 1-10 (feedback)
    user_note TEXT,                 -- feedback libre
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cache recherche (évite de re-chercher le même sujet)
CREATE TABLE research_cache (
    id INTEGER PRIMARY KEY,
    context TEXT NOT NULL,
    query TEXT NOT NULL,
    results TEXT NOT NULL,          -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- TTL géré en code : si > 24h, on re-recherche
);

-- Tracking des prompts (optionnel mais utile)
CREATE TABLE prompt_versions (
    id INTEGER PRIMARY KEY,
    prompt_file TEXT NOT NULL,      -- "writer.md"
    hash TEXT NOT NULL,             -- hash du contenu
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Pas de ChromaDB.** La recherche sémantique est remplacée par :
- `SELECT * FROM posts WHERE context = ? ORDER BY user_score DESC LIMIT 5` → meilleurs posts
- `SELECT * FROM posts WHERE context = ? ORDER BY created_at DESC LIMIT 10` → posts récents (éviter répétitions)
- Le dossier `examples/` pour le style de référence

---

## 8. Modules détaillés

### 8.1 — `agent/llm.py` — Client OpenRouter multi-modèle

Wrapper autour du SDK `openai` pointé sur `https://openrouter.ai/api/v1`.

**Fonctions :**
- `call(messages, model_key, temperature, max_tokens)` → appel LLM, résout le modèle depuis config
- `call_json(messages, model_key, schema)` → appel avec réponse JSON structurée (response_format)
- Retry automatique (3 essais avec backoff)
- Log tokens consommés par appel (print si `--verbose`)

```python
# Usage
response = llm.call(
    messages=[{"role": "user", "content": "..."}],
    model_key="writer",       # → résolu en "anthropic/claude-sonnet-4-6"
    temperature=0.8
)
```

### 8.2 — `agent/researcher.py` — Recherche Firecrawl

**Entrée :** Un topic + le contexte ICP
**Sortie :** Un brief structuré pour le writer

**Workflow :**
1. Vérifie le cache SQLite (TTL 24h). Si frais → retourne le cache.
2. Génère 2-3 queries de recherche via LLM (`query_gen` → Haiku, rapide et cheap)
3. Lance `firecrawl.search()` pour chaque query (endpoint `/search` = recherche + scrape)
4. Synthétise les résultats via LLM (`research_synth` → Sonnet)
5. Cache le résultat en SQLite
6. Retourne un brief : tendances, chiffres clefs, angles potentiels

**Option `--no-cache` :** force une recherche fraîche.
**Option `--no-research` :** skip la recherche (mode quick).

### 8.3 — `agent/writer.py` — Rédaction multi-format

**Entrée :** Topic + brief recherche + contexte complet (ICP, voice, templates, exemples, posts passés)
**Sortie :** 3 versions de post en JSON structuré

**Pour chaque version :**
```json
{
  "format": "Storytelling",
  "hook": "La première ligne du post",
  "body": "Le corps complet du post",
  "cta": "La question/action de fin",
  "hashtags": ["#recrutement", "#IA"],
  "pillar": "IA & Automatisation",
  "char_count": 987
}
```

**Logique :**
1. Sélectionne 3 formats différents (les plus adaptés au topic, ou aléatoire)
2. Charge les posts récents du même contexte (SQLite) → éviter les répétitions
3. Charge les exemples de référence (dossier `examples/`)
4. Injecte tout dans le prompt : ICP + voice + templates + research + exemples + posts récents
5. Génère 3 posts via LLM (`writer` → Sonnet)
6. Valide les contraintes voice (longueur, pas de mots interdits)

**Modèle utilisé :** `anthropic/claude-sonnet-4-6` — meilleur en écriture créative structurée.

### 8.4 — `agent/scorer.py` — Scoring et ranking

**Entrée :** Un post + le contexte ICP
**Sortie :** Score détaillé sur 5 critères

| Critère | Poids | Ce qu'on évalue |
|---------|-------|-----------------|
| **Hook** | ×2 | Arrête le scroll ? Intrigant/provocateur ? |
| **Structure** | ×1 | Aéré, lisible, bien rythmé ? |
| **ICP Fit** | ×2 | Parle aux douleurs/objectifs de l'ICP ? |
| **CTA** | ×1.5 | Incite à commenter, sauvegarder ? |
| **Originalité** | ×1.5 | Angle frais, pas du contenu vu 1000 fois ? |

**Score global** = moyenne pondérée → /10

**Modèle utilisé :** `anthropic/claude-haiku-4-5` — rapide, pas cher. 3 posts × 1 appel chacun = 3 appels.

**Heuristiques complémentaires (déterministes) :**
- Longueur du hook > 2 lignes → malus -1 sur Hook
- Char count hors range voice.yaml → malus -1 sur Structure
- Pas de question ni CTA en fin → malus -1 sur CTA
- Émojis dans le hook (si interdit dans voice) → malus -0.5 sur Structure

Ces malus stabilisent le scoring là où le LLM est inconsistant.

### 8.5 — `agent/orchestrator.py` — Le cerveau

**Workflow `generate` (commande principale) :**
```
1. Charge le contexte (loader.py → YAML + exemples)
2. Charge l'historique récent (SQLite → derniers posts)
3. Recherche (researcher.py → brief avec données fraîches)
4. Rédaction (writer.py → 3 versions)
5. Scoring (scorer.py → score chaque version)
6. Ranking → tri par score décroissant
7. Affichage → Rich panels avec scores
8. Sélection → l'utilisateur choisit, édite ou relance
9. Sauvegarde → SQLite + fichier markdown dans output/
10. Copie dans le presse-papier
```

**Workflow `quick` (post rapide, sans recherche ni scoring) :**
```
1. Charge le contexte
2. Rédaction directe (1 seul post, format au choix ou random)
3. Affichage
4. Copie dans le presse-papier
```

**Workflow `suggest` (idées de sujets) :**
```
1. Charge le contexte + historique des 30 derniers jours
2. Analyse les piliers sous-représentés
3. LLM génère 5 idées de topics (pilier + angle + hook potentiel)
4. L'utilisateur en choisit un → lance generate
```

**Workflow `feedback` :**
```
1. L'utilisateur note un post (1-10) + commentaire libre
2. Sauvegarde en SQLite
3. Si score ≥ 8 → le post est marqué comme "top" (utilisé comme référence future)
4. Si score ≤ 4 → log le pattern à éviter
```

---

## 9. CLI — Commandes

```bash
# Générer 3 posts scorés et choisir le meilleur
python main.py generate --context hyring-agency --topic "automatisation recrutement"
python main.py generate --context hyring-agency --topic "IA recrutement" --funnel tofu
python main.py generate --context hyring-agency           # topic + funnel auto

# Post rapide (1 post, pas de recherche, pas de scoring)
python main.py quick --context hyring-agency --topic "pourquoi l'IA ne remplace pas les recruteurs"
python main.py quick --context hyring-agency --topic "..." --format storytelling

# Suggestions de sujets pour la semaine
python main.py suggest --context hyring-agency

# Feedback après publication
python main.py feedback --post-id 42 --score 8 --note "15K vues, hook très bon"

# Historique
python main.py history --context hyring-agency --last 20
python main.py history --context hyring-agency --best      # top par user_score
python main.py history --context hyring-agency --funnel-stats  # distribution TOFU/MOFU/BOFU

# Créer un nouveau contexte depuis le template
python main.py init-context --name "coach-fitness"

# Options globales
--verbose          # Affiche les tokens consommés et les appels LLM
--no-cache         # Force une recherche fraîche (ignore le cache)
--no-research      # Skip la recherche (utile en mode hors-ligne)
--funnel tofu|mofu|bofu  # Force un stage de funnel (sinon auto)
```

### UX du mode `generate`

```
╭──────────────────────────────────────────────────────────────╮
│  📊 Funnel : MOFU (auto — 0 cette semaine, cible : 1)       │
│  🔍 Recherche : "automatisation recrutement 2026"            │
│  ✅ 8 résultats trouvés — synthèse en cours...               │
╰──────────────────────────────────────────────────────────────╯

╭─ POST 1/3 ──────────────────────── Score: 8.4/10 ───────────╮
│ Format: Avant/Après    Pilier: Résultats & Case studies      │
│ Funnel: MOFU                                                  │
│                                                               │
│ Il y a 3 mois, un cabinet de recrutement passait             │
│ 6h par jour à trier des CVs.                                 │
│                                                               │
│ Aujourd'hui ? 20 minutes.                                    │
│                                                               │
│ [... corps du post ...]                                      │
│                                                               │
│ Et vous, combien de temps passez-vous sur                    │
│ des tâches que l'IA pourrait faire ?                          │
│                                                               │
│  Hook: 9 │ Structure: 8 │ ICP: 9 │ CTA: 7 │ Orig: 8        │
╰──────────────────────────────────────────────────────────────╯

╭─ POST 2/3 ──────────────────────── Score: 7.8/10 ───────────╮
│ ...                                                           │
╰──────────────────────────────────────────────────────────────╯

╭─ POST 3/3 ──────────────────────── Score: 7.2/10 ───────────╮
│ ...                                                           │
╰──────────────────────────────────────────────────────────────╯

 [1] Choisir post 1    [2] Post 2    [3] Post 3
 [R] Régénérer         [E] Éditer    [Q] Quitter

> 1

✅ Post sauvegardé (ID: #42)
📋 Copié dans le presse-papier
📄 Sauvé dans output/hyring-agency/2026-03-03_automatisation.md
```

---

## 10. Stack technique

| Composant | Techno | Rôle | Coût |
|-----------|--------|------|------|
| **LLM** | OpenRouter → multi-modèle | Rédaction, scoring, recherche | ~1-2€/mois |
| **SDK LLM** | `openai` 1.x | Client HTTP compatible OpenRouter | Gratuit |
| **Recherche** | `firecrawl-py` | Recherche web + scrape | 16$/mois (Hobby) ou gratuit (500 crédits) |
| **Base de données** | `sqlite3` (stdlib) | Historique, feedback, cache | Gratuit |
| **CLI** | `click` + `rich` | Interface terminal | Gratuit |
| **Config** | `pyyaml` | Fichiers YAML | Gratuit |
| **Validation** | `pydantic` 2.x | Validation outputs LLM | Gratuit |
| **Clipboard** | `pyperclip` | Copie presse-papier | Gratuit |
| **Env** | `python-dotenv` | Variables d'environnement | Gratuit |

**Coût total V1 : ~16-18$/mois** (Firecrawl Hobby + OpenRouter usage léger)

### `requirements.txt`

```
openai>=1.0.0
firecrawl-py>=1.0.0
rich>=13.0.0
click>=8.0.0
pyyaml>=6.0
pydantic>=2.0.0
pyperclip>=1.8.0
python-dotenv>=1.0.0
```

8 dépendances. Pas de ChromaDB, pas de sentence-transformers, pas de prompt-toolkit.

---

## 11. Variables d'environnement

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
FIRECRAWL_API_KEY=fc-xxxxxxxxxxxx
```

---

## 12. Plan de build

| Phase | Quoi | Résultat concret |
|-------|------|-----------------|
| **1. Foundation** | Structure projet, `config.yaml`, `.env`, `agent/llm.py` | `llm.call()` fonctionne avec OpenRouter |
| **2. Contexte** | 5 fichiers YAML (icp, voice, templates, pillars, funnel) + hyring-agency, `memory/loader.py` | `loader.load("hyring-agency")` retourne tout le contexte dont le funnel |
| **3. Writer** | `prompts/system.md`, `prompts/writer.md`, `agent/writer.py` | Génère 3 posts LinkedIn réalistes |
| **4. Scorer** | `prompts/scorer.md`, `agent/scorer.py` + heuristiques | Score + rank les 3 posts |
| **5. Recherche** | `agent/researcher.py`, `prompts/research.md`, Firecrawl | Brief de recherche intégré au writer |
| **6. CLI + Orchestrator** | `main.py` (generate + quick), `agent/orchestrator.py` | Pipeline end-to-end fonctionnel |
| **7. Mémoire** | `memory/history.py` (SQLite), feedback, output markdown | Posts sauvés, feedback enregistré |
| **8. Polish** | suggest, history, clipboard, init-context, verbose mode | Outil complet et utilisable au quotidien |

**Règle : à la fin de la phase 6, tu dois pouvoir copier un post et le publier sur LinkedIn.**
Tout ce qui vient après est de l'optimisation.

---

## 13. V1.5 — Intégration Unipile (post-V1)

Quand la V1 tourne et que tu publies régulièrement :

### Ce qu'Unipile apporte

| Feature | Valeur |
|---------|--------|
| **Publication directe** | `python main.py publish --post-id 42` → publié sur LinkedIn |
| **Stats automatiques** | Récupère vues, likes, commentaires → injecte dans le feedback |
| **Feedback loop automatisé** | Post publié → 48h → récupère stats → met à jour user_score |
| **Scheduling** | Planifier la publication à une heure optimale |

### Coût additionnel

55$/mois pour 1 compte LinkedIn. Se justifie quand :
- Tu publies 4+ posts/semaine
- Tu veux tracker les performances automatiquement
- Tu gères plusieurs comptes clients

### Architecture V1.5

```python
# Nouveau module
agent/
  └── publisher.py       # Client Unipile (REST API)

# Nouvelles commandes CLI
python main.py publish --post-id 42                    # Publie maintenant
python main.py publish --post-id 42 --schedule "demain 9h"  # Planifie
python main.py sync-stats --context hyring-agency      # Récupère les stats
```

### Pas de SDK Python pour Unipile

Unipile n'a qu'un SDK Node.js. On utilise leur REST API directement avec `httpx` (déjà dispo via `openai`). Pas besoin de dépendance supplémentaire.

---

## 14. Évolutions V2+

| Feature | Description | Quand |
|---------|-------------|-------|
| **Streamlit UI** | Interface web pour usage plus confortable | Quand le CLI est stable |
| **Multi-langue** | Anglais (champ `langue` dans voice.yaml) | Quand tu as un client anglophone |
| **Carousel generator** | Générer des scripts de carousel avec slides | Quand le texte est maîtrisé |
| **ChromaDB** | Mémoire sémantique pour recherche par similarité | Quand tu as 100+ posts |
| **A/B testing** | Publier 2 versions, comparer les perfs via Unipile | Après V1.5 |
| **Multi-plateforme** | Twitter/X, newsletter | Quand LinkedIn est rentable |
