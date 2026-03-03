"""Recherche web via Firecrawl — génération de brief pour le writer."""

import json
from pathlib import Path

from firecrawl import Firecrawl
from rich.console import Console

from agent import llm
from memory import history

console = Console(stderr=True)
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_firecrawl: Firecrawl | None = None


def init(api_key: str):
    global _firecrawl
    _firecrawl = Firecrawl(api_key=api_key)


def research(
    topic: str,
    ctx: dict,
    config: dict,
    use_cache: bool = True,
    verbose: bool = False,
) -> str:
    """Recherche web et génère un brief structuré.

    Returns:
        Brief formaté en texte pour injection dans le prompt du writer.
    """
    context_name = ctx.get("name", "unknown")
    ttl = config.get("research", {}).get("cache_ttl_hours", 24)

    if use_cache:
        cached = history.get_cached_research(context_name, topic, ttl)
        if cached:
            if verbose:
                console.print("  [dim]Cache recherche trouvé, utilisation du cache[/dim]")
            return cached

    queries = _generate_queries(topic, ctx, config, verbose)

    if verbose:
        console.print(f"  [dim]Queries générées : {queries}[/dim]")

    raw_results = _search(queries, config, verbose)

    if not raw_results:
        brief = "Aucun résultat de recherche trouvé. Génère le contenu à partir de ton expertise."
        return brief

    brief = _synthesize(topic, ctx, raw_results, verbose)

    history.save_research_cache(context_name, topic, brief)

    return brief


def _generate_queries(
    topic: str, ctx: dict, config: dict, verbose: bool
) -> list[str]:
    """Génère 2-3 queries de recherche via LLM."""
    icp = ctx.get("icp", {})
    context_desc = f"{icp.get('name', '')} — {icp.get('description', '')}"
    sector = icp.get("persona", {}).get("secteur", "")

    prompt = f"""Génère exactement 3 requêtes de recherche web pour trouver des informations récentes et pertinentes sur ce sujet.

Sujet : {topic}
Secteur : {sector}
Contexte : {context_desc}

Les requêtes doivent :
- Être en français (sauf si le sujet est international)
- Cibler des données récentes (2025-2026)
- Varier les angles (tendances, statistiques, opinions)

Réponds en JSON : {{"queries": ["query1", "query2", "query3"]}}"""

    result = llm.call_json(
        messages=[{"role": "user", "content": prompt}],
        model_key="query_gen",
    )

    queries = result.get("queries", [topic])
    max_queries = config.get("research", {}).get("max_queries", 3)
    return queries[:max_queries]


def _search(queries: list[str], config: dict, verbose: bool) -> list[dict]:
    """Lance les recherches Firecrawl."""
    if not _firecrawl:
        return []

    max_results = config.get("research", {}).get("max_results_per_query", 5)
    all_results = []

    for query in queries:
        try:
            if verbose:
                console.print(f"  [dim]Recherche : {query}[/dim]")

            response = _firecrawl.search(
                query,
                limit=max_results,
                scrape_options={"formats": ["markdown"]},
            )

            data = []
            if isinstance(response, dict):
                data = response.get("data", [])
            elif isinstance(response, list):
                data = response

            for item in data:
                all_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "content": (item.get("markdown", "") or "")[:2000],
                })

        except Exception as e:
            if verbose:
                console.print(f"  [yellow]Erreur recherche '{query}': {e}[/yellow]")

    return all_results


def _synthesize(
    topic: str, ctx: dict, raw_results: list[dict], verbose: bool
) -> str:
    """Synthétise les résultats bruts en brief structuré via LLM."""
    research_template = (PROMPTS_DIR / "research.md").read_text(encoding="utf-8")

    icp = ctx.get("icp", {})

    raw_text = ""
    for i, r in enumerate(raw_results, 1):
        raw_text += f"\n--- Résultat {i} ---\n"
        raw_text += f"Titre : {r['title']}\n"
        raw_text += f"URL : {r['url']}\n"
        raw_text += f"Description : {r['description']}\n"
        if r.get("content"):
            raw_text += f"Contenu :\n{r['content']}\n"

    user_prompt = research_template.format(
        topic=topic,
        context_name=icp.get("name", ""),
        context_description=icp.get("description", ""),
        raw_results=raw_text,
    )

    result = llm.call_json(
        messages=[{"role": "user", "content": user_prompt}],
        model_key="research_synth",
    )

    brief_parts = []

    tendances = result.get("tendances", [])
    if tendances:
        brief_parts.append("### Tendances")
        for t in tendances:
            brief_parts.append(f"- {t}")

    chiffres = result.get("chiffres", [])
    if chiffres:
        brief_parts.append("\n### Chiffres clés")
        for c in chiffres:
            brief_parts.append(f"- {c}")

    angles = result.get("angles", [])
    if angles:
        brief_parts.append("\n### Angles potentiels")
        for a in angles:
            brief_parts.append(f"- {a}")

    controverses = result.get("controverses", [])
    if controverses:
        brief_parts.append("\n### Points de débat")
        for c in controverses:
            brief_parts.append(f"- {c}")

    citations = result.get("citations", [])
    if citations:
        brief_parts.append("\n### Citations")
        for c in citations:
            brief_parts.append(f"- \"{c}\"")

    return "\n".join(brief_parts) if brief_parts else "Aucune donnée exploitable trouvée."
