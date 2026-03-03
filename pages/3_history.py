"""Historique + Analytics des posts LinkedIn."""

import json

import streamlit as st
import pandas as pd

from memory import loader, history

st.set_page_config(page_title="Historique", page_icon="📊", layout="wide")
st.title("📊 Historique & Analytics")

contexts = loader.list_contexts()
if not contexts:
    st.warning("Aucun contexte disponible.")
    st.stop()

context_name = st.session_state.get("active_context", contexts[0])
st.caption(f"Contexte : **{context_name}**")

# --- Funnel distribution ---
st.subheader("Distribution Funnel (7 derniers jours)")
funnel_stats = history.get_funnel_distribution(context_name, days=7)

col1, col2, col3 = st.columns(3)
col1.metric("TOFU", funnel_stats.get("tofu", 0))
col2.metric("MOFU", funnel_stats.get("mofu", 0))
col3.metric("BOFU", funnel_stats.get("bofu", 0))

st.bar_chart(pd.DataFrame({"Posts": funnel_stats}, index=[k.upper() for k in funnel_stats]), height=200)

st.markdown("---")

# --- History table ---
st.subheader("Posts récents")

filter_funnel = st.selectbox("Filtrer par funnel", ["Tous", "TOFU", "MOFU", "BOFU"])

posts = history.get_history(context_name, last=50)

if not posts:
    st.info("Aucun post trouvé pour ce contexte.")
    st.stop()

# Filter
if filter_funnel != "Tous":
    posts = [p for p in posts if (p.get("funnel_stage") or "").upper() == filter_funnel]

if not posts:
    st.info(f"Aucun post {filter_funnel} trouvé.")
    st.stop()

# Build dataframe
df = pd.DataFrame(posts)
df = df.rename(columns={
    "id": "ID",
    "topic": "Sujet",
    "format": "Format",
    "funnel_stage": "Funnel",
    "hook": "Hook",
    "score_total": "Score",
    "user_score": "Note",
    "status": "Status",
    "created_at": "Date",
})

display_cols = ["ID", "Sujet", "Format", "Funnel", "Score", "Note", "Status", "Date"]
available = [c for c in display_cols if c in df.columns]
st.dataframe(df[available], use_container_width=True, hide_index=True)

st.markdown("---")

# --- Best posts ---
st.subheader("Meilleurs posts (par score)")
best = history.get_best_posts(context_name, limit=5)

if best:
    for i, p in enumerate(best, 1):
        with st.expander(f"#{p['id']} — Score user: {p.get('user_score', '-')} | {p.get('topic', '?')}"):
            st.markdown(f"**{p.get('hook', '')}**")
            st.markdown(p.get("body", ""))
            if p.get("cta"):
                st.markdown(f"*{p['cta']}*")
            hashtags = p.get("hashtags")
            if hashtags:
                try:
                    tags = json.loads(hashtags) if isinstance(hashtags, str) else hashtags
                    st.markdown(" ".join(tags))
                except (json.JSONDecodeError, TypeError):
                    st.markdown(str(hashtags))
else:
    st.info("Aucun post avec feedback utilisateur.")

st.markdown("---")

# --- Feedback form ---
st.subheader("Donner un feedback")

with st.form("feedback_form"):
    post_id = st.number_input("ID du post", min_value=1, step=1)
    user_score = st.slider("Note", 1, 10, 7)
    user_note = st.text_input("Commentaire (optionnel)")
    submitted = st.form_submit_button("Enregistrer le feedback")

if submitted:
    post = history.get_post_by_id(int(post_id))
    if not post:
        st.error(f"Post #{post_id} introuvable.")
    else:
        history.update_feedback(int(post_id), user_score, user_note or None)
        st.success(f"Feedback enregistré pour le post #{post_id} ({user_score}/10)")
        st.rerun()
