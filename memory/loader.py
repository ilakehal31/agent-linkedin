"""Charge et fusionne le contexte (YAML + exemples) pour un client/niche donné."""

import os
import re
from pathlib import Path

import yaml

CONTEXTS_DIR = Path(__file__).parent / "contexts"
YAML_FILES = ["icp.yaml", "voice.yaml", "templates.yaml", "pillars.yaml", "funnel.yaml", "personal.yaml", "tech.yaml"]


def load(context_name: str) -> dict:
    """Charge tout le contexte d'un dossier et retourne un dict unifié."""
    context_dir = CONTEXTS_DIR / context_name
    if not context_dir.exists():
        available = [d.name for d in CONTEXTS_DIR.iterdir() if d.is_dir() and d.name != "_template"]
        raise FileNotFoundError(
            f"Contexte '{context_name}' introuvable. Disponibles : {', '.join(available)}"
        )

    ctx = {"name": context_name}

    for filename in YAML_FILES:
        filepath = context_dir / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    key = filename.replace(".yaml", "")
                    ctx[key] = data

    ctx["examples"] = _load_examples(context_dir / "examples")

    return ctx


def _load_examples(examples_dir: Path) -> list[dict]:
    """Charge les posts de référence depuis le dossier examples/."""
    examples = []
    if not examples_dir.exists():
        return examples

    for filepath in sorted(examples_dir.rglob("*.txt")):
        if filepath.name == "README.txt":
            continue
        raw = filepath.read_text(encoding="utf-8").strip()
        if not raw:
            continue

        stats, content = _parse_stats(raw)

        funnel_stage = None
        relative = filepath.relative_to(examples_dir)
        if len(relative.parts) > 1:
            parent = relative.parts[0]
            if parent in ("tofu", "mofu", "bofu"):
                funnel_stage = parent

        examples.append({
            "filename": filepath.name,
            "content": content,
            "funnel_stage": funnel_stage,
            "stats": stats,
        })

    # Trier par pertinence : ICP attiré d'abord, puis par vues
    # Un post viral qui attire la mauvaise audience vaut moins qu'un post modeste qui touche l'ICP
    def _sort_key(e):
        stats = e.get("stats", {})
        icp_ok = 1 if stats.get("icp_attire", "oui").lower() in ("oui", "yes", "true") else 0
        vues = stats.get("vues", 0)
        return (icp_ok, vues)

    examples.sort(key=_sort_key, reverse=True)

    return examples


def _parse_stats(raw: str) -> tuple[dict, str]:
    """Parse la ligne [stats: ...] en haut d'un fichier exemple.

    Returns:
        (stats_dict, content_without_stats)
    """
    stats = {}
    content = raw

    match = re.match(r"^\[stats:\s*(.+?)\]\s*\n*", raw)
    if match:
        stats_str = match.group(1)
        content = raw[match.end():].strip()

        for pair in stats_str.split(","):
            pair = pair.strip()
            if "=" in pair:
                key, val = pair.split("=", 1)
                key = key.strip()
                val = val.strip()
                try:
                    stats[key] = int(val)
                except ValueError:
                    stats[key] = val

    return stats, content


def get_funnel_config(ctx: dict, stage: str) -> dict | None:
    """Extrait la config d'un stage de funnel depuis le contexte."""
    funnel = ctx.get("funnel", {}).get("funnel", {})
    return funnel.get(stage)


def get_funnel_distribution(ctx: dict) -> dict:
    """Retourne la distribution hebdo recommandée."""
    funnel = ctx.get("funnel", {})
    return funnel.get("distribution_hebdo", {"tofu": 2, "mofu": 1, "bofu": 1})


def get_formats(ctx: dict) -> list[dict]:
    """Retourne la liste des formats disponibles."""
    return ctx.get("templates", {}).get("formats", [])


def get_pillars(ctx: dict) -> list[dict]:
    """Retourne la liste des piliers."""
    return ctx.get("pillars", {}).get("pillars", [])


def get_voice_length_range(ctx: dict) -> tuple[int, int]:
    """Parse la longueur cible du voice.yaml et retourne (min, max)."""
    raw = ctx.get("voice", {}).get("longueur_cible", "800-1300 caractères")
    numbers = re.findall(r"\d+", raw)
    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    return 800, 1300


