"""LinkedIn Ghost Writer — Streamlit UI."""

import os
from pathlib import Path

import streamlit as st
import yaml
from dotenv import load_dotenv

from agent import llm, researcher
from memory import loader

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _init_services():
    """Initialise LLM et Researcher une seule fois via session_state."""
    if st.session_state.get("services_initialized"):
        return

    config = _load_config()
    st.session_state["config"] = config

    openrouter_key = st.session_state.get("openrouter_key") or os.getenv("OPENROUTER_API_KEY")
    firecrawl_key = st.session_state.get("firecrawl_key") or os.getenv("FIRECRAWL_API_KEY")

    if openrouter_key and "xxxx" not in openrouter_key:
        llm.init(openrouter_key, config, verbose=False)
        st.session_state["openrouter_ok"] = True
    else:
        st.session_state["openrouter_ok"] = False

    if firecrawl_key and "xxxx" not in firecrawl_key:
        researcher.init(firecrawl_key)
        st.session_state["firecrawl_ok"] = True
    else:
        st.session_state["firecrawl_ok"] = False

    st.session_state["services_initialized"] = True


# --- Page config ---
st.set_page_config(
    page_title="LinkedIn Ghost Writer",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

_init_services()

# --- Sidebar ---
st.sidebar.title("✍️ Ghost Writer")

# Context selector
contexts = loader.list_contexts()
if contexts:
    active = st.sidebar.selectbox(
        "Contexte actif",
        contexts,
        index=0,
        key="active_context",
    )
else:
    st.sidebar.warning("Aucun contexte trouvé.")
    if st.sidebar.button("Créer mon contexte"):
        st.switch_page("pages/1_onboarding.py")
    active = None

# API status
st.sidebar.markdown("---")
st.sidebar.markdown("**API Status**")
or_ok = st.session_state.get("openrouter_ok", False)
fc_ok = st.session_state.get("firecrawl_ok", False)
st.sidebar.markdown(f"{'🟢' if or_ok else '🔴'} OpenRouter")
st.sidebar.markdown(f"{'🟢' if fc_ok else '🔴'} Firecrawl")

if not or_ok:
    st.sidebar.caption("Configurez vos clés dans Settings.")

# --- Main page ---
st.title("LinkedIn Ghost Writer")
st.markdown("Générez des posts LinkedIn optimisés pour votre audience.")

if not contexts:
    st.info("Bienvenue ! Commencez par configurer vos clés API dans **Settings**, puis créez votre contexte dans **Onboarding**.")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📋 Onboarding")
    st.markdown("Configurez votre ICP, voix, piliers et funnel.")
    if st.button("Commencer", key="goto_onboarding"):
        st.switch_page("pages/1_onboarding.py")

with col2:
    st.markdown("### ✍️ Générer")
    st.markdown("Créez des posts LinkedIn scorés et rankés.")
    if st.button("Générer un post", key="goto_generate"):
        st.switch_page("pages/2_generate.py")

with col3:
    st.markdown("### 📊 Historique")
    st.markdown("Consultez vos posts passés et analytics.")
    if st.button("Voir l'historique", key="goto_history"):
        st.switch_page("pages/3_history.py")
