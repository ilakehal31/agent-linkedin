"""Orchestrateur — pipelines generate, quick, suggest, feedback."""

import json
from datetime import date
from pathlib import Path

import pyperclip
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table

from agent import llm, researcher, writer, scorer
from memory import loader, history

console = Console()
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def generate_posts(
    context_name: str,
    topic: str,
    config: dict,
    funnel_stage: str | None = None,
    no_research: bool = False,
    no_cache: bool = False,
    verbose: bool = False,
) -> tuple[list[dict], str, str | None]:
    """Pipeline non-interactif : retourne (posts_scored, funnel_stage, research_brief).

    Utilisé par l'UI Streamlit — pas d'interaction CLI.
    """
    ctx = loader.load(context_name)

    if not funnel_stage:
        funnel_stage = _auto_funnel_silent(ctx, context_name)

    # Recherche
    research_brief = None
    if not no_research:
        research_brief = researcher.research(
            topic, ctx, config, use_cache=not no_cache, verbose=verbose
        )

    # Posts récents
    recent_posts = history.get_recent_posts(context_name, limit=10)

    # Génération
    num_posts = config.get("defaults", {}).get("num_posts", 3)
    posts = writer.generate(
        ctx, topic, research_brief, recent_posts,
        funnel_stage=funnel_stage, num_posts=num_posts,
    )

    if not posts:
        return [], funnel_stage, research_brief

    # Scoring
    posts = scorer.score_and_rank(posts, ctx, funnel_stage, config)

    return posts, funnel_stage, research_brief


def quick_generate(
    context_name: str,
    topic: str,
    config: dict,
    funnel_stage: str | None = None,
    format_name: str | None = None,
) -> tuple[list[dict], str]:
    """Quick generation non-interactif : 1 post, sans recherche ni scoring.

    Retourne (posts, funnel_stage).
    """
    ctx = loader.load(context_name)

    if not funnel_stage:
        funnel_stage = _auto_funnel_silent(ctx, context_name)

    posts = writer.generate(
        ctx, topic, None, None,
        funnel_stage=funnel_stage, num_posts=1, format_name=format_name,
    )

    return posts, funnel_stage


def suggest_topics(
    context_name: str,
    config: dict,
    funnel_stage: str | None = None,
) -> list[dict]:
    """Suggestions non-interactives : retourne une liste de suggestions."""
    ctx = loader.load(context_name)
    suggest_template = (PROMPTS_DIR / "suggest.md").read_text(encoding="utf-8")

    recent_posts = history.get_recent_posts(context_name, limit=30)
    recent_topics = "\n".join(
        f"- {p.get('topic', '?')} ({p.get('format', '?')}, {p.get('funnel_stage', '?')})"
        for p in recent_posts
    ) or "Aucun post récent."

    funnel_stats = history.get_funnel_distribution(context_name, days=7)
    funnel_target = loader.get_funnel_distribution(ctx)

    context_text = loader.format_context_for_prompt(ctx, funnel_stage)
    pillars_text = "\n".join(
        f"- {p['name']}: {p.get('description', '')}"
        for p in loader.get_pillars(ctx)
    )

    funnel_stats_text = " | ".join(f"{k.upper()}: {v}" for k, v in funnel_stats.items())
    funnel_target_text = " | ".join(f"{k.upper()}: {v}" for k, v in funnel_target.items())

    user_prompt = suggest_template.format(
        context=context_text,
        pillars=pillars_text,
        recent_topics=recent_topics,
        funnel_stats=funnel_stats_text,
        funnel_target=funnel_target_text,
    )

    result = llm.call_json(
        messages=[{"role": "user", "content": user_prompt}],
        model_key="suggest",
    )

    return result.get("suggestions", [])


def _auto_funnel_silent(ctx: dict, context_name: str) -> str:
    """Auto-funnel sans affichage CLI."""
    current = history.get_funnel_distribution(context_name, days=7)
    target = loader.get_funnel_distribution(ctx)

    best_stage = "tofu"
    best_gap = -999

    for stage in ("tofu", "mofu", "bofu"):
        target_count = target.get(stage, 1)
        current_count = current.get(stage, 0)
        gap = target_count - current_count
        if gap > best_gap:
            best_gap = gap
            best_stage = stage

    return best_stage


