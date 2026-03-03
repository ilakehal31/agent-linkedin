"""Settings — Clés API, gestion des contextes, exemples."""

import os
import shutil
from pathlib import Path

import streamlit as st

from agent import llm, researcher
from memory import loader

CONTEXTS_DIR = Path(__file__).parent.parent / "memory" / "contexts"

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings")

# --- API Keys ---
st.subheader("Clés API")

or_key = st.text_input(
    "OpenRouter API Key",
    value=st.session_state.get("openrouter_key", os.getenv("OPENROUTER_API_KEY", "")),
    type="password",
)
fc_key = st.text_input(
    "Firecrawl API Key",
    value=st.session_state.get("firecrawl_key", os.getenv("FIRECRAWL_API_KEY", "")),
    type="password",
)

if st.button("Sauvegarder les clés"):
    config = st.session_state.get("config")
    if not config:
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        st.session_state["config"] = config

    if or_key and "xxxx" not in or_key:
        st.session_state["openrouter_key"] = or_key
        llm.init(or_key, config, verbose=False)
        st.session_state["openrouter_ok"] = True
    else:
        st.session_state["openrouter_ok"] = False

    if fc_key and "xxxx" not in fc_key:
        st.session_state["firecrawl_key"] = fc_key
        researcher.init(fc_key)
        st.session_state["firecrawl_ok"] = True
    else:
        st.session_state["firecrawl_ok"] = False

    # Reset to re-init services on next page load
    st.session_state["services_initialized"] = True
    st.success("Clés sauvegardées pour cette session.")
    st.rerun()

or_ok = st.session_state.get("openrouter_ok", False)
fc_ok = st.session_state.get("firecrawl_ok", False)
st.markdown(f"{'🟢' if or_ok else '🔴'} OpenRouter | {'🟢' if fc_ok else '🔴'} Firecrawl")

st.markdown("---")

# --- Context management ---
st.subheader("Gestion des contextes")

contexts = loader.list_contexts()
if contexts:
    for ctx_name in contexts:
        col1, col2 = st.columns([4, 1])
        col1.markdown(f"**{ctx_name}**")
        if col2.button("Supprimer", key=f"del_{ctx_name}"):
            ctx_dir = CONTEXTS_DIR / ctx_name
            if ctx_dir.exists():
                shutil.rmtree(ctx_dir)
                st.success(f"Contexte '{ctx_name}' supprimé.")
                st.rerun()
else:
    st.info("Aucun contexte. Créez-en un dans Onboarding.")

st.markdown("---")

# --- Examples management ---
st.subheader("Gestion des exemples")

if contexts:
    ctx_for_examples = st.selectbox("Contexte", contexts, key="examples_ctx")
    examples_dir = CONTEXTS_DIR / ctx_for_examples / "examples"

    if examples_dir.exists():
        txt_files = list(examples_dir.rglob("*.txt"))
        txt_files = [f for f in txt_files if f.name != "README.txt"]
        st.caption(f"{len(txt_files)} fichier(s) d'exemple trouvé(s)")
    else:
        st.caption("Pas de dossier examples/")

    uploaded = st.file_uploader(
        "Uploader des exemples (.txt)",
        type=["txt"],
        accept_multiple_files=True,
        key="upload_examples",
    )

    if uploaded:
        examples_dir.mkdir(parents=True, exist_ok=True)
        for f in uploaded:
            target = examples_dir / f.name
            target.write_bytes(f.read())
        st.success(f"{len(uploaded)} fichier(s) uploadé(s) dans {ctx_for_examples}/examples/")
        st.rerun()
