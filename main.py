"""LinkedIn Ghost Writer — CLI (Click + Rich)."""

import os
import shutil
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv
from rich.console import Console

from agent import llm, researcher, orchestrator
from memory import loader

console = Console()
CONFIG_PATH = Path(__file__).parent / "config.yaml"

load_dotenv()


def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _init(verbose: bool = False):
    """Initialise les clients LLM et Firecrawl."""
    config = _load_config()

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key or "xxxx" in openrouter_key:
        console.print("[red]OPENROUTER_API_KEY manquante ou invalide dans .env[/red]")
        raise click.Abort()

    llm.init(openrouter_key, config, verbose=verbose)

    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    if firecrawl_key and "xxxx" not in firecrawl_key:
        researcher.init(firecrawl_key)
    elif verbose:
        console.print("[yellow]FIRECRAWL_API_KEY absente — recherche désactivée[/yellow]")

    return config


@click.group()
@click.version_option(version="1.0.0", prog_name="linkedin-ghost-writer")
def cli():
    """LinkedIn Ghost Writer — Agent IA éditorial LinkedIn."""
    pass


@cli.command()
@click.option("--context", "-c", default=None, help="Nom du contexte (dossier dans memory/contexts/)")
@click.option("--topic", "-t", required=True, help="Sujet du post")
@click.option("--funnel", "-f", type=click.Choice(["tofu", "mofu", "bofu"]), default=None, help="Stage de funnel")
@click.option("--no-research", is_flag=True, help="Skip la recherche web")
@click.option("--no-cache", is_flag=True, help="Force une recherche fraîche")
@click.option("--verbose", "-v", is_flag=True, help="Mode verbose")
def generate(context, topic, funnel, no_research, no_cache, verbose):
    """Génère 3 posts LinkedIn scorés et rankés."""
    config = _init(verbose)
    context = context or config.get("defaults", {}).get("context", "hyring-agency")

    orchestrator.generate(
        context_name=context,
        topic=topic,
        config=config,
        funnel_stage=funnel,
        no_research=no_research,
        no_cache=no_cache,
        verbose=verbose,
    )


@cli.command()
@click.option("--context", "-c", default=None, help="Nom du contexte")
@click.option("--topic", "-t", required=True, help="Sujet du post")
@click.option("--funnel", "-f", type=click.Choice(["tofu", "mofu", "bofu"]), default=None)
@click.option("--format", "format_name", default=None, help="Nom du format (ex: storytelling)")
@click.option("--verbose", "-v", is_flag=True)
def quick(context, topic, funnel, format_name, verbose):
    """Post rapide — 1 post, sans recherche ni scoring."""
    config = _init(verbose)
    context = context or config.get("defaults", {}).get("context", "hyring-agency")

    orchestrator.quick(
        context_name=context,
        topic=topic,
        config=config,
        funnel_stage=funnel,
        format_name=format_name,
        verbose=verbose,
    )


@cli.command()
@click.option("--context", "-c", default=None, help="Nom du contexte")
@click.option("--funnel", "-f", type=click.Choice(["tofu", "mofu", "bofu"]), default=None)
@click.option("--verbose", "-v", is_flag=True)
def suggest(context, funnel, verbose):
    """Suggestions de sujets pour la semaine."""
    config = _init(verbose)
    context = context or config.get("defaults", {}).get("context", "hyring-agency")

    orchestrator.suggest(
        context_name=context,
        config=config,
        funnel_stage=funnel,
        verbose=verbose,
    )


@cli.command()
@click.option("--post-id", required=True, type=int, help="ID du post")
@click.option("--score", required=True, type=click.IntRange(1, 10), help="Note de 1 à 10")
@click.option("--note", default=None, help="Commentaire libre")
def feedback(post_id, score, note):
    """Donne un feedback sur un post publié."""
    _init()
    orchestrator.feedback(post_id, score, note)


@cli.command()
@click.option("--context", "-c", default=None, help="Nom du contexte")
@click.option("--last", default=20, help="Nombre de posts à afficher")
@click.option("--best", is_flag=True, help="Trier par meilleur user_score")
@click.option("--funnel-stats", is_flag=True, help="Afficher la distribution funnel")
def history(context, last, best, funnel_stats):
    """Affiche l'historique des posts."""
    config = _init()
    context = context or config.get("defaults", {}).get("context", "hyring-agency")

    orchestrator.show_history(
        context_name=context,
        last=last,
        best=best,
        funnel_stats=funnel_stats,
    )


@cli.command("init-context")
@click.option("--name", required=True, help="Nom du nouveau contexte")
def init_context(name):
    """Crée un nouveau contexte depuis le template."""
    template_dir = Path(__file__).parent / "memory" / "contexts" / "_template"
    target_dir = Path(__file__).parent / "memory" / "contexts" / name

    if target_dir.exists():
        console.print(f"[red]Le contexte '{name}' existe déjà.[/red]")
        raise click.Abort()

    shutil.copytree(template_dir, target_dir)
    console.print(f"[green]Contexte '{name}' créé dans {target_dir}[/green]")
    console.print("[dim]Édite les fichiers YAML pour configurer ton ICP, ton, et funnel.[/dim]")


@cli.command("list-contexts")
def list_contexts():
    """Liste les contextes disponibles."""
    contexts = loader.list_contexts()
    if not contexts:
        console.print("[dim]Aucun contexte trouvé. Utilise init-context pour en créer un.[/dim]")
        return
    for ctx in contexts:
        console.print(f"  - {ctx}")


if __name__ == "__main__":
    cli()