def get_funnel_length_range(funnel_config: dict) -> tuple[int, int]:
    """Parse la longueur du funnel config et retourne (min, max)."""
    raw = funnel_config.get("longueur", "800-1300 caractères")
    numbers = re.findall(r"\d+", raw)
    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    return 800, 1300


def list_contexts() -> list[str]:
    """Liste les contextes disponibles (exclut _template)."""
    return [
        d.name
        for d in CONTEXTS_DIR.iterdir()
        if d.is_dir() and d.name != "_template"
    ]


def format_context_for_prompt(ctx: dict, funnel_stage: str | None = None) -> str:
    """Formate le contexte complet en texte pour injection dans les prompts LLM."""
    parts = []

    icp = ctx.get("icp", {})
    if icp:
        parts.append("## ICP (Profil Client Idéal)")
        parts.append(f"Nom : {icp.get('name', 'N/A')}")
        parts.append(f"Description : {icp.get('description', 'N/A')}")

        persona = icp.get("persona", {})
        if persona:
            parts.append(f"Persona : {persona.get('titre', '')} — {persona.get('secteur', '')}")
            parts.append(f"Taille entreprise : {persona.get('taille_entreprise', '')}")
            parts.append(f"Localisation : {persona.get('localisation', '')}")

        douleurs = icp.get("douleurs", [])
        if douleurs:
            parts.append("\nDouleurs :")
            for d in douleurs:
                parts.append(f"  - {d}")

        objectifs = icp.get("objectifs", [])
        if objectifs:
            parts.append("\nObjectifs :")
            for o in objectifs:
                parts.append(f"  - {o}")

        objections = icp.get("objections", [])
        if objections:
            parts.append("\nObjections courantes :")
            for o in objections:
                parts.append(f"  - {o}")

        vocab = icp.get("vocabulaire", {})
        if vocab:
            parts.append(f"\nVocabulaire à utiliser : {', '.join(vocab.get('utilise', []))}")
            parts.append(f"Vocabulaire à éviter : {', '.join(vocab.get('evite', []))}")

    voice = ctx.get("voice", {})
    if voice:
        parts.append("\n## Ton et Style")
        parts.append(f"Registre : {voice.get('registre', '')}")
        parts.append(f"Tutoiement : {'oui' if voice.get('tutoiement') else 'non'}")
        parts.append(f"Longueur cible : {voice.get('longueur_cible', '')}")
        style = voice.get("style", [])
        if style:
            parts.append("Style :")
            for s in style:
                parts.append(f"  - {s}")
        interdit = voice.get("interdit", [])
        if interdit:
            parts.append("Interdit :")
            for i in interdit:
                parts.append(f"  - {i}")
        emojis = voice.get("emojis", {})
        if emojis:
            parts.append(f"Emojis : {'oui' if emojis.get('utiliser') else 'non'} — {emojis.get('frequence', '')}")

    if funnel_stage:
        fc = get_funnel_config(ctx, funnel_stage)
        if fc:
            parts.append(f"\n## Funnel — {fc.get('label', funnel_stage.upper())}")
            parts.append(f"Objectif : {fc.get('objectif', '')}")
            parts.append(f"Ton : {fc.get('ton', '')}")
            parts.append(f"Profondeur : {fc.get('profondeur', '')}")
            parts.append(f"Longueur : {fc.get('longueur', '')}")
            parts.append(f"Style de CTA : {fc.get('cta_style', '')}")
            parts.append(f"Formats préférés : {', '.join(fc.get('formats_preferes', []))}")
            regles = fc.get("regles", [])
            if regles:
                parts.append("Règles funnel :")
                for r in regles:
                    parts.append(f"  - {r}")

    # Personal branding
    personal = ctx.get("personal", {})
    if personal:
        parts.append(f"\n## Personal Branding — {personal.get('prenom', '')} ({personal.get('role', '')})")

        convictions = personal.get("convictions", [])
        if convictions:
            parts.append("\nConvictions (à distiller dans les posts) :")
            for c in convictions:
                parts.append(f"  - {c}")

        erreurs = personal.get("erreurs", personal.get("erreurs_et_lecons", []))
        if erreurs:
            parts.append("\nErreurs vécues (pour du storytelling authentique) :")
            for e in erreurs:
                if isinstance(e, dict):
                    parts.append(f"  - {e.get('situation', '')} → Leçon : {e.get('lecon', '')}")
                else:
                    parts.append(f"  - {e}")

        reussites = personal.get("reussites", [])
        if reussites:
            parts.append("\nRéussites (pour de la preuve sociale) :")
            for r in reussites:
                if isinstance(r, dict):
                    parts.append(f"  - {r.get('situation', '')} — {r.get('chiffres', '')}")
                else:
                    parts.append(f"  - {r}")

        anecdotes = personal.get("anecdotes", [])
        if anecdotes:
            parts.append("\nAnecdotes utilisables :")
            for a in anecdotes:
                if isinstance(a, dict):
                    parts.append(f"  - {a.get('contexte', '')} → {a.get('histoire', '')} (Morale : {a.get('morale', '')})")
                else:
                    parts.append(f"  - {a}")

        expressions = personal.get("style_personnel", {}).get("expressions_frequentes", [])
        if expressions:
            parts.append(f"\nExpressions signature : {', '.join(expressions)}")

    # Tech stack
    tech = ctx.get("tech", {})
    if tech:
        stack = tech.get("stack", {})
        parts.append(f"\n## Stack Technique — {stack.get('description', '')}")

        frontend = stack.get("frontend", {})
        if frontend:
            parts.append(f"Frontend : {frontend.get('framework', '')} + {frontend.get('meta_framework', '')}")
            parts.append(f"Pourquoi : {frontend.get('pourquoi', '')}")

        backend = stack.get("backend", {})
        if backend:
            parts.append(f"Backend : {backend.get('framework', '')}")
            parts.append(f"Pourquoi : {backend.get('pourquoi', '')}")

        principes = stack.get("principes", [])
        if principes:
            parts.append("Principes tech :")
            for p in principes:
                parts.append(f"  - {p}")

        opinions = tech.get("opinions_tech", [])
        if opinions:
            parts.append("\nOpinions tech (utilisables dans les posts) :")
            for o in opinions:
                parts.append(f"  - {o.get('opinion', '')} — {o.get('argument', '')}")

        traductions = tech.get("vocabulaire_tech_accessible", {}).get("traductions", [])
        if traductions:
            parts.append("\nTraductions tech → accessible (pour parler à des non-techs) :")
            for t in traductions:
                parts.append(f"  - {t.get('technique', '')} = \"{t.get('accessible', '')}\"")

    examples = ctx.get("examples", [])
    if examples:
        relevant = examples
        if funnel_stage:
            stage_examples = [e for e in examples if e["funnel_stage"] == funnel_stage]
            if stage_examples:
                relevant = stage_examples
            else:
                relevant = [e for e in examples if e["funnel_stage"] is None]
                if not relevant:
                    relevant = examples[:5]

        parts.append(f"\n## Exemples de posts de référence ({len(relevant)} posts)")
        parts.append("(Triés par performance — le premier est le meilleur)")
        for i, ex in enumerate(relevant[:5], 1):
            stage_label = f" [{ex['funnel_stage'].upper()}]" if ex["funnel_stage"] else ""
            stats = ex.get("stats", {})
            if stats:
                stats_label = f" — {stats.get('vues', '?')} vues, {stats.get('likes', '?')} likes, {stats.get('commentaires', '?')} commentaires"
                icp_attire = stats.get("icp_attire", "oui")
                if str(icp_attire).lower() in ("non", "no", "false"):
                    note = stats.get("note", "Audience hors cible")
                    stats_label += f"\n⚠️ ATTENTION : Ce post a fait du reach MAIS n'a PAS attiré l'ICP. {note}"
                    stats_label += "\n→ NE PAS reproduire cet angle. S'en servir comme contre-exemple."
            else:
                stats_label = ""
            parts.append(f"\n--- Exemple {i}{stage_label}{stats_label} ---")
            parts.append(ex["content"])

    return "\n".join(parts)