def generate(
    context_name: str,
    topic: str,
    config: dict,
    funnel_stage: str | None = None,
    no_research: bool = False,
    no_cache: bool = False,
    verbose: bool = False,
):
    """Pipeline principal : contexte → recherche → écriture → scoring → sélection."""
    ctx = loader.load(context_name)

    # Auto-funnel si pas spécifié
    if not funnel_stage:
        funnel_stage = _auto_funnel(ctx, context_name, verbose)

    funnel_label = funnel_stage.upper() if funnel_stage else "AUTO"
    fc = loader.get_funnel_config(ctx, funnel_stage) if funnel_stage else None
    if fc:
        console.print(Panel(
            f"[bold]{fc.get('label', funnel_label)}[/bold]\n"
            f"Objectif : {fc.get('objectif', '')}",
            title=f"Funnel : {funnel_label}",
            border_style="blue",
        ))

    # Recherche
    research_brief = None
    if not no_research:
        with console.status("[bold blue]Recherche en cours..."):
            research_brief = researcher.research(
                topic, ctx, config, use_cache=not no_cache, verbose=verbose
            )
        console.print("[green]Recherche terminée[/green]")

    # Posts récents (éviter répétitions)
    recent_posts = history.get_recent_posts(context_name, limit=10)

    # Génération
    num_posts = config.get("defaults", {}).get("num_posts", 3)
    with console.status(f"[bold blue]Génération de {num_posts} posts..."):
        posts = writer.generate(
            ctx, topic, research_brief, recent_posts,
            funnel_stage=funnel_stage, num_posts=num_posts,
        )

    if not posts:
        console.print("[red]Aucun post généré.[/red]")
        return

    # Scoring
    with console.status("[bold blue]Scoring en cours..."):
        posts = scorer.score_and_rank(posts, ctx, funnel_stage, config)

    # Affichage
    _display_posts(posts, funnel_stage)

    # Sélection
    choice = _prompt_selection(len(posts))
    if choice is None:
        return

    if choice == "r":
        console.print("[yellow]Régénération...[/yellow]")
        return generate(context_name, topic, config, funnel_stage, no_research, no_cache, verbose)

    selected = posts[choice]

    # Sauvegarde
    post_id = history.save_post(
        context=context_name,
        topic=topic,
        format_name=selected.get("format", ""),
        pillar=selected.get("pillar"),
        funnel_stage=funnel_stage,
        hook=selected.get("hook", ""),
        body=selected.get("body", ""),
        cta=selected.get("cta"),
        hashtags=selected.get("hashtags"),
        score_total=selected.get("score_total"),
        score_details=selected.get("score_details"),
        char_count=selected.get("char_count", 0),
    )

    # Copie presse-papier
    full_post = _format_full_post(selected)
    try:
        pyperclip.copy(full_post)
        console.print("[green]Copié dans le presse-papier[/green]")
    except Exception:
        console.print("[yellow]Impossible de copier dans le presse-papier[/yellow]")

    # Sauvegarde fichier
    output_path = _save_output(context_name, topic, selected, post_id)

    console.print(f"[green]Post sauvegardé (ID: #{post_id})[/green]")
    console.print(f"[dim]Fichier : {output_path}[/dim]")


def quick(
    context_name: str,
    topic: str,
    config: dict,
    funnel_stage: str | None = None,
    format_name: str | None = None,
    verbose: bool = False,
):
    """Post rapide — 1 post, pas de recherche, pas de scoring."""
    ctx = loader.load(context_name)

    if not funnel_stage:
        funnel_stage = _auto_funnel(ctx, context_name, verbose)

    with console.status("[bold blue]Génération rapide..."):
        posts = writer.generate(
            ctx, topic, None, None,
            funnel_stage=funnel_stage, num_posts=1, format_name=format_name,
        )

    if not posts:
        console.print("[red]Aucun post généré.[/red]")
        return

    post = posts[0]
    _display_single_post(post, funnel_stage)

    full_post = _format_full_post(post)
    try:
        pyperclip.copy(full_post)
        console.print("[green]Copié dans le presse-papier[/green]")
    except Exception:
        console.print("[yellow]Impossible de copier dans le presse-papier[/yellow]")

    post_id = history.save_post(
        context=context_name,
        topic=topic,
        format_name=post.get("format", ""),
        pillar=post.get("pillar"),
        funnel_stage=funnel_stage,
        hook=post.get("hook", ""),
        body=post.get("body", ""),
        cta=post.get("cta"),
        hashtags=post.get("hashtags"),
        score_total=None,
        score_details=None,
        char_count=post.get("char_count", 0),
    )
    console.print(f"[green]Post sauvegardé (ID: #{post_id})[/green]")


