"""Génération de posts LinkedIn multi-format."""

import random
from pathlib import Path

from agent import llm
from memory import loader

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def generate(
    ctx: dict,
    topic: str,
    research_brief: str | None = None,
    recent_posts: list[dict] | None = None,
    funnel_stage: str | None = None,
    num_posts: int = 3,
    format_name: str | None = None,
) -> list[dict]:
    """Génère num_posts versions de post LinkedIn."""
    system_prompt = (PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    writer_template = (PROMPTS_DIR / "writer.md").read_text(encoding="utf-8")

    context_text = loader.format_context_for_prompt(ctx, funnel_stage)
    formats = _build_formats_text(ctx, funnel_stage, format_name)
    research_text = _format_research(research_brief)
    recent_text = _format_recent_posts(recent_posts)

    user_prompt = writer_template.format(
        num_posts=num_posts,
        topic=topic,
        context=context_text,
        formats=formats,
        research_brief=research_text,
        recent_posts=recent_text,
    )

    result = llm.call_json(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model_key="writer",
    )

    posts = result.get("posts", [])

    for post in posts:
        full_text = f"{post.get('hook', '')}\n\n{post.get('body', '')}\n\n{post.get('cta', '')}"
        post["char_count"] = len(full_text)
        post["funnel_stage"] = funnel_stage
        post = _validate_post(post, ctx, funnel_stage)

    return posts


def _build_formats_text(
    ctx: dict, funnel_stage: str | None, format_name: str | None
) -> str:
    """Construit le texte des formats disponibles, filtré par funnel si applicable."""
    all_formats = loader.get_formats(ctx)

    if format_name:
        selected = [f for f in all_formats if f["name"].lower() == format_name.lower()]
        if not selected:
            selected = all_formats
    elif funnel_stage:
        fc = loader.get_funnel_config(ctx, funnel_stage)
        if fc:
            preferred = [n.lower() for n in fc.get("formats_preferes", [])]
            selected = [f for f in all_formats if f["name"].lower() in preferred]
            if len(selected) < 2:
                selected = all_formats
        else:
            selected = all_formats
    else:
        selected = all_formats

    lines = []
    for f in selected:
        lines.append(f"### {f['name']}")
        lines.append(f"Description : {f.get('description', '')}")
        lines.append(f"Structure :\n{f.get('structure', '')}")
        lines.append(f"Exemple de hook : {f.get('exemple_hook', '')}")
        lines.append(f"Performance : {f.get('performance', '')}")
        lines.append("")
    return "\n".join(lines)


def _format_research(brief: str | None) -> str:
    if not brief:
        return "Aucune recherche disponible. Génère le contenu à partir de ton expertise."
    return brief


def _format_recent_posts(posts: list[dict] | None) -> str:
    if not posts:
        return "Aucun post récent."
    lines = []
    for p in posts[:10]:
        lines.append(f"- [{p.get('format', '?')}] {p.get('hook', '(pas de hook)')}")
    return "\n".join(lines)


def _validate_post(post: dict, ctx: dict, funnel_stage: str | None) -> dict:
    """Validation basique des contraintes voice."""
    post.setdefault("validation_warnings", [])

    if funnel_stage:
        min_len, max_len = loader.get_funnel_length_range(
            loader.get_funnel_config(ctx, funnel_stage) or {}
        )
    else:
        min_len, max_len = loader.get_voice_length_range(ctx)

    char_count = post.get("char_count", 0)
    if char_count < min_len:
        post["validation_warnings"].append(f"Trop court ({char_count} < {min_len})")
    elif char_count > max_len:
        post["validation_warnings"].append(f"Trop long ({char_count} > {max_len})")

    interdit = ctx.get("voice", {}).get("interdit", [])
    full_text = f"{post.get('hook', '')} {post.get('body', '')} {post.get('cta', '')}"
    for rule in interdit:
        check_phrase = rule.replace("Pas de ", "").replace("pas de ", "").strip("'\"")
        if check_phrase.lower() in full_text.lower() and len(check_phrase) > 5:
            post["validation_warnings"].append(f"Règle violée : {rule}")

    return post
