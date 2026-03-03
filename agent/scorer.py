"""Scoring et ranking des posts LinkedIn."""

import re
from pathlib import Path

from agent import llm
from memory import loader

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

WEIGHTS = {
    "hook": 2.0,
    "structure": 1.0,
    "icp_fit": 2.0,
    "cta": 1.5,
    "originality": 1.5,
    "funnel_fit": 2.0,
}


def score_post(
    post: dict,
    ctx: dict,
    funnel_stage: str | None = None,
    config: dict | None = None,
) -> dict:
    """Score un post et retourne les scores détaillés + score total."""
    weights = WEIGHTS.copy()
    if config:
        config_weights = config.get("scoring", {}).get("weights", {})
        weights.update(config_weights)

    llm_scores = _llm_score(post, ctx, funnel_stage)
    heuristic_penalties = _heuristic_penalties(post, ctx, funnel_stage)

    final_scores = {}
    for criterion in weights:
        base = llm_scores.get(criterion, 5)
        penalty = heuristic_penalties.get(criterion, 0)
        final_scores[criterion] = max(1, min(10, base + penalty))

    total_weight = sum(weights.values())
    weighted_sum = sum(final_scores[c] * weights[c] for c in weights)
    score_total = round(weighted_sum / total_weight, 1)

    return {
        "scores": final_scores,
        "score_total": score_total,
        "feedback": llm_scores.get("feedback", ""),
        "penalties": {k: v for k, v in heuristic_penalties.items() if v != 0},
    }


def score_and_rank(
    posts: list[dict],
    ctx: dict,
    funnel_stage: str | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Score tous les posts et les trie par score décroissant."""
    for post in posts:
        result = score_post(post, ctx, funnel_stage, config)
        post["score_total"] = result["score_total"]
        post["score_details"] = result["scores"]
        post["score_feedback"] = result["feedback"]
        post["score_penalties"] = result["penalties"]

    posts.sort(key=lambda p: p.get("score_total", 0), reverse=True)
    return posts


def _llm_score(post: dict, ctx: dict, funnel_stage: str | None) -> dict:
    """Score via LLM (Haiku — rapide et pas cher)."""
    scorer_template = (PROMPTS_DIR / "scorer.md").read_text(encoding="utf-8")

    context_text = loader.format_context_for_prompt(ctx, funnel_stage)

    funnel_rules = ""
    if funnel_stage:
        fc = loader.get_funnel_config(ctx, funnel_stage)
        if fc:
            rules = fc.get("regles", [])
            funnel_rules = "\n".join(f"- {r}" for r in rules)

    hashtags_text = ", ".join(post.get("hashtags", []))

    user_prompt = scorer_template.format(
        context=context_text,
        funnel_stage=funnel_stage or "non spécifié",
        funnel_rules=funnel_rules or "Aucune règle funnel spécifique.",
        hook=post.get("hook", ""),
        body=post.get("body", ""),
        cta=post.get("cta", ""),
        hashtags=hashtags_text,
        char_count=post.get("char_count", 0),
    )

    result = llm.call_json(
        messages=[{"role": "user", "content": user_prompt}],
        model_key="scorer",
    )

    scores = result.get("scores", {})
    feedback = result.get("feedback", "")

    return {**scores, "feedback": feedback}


def _heuristic_penalties(
    post: dict, ctx: dict, funnel_stage: str | None
) -> dict[str, float]:
    """Heuristiques déterministes — malus sur les critères."""
    penalties = {}
    hook = post.get("hook", "")
    body = post.get("body", "")
    cta = post.get("cta", "")
    full_text = f"{hook}\n\n{body}\n\n{cta}"
    char_count = post.get("char_count", len(full_text))

    # Hook trop long (> 2 lignes / > 100 chars)
    if len(hook) > 100 or hook.count("\n") > 1:
        penalties["hook"] = -1

    # Emojis dans le hook (si interdit)
    emojis_config = ctx.get("voice", {}).get("emojis", {})
    if emojis_config.get("utiliser"):
        freq = emojis_config.get("frequence", "")
        if "jamais dans le hook" in freq.lower():
            if _has_emoji(hook):
                penalties["structure"] = penalties.get("structure", 0) - 0.5

    # Longueur hors range
    if funnel_stage:
        fc = loader.get_funnel_config(ctx, funnel_stage)
        if fc:
            min_len, max_len = loader.get_funnel_length_range(fc)
        else:
            min_len, max_len = loader.get_voice_length_range(ctx)
    else:
        min_len, max_len = loader.get_voice_length_range(ctx)

    if char_count < min_len or char_count > max_len:
        penalties["structure"] = penalties.get("structure", 0) - 1

    # Pas de CTA
    if not cta or len(cta.strip()) < 10:
        penalties["cta"] = -1
    elif not any(c in cta for c in ["?", "DM", "commentaire", "comment", "partagez", "sauvegardez"]):
        penalties["cta"] = penalties.get("cta", 0) - 0.5

    # Funnel-specific
    if funnel_stage == "tofu":
        service_words = ["notre offre", "nos services", "réservez", "prenez rendez-vous", "lien en commentaire"]
        for w in service_words:
            if w.lower() in full_text.lower():
                penalties["funnel_fit"] = penalties.get("funnel_fit", 0) - 2
                break

    elif funnel_stage == "bofu":
        has_number = bool(re.search(r"\d+%|\d+€|\d+ ", body))
        if not has_number:
            penalties["funnel_fit"] = penalties.get("funnel_fit", 0) - 2

        direct_cta = ["dm", "message", "commentaire", "lien", "rdv", "rendez-vous", "créneau", "appel"]
        if not any(w in cta.lower() for w in direct_cta):
            penalties["funnel_fit"] = penalties.get("funnel_fit", 0) - 1

    return penalties


def _has_emoji(text: str) -> bool:
    """Détecte la présence d'emojis dans le texte."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f900-\U0001f9FF"  # supplemental
        "\U00002600-\U000026FF"  # misc symbols
        "]+",
        flags=re.UNICODE,
    )
    return bool(emoji_pattern.search(text))