def suggest(
    context_name: str,
    config: dict,
    funnel_stage: str | None = None,
    verbose: bool = False,
):
    """Suggestions de sujets pour la semaine."""
    ctx = loader.load(context_name)
    suggest_template = (PROMPTS_DIR / "suggest.md").read_text(encoding="utf-8")

    recent_posts = history.get_recent_posts(context_name, limit=30)
    recent_topics = "\n".join(
        f"- {p.get('topic', '?')} ({p.get('format', '?')}, {p.get('funnel_stage', '?')})"
        for p in recent_posts
    ) or "Aucun post récent."

    funnel_stats = history.get_funnel_distribution(context_name, days=7)
    funnel_target = loader.get_funnel_distribution(ctx)

    context_text = loader.format_context_for_prompt(ctx)
    pillars_text = "\n".join(
        f"- {p['name']}: {p.get('description', '')}"
        for p in loader.get_pillars(ctx)
    )

    funnel_stats_text = " | ".join(f"{k.upper()}: {v}" for k, v in funnel_stats.items())
    funnel_target_text = " | ".join(f"{k.upper()}: {v}" for k, v in funnel_target.items())

    user_prompt = suggest_template.format(
        context=context_text,
        pillars=pillars_text,
        recent_topics=recent_topics,
        funnel_stats=funnel_stats_text,
        funnel_target=funnel_target_text,
    )

    with console.status("[bold blue]Génération de suggestions..."):
        result = llm.call_json(
            messages=[{"role": "user", "content": user_prompt}],
            model_key="suggest",
        )

    suggestions = result.get("suggestions", [])
    if not suggestions:
        console.print("[red]Aucune suggestion générée.[/red]")
        return

    table = Table(title="Suggestions de sujets", show_lines=True)
    table.add_column("#", style="bold", width=3)
    table.add_column("Sujet", style="cyan")
    table.add_column("Pilier", style="green")
    table.add_column("Funnel", style="blue")
    table.add_column("Hook potentiel", style="yellow")

    for i, s in enumerate(suggestions, 1):
        table.add_row(
            str(i),
            s.get("topic", ""),
            s.get("pillar", ""),
            s.get("funnel_stage", "").upper(),
            s.get("hook", ""),
        )

    console.print(table)


def feedback(post_id: int, user_score: int, user_note: str | None = None):
    """Enregistre le feedback sur un post."""
    post = history.get_post_by_id(post_id)
    if not post:
        console.print(f"[red]Post #{post_id} introuvable.[/red]")
        return

    history.update_feedback(post_id, user_score, user_note)

    if user_score >= 8:
        console.print(f"[green]Post #{post_id} marqué comme top performer (score: {user_score}/10)[/green]")
    elif user_score <= 4:
        console.print(f"[yellow]Post #{post_id} marqué comme sous-performant (score: {user_score}/10)[/yellow]")
    else:
        console.print(f"[blue]Feedback enregistré pour #{post_id} (score: {user_score}/10)[/blue]")


def show_history(
    context_name: str,
    last: int = 20,
    best: bool = False,
    funnel_stats: bool = False,
):
    """Affiche l'historique des posts."""
    if funnel_stats:
        stats = history.get_funnel_distribution(context_name, days=30)
        total = sum(stats.values())
        console.print(Panel(
            " | ".join(
                f"{k.upper()}: {v} ({round(v/total*100)}%)" if total > 0 else f"{k.upper()}: 0"
                for k, v in stats.items()
            ),
            title="Distribution Funnel (30 jours)",
            border_style="blue",
        ))
        return

    if best:
        posts = history.get_best_posts(context_name, limit=last)
    else:
        posts = history.get_history(context_name, last=last)

    if not posts:
        console.print("[dim]Aucun post trouvé.[/dim]")
        return

    table = Table(title=f"Historique — {context_name}", show_lines=True)
    table.add_column("ID", style="bold", width=5)
    table.add_column("Topic", style="cyan", max_width=30)
    table.add_column("Format", style="green")
    table.add_column("Funnel", style="blue")
    table.add_column("Score", style="yellow")
    table.add_column("User", style="magenta")
    table.add_column("Status")
    table.add_column("Date", style="dim")

    for p in posts:
        table.add_row(
            str(p.get("id", "")),
            p.get("topic", ""),
            p.get("format", ""),
            (p.get("funnel_stage") or "").upper(),
            str(p.get("score_total") or "-"),
            str(p.get("user_score") or "-"),
            p.get("status", ""),
            str(p.get("created_at", ""))[:10],
        )

    console.print(table)


# --- Helpers privés ---


