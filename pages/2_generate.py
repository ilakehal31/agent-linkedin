"""Génération de posts LinkedIn."""

import os
from pathlib import Path

import streamlit as st
import yaml
from dotenv import load_dotenv

from agent import llm, researcher, orchestrator
from memory import loader, history

load_dotenv()

st.set_page_config(page_title="Générer", page_icon="✍️", layout="wide")
st.title("✍️ Génération de posts")


def _ensure_init():
    """S'assure que LLM et Researcher sont initialisés."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if "config" not in st.session_state:
        with open(config_path, "r", encoding="utf-8") as f:
            st.session_state["config"] = yaml.safe_load(f)

    config = st.session_state["config"]

    if not st.session_state.get("openrouter_ok"):
        api_key = st.session_state.get("openrouter_key") or os.getenv("OPENROUTER_API_KEY")
        if api_key and "xxxx" not in api_key:
            llm.init(api_key, config, verbose=False)
            st.session_state["openrouter_ok"] = True

    if not st.session_state.get("firecrawl_ok"):
        fc_key = st.session_state.get("firecrawl_key") or os.getenv("FIRECRAWL_API_KEY")
        if fc_key and "xxxx" not in fc_key:
            researcher.init(fc_key)
            st.session_state["firecrawl_ok"] = True


_ensure_init()

# --- Check prerequisites ---
if not st.session_state.get("openrouter_ok"):
    st.error("Clé OpenRouter manquante. Configurez-la dans Settings.")
    st.stop()

contexts = loader.list_contexts()
if not contexts:
    st.warning("Aucun contexte disponible. Créez-en un dans Onboarding.")
    st.stop()

# --- Sidebar context selector (mirrors app.py) ---
st.sidebar.title("✍️ Ghost Writer")
config_path_yaml = Path(__file__).parent.parent / "config.yaml"
with open(config_path_yaml, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)
default_context = _cfg.get("defaults", {}).get("context", contexts[0])
default_idx = contexts.index(default_context) if default_context in contexts else 0
context_name = st.sidebar.selectbox(
    "Contexte actif",
    contexts,
    index=default_idx,
    key="active_context",
)
config = st.session_state["config"]

# Load context for pillar/format options
try:
    ctx = loader.load(context_name)
except FileNotFoundError:
    st.error(f"Contexte '{context_name}' introuvable.")
    st.stop()

# --- Suggestions section ---
st.subheader("💡 Suggestions de sujets")

if st.button("Générer des suggestions", key="suggest_btn"):
    with st.spinner("Génération de suggestions..."):
        suggestions = orchestrator.suggest_topics(
            context_name=context_name,
            config=config,
        )
    st.session_state["suggestions"] = suggestions

suggestions = st.session_state.get("suggestions", [])
if suggestions:
    for i, s in enumerate(suggestions):
        col_s1, col_s2 = st.columns([5, 1])
        with col_s1:
            hook_preview = f" — *{s.get('hook', '')}*" if s.get("hook") else ""
            st.markdown(
                f"**{s.get('topic', '?')}** "
                f"| {s.get('pillar', '?')} | {s.get('funnel_stage', '?').upper()}"
                f"{hook_preview}"
            )
        with col_s2:
            if st.button("Utiliser", key=f"use_suggestion_{i}"):
                st.session_state["topic_input"] = s.get("topic", "")
                st.rerun()

st.markdown("---")

# --- Topic input ---
if "topic_input" not in st.session_state:
    st.session_state["topic_input"] = ""
topic = st.text_input("Sujet du post", key="topic_input", placeholder="Ex: L'IA va tuer les agences qui ne se transforment pas")

# --- Options ---
col1, col2, col3 = st.columns(3)
with col1:
    funnel_stage = st.radio("Funnel stage", ["auto", "tofu", "mofu", "bofu"], horizontal=True)
with col2:
    with_research = st.checkbox("Avec recherche web", value=True)
with col3:
    quick_mode = st.toggle("Mode rapide (1 post, sans scoring)")

# Pillar & format selectors
pillars = loader.get_pillars(ctx)
pillar_names = ["auto"] + [p["name"] for p in pillars]

formats = loader.get_formats(ctx)
format_names = ["auto"] + [f["name"] for f in formats]

col_p, col_f = st.columns(2)
with col_p:
    selected_pillar = st.selectbox("Pilier", pillar_names)
with col_f:
    selected_format = st.selectbox("Format", format_names)

if not topic:
    st.info("Entrez un sujet ou utilisez une suggestion ci-dessus.")
    st.stop()

# --- Generate ---
generate_btn = st.button("Générer", type="primary", use_container_width=True)

if generate_btn:
    stage = None if funnel_stage == "auto" else funnel_stage
    fmt = None if selected_format == "auto" else selected_format

    if quick_mode:
        with st.spinner("Génération rapide en cours..."):
            posts, final_stage = orchestrator.quick_generate(
                context_name=context_name,
                topic=topic,
                config=config,
                funnel_stage=stage,
                format_name=fmt,
            )
        if not posts:
            st.error("Aucun post généré.")
            st.stop()

        st.session_state["generated_posts"] = posts
        st.session_state["generated_funnel"] = final_stage
        st.session_state["generated_topic"] = topic
        st.session_state["generated_research"] = None
    else:
        with st.spinner("Recherche + Génération + Scoring en cours..."):
            posts, final_stage, research_brief = orchestrator.generate_posts(
                context_name=context_name,
                topic=topic,
                config=config,
                funnel_stage=stage,
                no_research=not with_research,
            )
        if not posts:
            st.error("Aucun post généré.")
            st.stop()

        st.session_state["generated_posts"] = posts
        st.session_state["generated_funnel"] = final_stage
        st.session_state["generated_topic"] = topic
        st.session_state["generated_research"] = research_brief

# --- Display results ---
posts = st.session_state.get("generated_posts")
if not posts:
    st.stop()

final_stage = st.session_state.get("generated_funnel", "")
topic_display = st.session_state.get("generated_topic", "")

st.markdown(f"**Funnel:** {final_stage.upper() if final_stage else 'AUTO'} | **Sujet:** {topic_display}")
st.markdown("---")

for i, post in enumerate(posts):
    score = post.get("score_total")
    score_label = f"Score: {score}/10" if score else "Non scoré"

    with st.expander(f"Post {i+1} — {score_label} — {post.get('format', '?')}", expanded=(i == 0)):
        # Metadata
        col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)
        col_meta1.metric("Score", f"{score}/10" if score else "-")
        col_meta2.metric("Format", post.get("format", "?"))
        col_meta3.metric("Pilier", post.get("pillar", "?"))
        col_meta4.metric("Caractères", post.get("char_count", 0))

        # Score details bar chart
        score_details = post.get("score_details", {})
        if score_details:
            st.bar_chart(score_details, height=150)

        # Warnings
        warnings = post.get("validation_warnings", [])
        if warnings:
            for w in warnings:
                st.warning(w)

        st.markdown("---")

        # Post content
        hook = post.get("hook", "")
        body = post.get("body", "")
        cta = post.get("cta", "")
        hashtags = post.get("hashtags", [])

        st.markdown(f"**{hook}**")
        st.markdown(body)
        if cta:
            st.markdown(f"*{cta}*")
        if hashtags:
            st.markdown(" ".join(hashtags))

        st.markdown("---")

        # Full post for copy
        full_parts = [p for p in [hook, body, cta] if p]
        full_post = "\n\n".join(full_parts)
        if hashtags:
            full_post += "\n\n" + " ".join(hashtags)

        st.code(full_post, language=None)

        # Actions
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(f"Sauvegarder Post {i+1}", key=f"save_{i}"):
                post_id = history.save_post(
                    context=context_name,
                    topic=topic_display,
                    format_name=post.get("format", ""),
                    pillar=post.get("pillar"),
                    funnel_stage=final_stage,
                    hook=hook,
                    body=body,
                    cta=cta,
                    hashtags=hashtags,
                    score_total=score,
                    score_details=score_details,
                    char_count=post.get("char_count", 0),
                )
                st.success(f"Post sauvegardé (ID: #{post_id})")