def _auto_funnel(ctx: dict, context_name: str, verbose: bool) -> str:
    """Choisit automatiquement le stage de funnel le plus sous-représenté."""
    current = history.get_funnel_distribution(context_name, days=7)
    target = loader.get_funnel_distribution(ctx)

    best_stage = "tofu"
    best_gap = -999

    for stage in ("tofu", "mofu", "bofu"):
        target_count = target.get(stage, 1)
        current_count = current.get(stage, 0)
        gap = target_count - current_count
        if gap > best_gap:
            best_gap = gap
            best_stage = stage

    if verbose:
        console.print(
            f"  [dim]Auto-funnel : {best_stage.upper()} "
            f"(actuel: {current}, cible: {target})[/dim]"
        )

    console.print(
        f"[blue]Auto-funnel → {best_stage.upper()} "
        f"({current.get(best_stage, 0)} cette semaine, cible: {target.get(best_stage, 1)})[/blue]"
    )

    return best_stage


def _display_posts(posts: list[dict], funnel_stage: str | None):
    """Affiche les posts avec leurs scores dans des panels Rich."""
    for i, post in enumerate(posts, 1):
        score = post.get("score_total", 0)
        scores = post.get("score_details", {})
        funnel_label = (post.get("funnel_stage") or funnel_stage or "").upper()

        score_line = " | ".join(
            f"{k.capitalize()}: {v}" for k, v in scores.items()
        )

        full_post = _format_full_post(post)
        warnings = post.get("validation_warnings", [])
        warning_text = ""
        if warnings:
            warning_text = "\n[yellow]" + " | ".join(warnings) + "[/yellow]"

        content = (
            f"[dim]Format: {post.get('format', '?')}  |  "
            f"Pilier: {post.get('pillar', '?')}  |  "
            f"Funnel: {funnel_label}  |  "
            f"{post.get('char_count', 0)} chars[/dim]\n\n"
            f"{full_post}\n\n"
            f"[dim]{score_line}[/dim]"
            f"{warning_text}"
        )

        panel = Panel(
            content,
            title=f"POST {i}/{len(posts)} — Score: {score}/10",
            border_style="green" if score >= 8 else "yellow" if score >= 6 else "red",
        )
        console.print(panel)
        console.print()


def _display_single_post(post: dict, funnel_stage: str | None):
    """Affiche un seul post."""
    funnel_label = (post.get("funnel_stage") or funnel_stage or "").upper()
    full_post = _format_full_post(post)

    content = (
        f"[dim]Format: {post.get('format', '?')}  |  "
        f"Pilier: {post.get('pillar', '?')}  |  "
        f"Funnel: {funnel_label}  |  "
        f"{post.get('char_count', 0)} chars[/dim]\n\n"
        f"{full_post}"
    )

    console.print(Panel(content, title="Quick Post", border_style="cyan"))


def _format_full_post(post: dict) -> str:
    """Assemble le post complet (hook + body + cta + hashtags)."""
    parts = []
    if post.get("hook"):
        parts.append(post["hook"])
    if post.get("body"):
        parts.append(post["body"])
    if post.get("cta"):
        parts.append(post["cta"])
    text = "\n\n".join(parts)
    hashtags = post.get("hashtags", [])
    if hashtags:
        text += "\n\n" + " ".join(hashtags)
    return text


def _prompt_selection(num_posts: int) -> int | str | None:
    """Demande à l'utilisateur de choisir un post."""
    choices = [str(i) for i in range(1, num_posts + 1)] + ["r", "q"]
    labels = "  ".join(f"[{i}] Post {i}" for i in range(1, num_posts + 1))
    labels += "  [R] Régénérer  [Q] Quitter"
    console.print(labels)

    choice = Prompt.ask("Votre choix", choices=choices, default="1").lower()
    if choice == "q":
        return None
    if choice == "r":
        return "r"
    return int(choice) - 1


def _save_output(context_name: str, topic: str, post: dict, post_id: int) -> Path:
    """Sauvegarde le post en markdown dans output/."""
    output_dir = OUTPUT_DIR / context_name
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_topic = "".join(c if c.isalnum() or c in "-_ " else "" for c in topic)[:50].strip()
    safe_topic = safe_topic.replace(" ", "_").lower()
    filename = f"{date.today().isoformat()}_{safe_topic}.md"
    filepath = output_dir / filename

    full_post = _format_full_post(post)
    meta = (
        f"---\n"
        f"id: {post_id}\n"
        f"topic: {topic}\n"
        f"format: {post.get('format', '')}\n"
        f"pillar: {post.get('pillar', '')}\n"
        f"funnel: {post.get('funnel_stage', '')}\n"
        f"score: {post.get('score_total', '')}\n"
        f"chars: {post.get('char_count', '')}\n"
        f"date: {date.today().isoformat()}\n"
        f"---\n\n"
    )

    filepath.write_text(meta + full_post, encoding="utf-8")
    return filepath
