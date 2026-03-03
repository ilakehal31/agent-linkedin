"""Onboarding — Création / édition de contexte client."""

import streamlit as st
import yaml
from pathlib import Path

from memory import loader

CONTEXTS_DIR = Path(__file__).parent.parent / "memory" / "contexts"
TEMPLATE_DIR = CONTEXTS_DIR / "_template"


def _load_template(filename: str) -> dict:
    """Charge un fichier YAML du template."""
    path = TEMPLATE_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _load_existing(context_name: str, filename: str) -> dict | None:
    """Charge un YAML existant pour un contexte donné."""
    path = CONTEXTS_DIR / context_name / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None


def _save_yaml(context_name: str, filename: str, data: dict):
    """Sauvegarde un dict en YAML."""
    context_dir = CONTEXTS_DIR / context_name
    context_dir.mkdir(parents=True, exist_ok=True)
    path = context_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _lines_to_list(text: str) -> list[str]:
    """Convertit un text_area (1 par ligne) en liste."""
    return [line.strip() for line in text.strip().split("\n") if line.strip()]


def _list_to_lines(lst: list) -> str:
    """Convertit une liste en texte (1 par ligne)."""
    if not lst:
        return ""
    return "\n".join(str(item) for item in lst)


st.set_page_config(page_title="Onboarding", page_icon="📋", layout="wide")
st.title("📋 Onboarding — Configuration du contexte")

# --- Context selection / creation ---
contexts = loader.list_contexts()
mode = st.radio("Mode", ["Modifier un contexte existant", "Créer un nouveau contexte"], horizontal=True)

if mode == "Créer un nouveau contexte":
    context_name = st.text_input("Nom du contexte", placeholder="mon-client")
    if not context_name:
        st.info("Entrez un nom pour le nouveau contexte.")
        st.stop()
    context_name = context_name.strip().lower().replace(" ", "-")
    editing = False
else:
    if not contexts:
        st.warning("Aucun contexte existant. Créez-en un.")
        st.stop()
    context_name = st.selectbox("Contexte à modifier", contexts)
    editing = True

st.markdown("---")

# --- Tabs for each step ---
tab_icp, tab_voice, tab_pillars, tab_funnel, tab_personal = st.tabs(
    ["1. ICP", "2. Voix", "3. Piliers", "4. Funnel", "5. Personal"]
)

# ===================== ICP =====================
with tab_icp:
    st.subheader("Profil Client Idéal (ICP)")

    existing_icp = _load_existing(context_name, "icp.yaml") if editing else None
    defaults = existing_icp or _load_template("icp.yaml")

    with st.form("icp_form"):
        icp_name = st.text_input("Nom du client / niche", value=defaults.get("name", ""))
        icp_desc = st.text_input("Description courte", value=defaults.get("description", ""))

        st.markdown("**Persona cible**")
        persona = defaults.get("persona", {})
        col1, col2 = st.columns(2)
        with col1:
            p_titre = st.text_input("Titre", value=persona.get("titre", ""))
            p_secteur = st.text_input("Secteur", value=persona.get("secteur", ""))
            p_taille = st.text_input("Taille entreprise", value=persona.get("taille_entreprise", ""))
        with col2:
            p_localisation = st.text_input("Localisation", value=persona.get("localisation", ""))
            p_age = st.text_input("Tranche d'age", value=persona.get("age_range", ""))
            p_tech = st.text_input("Niveau tech", value=persona.get("niveau_tech", ""))

        st.markdown("**Douleurs** (1 par ligne)")
        douleurs = st.text_area("Douleurs", value=_list_to_lines(defaults.get("douleurs", [])), height=120)

        st.markdown("**Objectifs** (1 par ligne)")
        objectifs = st.text_area("Objectifs", value=_list_to_lines(defaults.get("objectifs", [])), height=100)

        st.markdown("**Objections courantes** (1 par ligne)")
        objections = st.text_area("Objections", value=_list_to_lines(defaults.get("objections", [])), height=100)

        st.markdown("**Vocabulaire**")
        vocab = defaults.get("vocabulaire", {})
        vocab_utilise = st.text_input(
            "Mots a utiliser (separés par des virgules)",
            value=", ".join(vocab.get("utilise", [])),
        )
        vocab_evite = st.text_input(
            "Mots a eviter (separés par des virgules)",
            value=", ".join(vocab.get("evite", [])),
        )

        submitted_icp = st.form_submit_button("Sauvegarder ICP")

    if submitted_icp:
        icp_data = {
            "name": icp_name,
            "description": icp_desc,
            "persona": {
                "titre": p_titre,
                "secteur": p_secteur,
                "taille_entreprise": p_taille,
                "localisation": p_localisation,
                "age_range": p_age,
                "niveau_tech": p_tech,
            },
            "douleurs": _lines_to_list(douleurs),
            "objectifs": _lines_to_list(objectifs),
            "objections": _lines_to_list(objections),
            "vocabulaire": {
                "utilise": [w.strip() for w in vocab_utilise.split(",") if w.strip()],
                "evite": [w.strip() for w in vocab_evite.split(",") if w.strip()],
            },
        }
        _save_yaml(context_name, "icp.yaml", icp_data)
        st.success(f"ICP sauvegardé pour '{context_name}'")

# ===================== VOICE =====================
with tab_voice:
    st.subheader("Ton et Style")

    existing_voice = _load_existing(context_name, "voice.yaml") if editing else None
    defaults_v = existing_voice or _load_template("voice.yaml")

    with st.form("voice_form"):
        tutoiement = st.toggle("Tutoiement", value=defaults_v.get("tutoiement", False))
        registre = st.text_input("Registre", value=defaults_v.get("registre", ""))

        longueur_raw = defaults_v.get("longueur_cible", "800-1300 caractères")
        import re
        nums = re.findall(r"\d+", longueur_raw)
        min_l = int(nums[0]) if len(nums) >= 1 else 800
        max_l = int(nums[1]) if len(nums) >= 2 else 1300
        longueur = st.slider("Longueur cible (caractères)", 400, 2000, (min_l, max_l))

        st.markdown("**Style** (1 par ligne)")
        style = st.text_area("Style", value=_list_to_lines(defaults_v.get("style", [])), height=100)

        emojis_conf = defaults_v.get("emojis", {})
        use_emojis = st.toggle("Utiliser des emojis", value=emojis_conf.get("utiliser", False))
        emoji_freq = st.text_input("Fréquence emojis", value=emojis_conf.get("frequence", ""))

        st.markdown("**Interdit** (1 par ligne)")
        interdit = st.text_area("Interdit", value=_list_to_lines(defaults_v.get("interdit", [])), height=100)

        submitted_voice = st.form_submit_button("Sauvegarder Voix")

    if submitted_voice:
        voice_data = {
            "tutoiement": tutoiement,
            "registre": registre,
            "longueur_cible": f"{longueur[0]}-{longueur[1]} caractères",
            "style": _lines_to_list(style),
            "emojis": {
                "utiliser": use_emojis,
                "frequence": emoji_freq,
            },
            "interdit": _lines_to_list(interdit),
        }
        _save_yaml(context_name, "voice.yaml", voice_data)
        st.success(f"Voix sauvegardée pour '{context_name}'")

# ===================== PILLARS =====================
with tab_pillars:
    st.subheader("Piliers de contenu")

    existing_pillars = _load_existing(context_name, "pillars.yaml") if editing else None
    defaults_p = existing_pillars or _load_template("pillars.yaml")
    existing_pillar_list = defaults_p.get("pillars", [])

    with st.form("pillars_form"):
        num_pillars = st.number_input(
            "Nombre de piliers", min_value=2, max_value=6,
            value=min(max(len(existing_pillar_list), 3), 6),
        )

        pillars_data = []
        for i in range(int(num_pillars)):
            st.markdown(f"**Pilier {i+1}**")
            default_pillar = existing_pillar_list[i] if i < len(existing_pillar_list) else {}
            col1, col2 = st.columns([1, 2])
            with col1:
                pname = st.text_input(f"Nom", value=default_pillar.get("name", ""), key=f"pillar_name_{i}")
            with col2:
                pdesc = st.text_input(f"Description", value=default_pillar.get("description", ""), key=f"pillar_desc_{i}")
            psujets = st.text_area(
                f"Sujets exemples (1 par ligne)",
                value=_list_to_lines(default_pillar.get("exemples_sujets", [])),
                height=60,
                key=f"pillar_sujets_{i}",
            )
            pillars_data.append({"name": pname, "desc": pdesc, "sujets": psujets})

        freq = defaults_p.get("frequence_recommandee", {})
        posts_per_week = st.number_input(
            "Posts par semaine", min_value=1, max_value=10,
            value=freq.get("posts_par_semaine", 4),
        )
        distribution = st.text_input(
            "Distribution",
            value=freq.get("distribution", "2 expertise + 1 coulisses + 1 tendances"),
        )

        submitted_pillars = st.form_submit_button("Sauvegarder Piliers")

    if submitted_pillars:
        data = {
            "description": "Les thèmes récurrents autour desquels tourne le contenu",
            "pillars": [
                {
                    "name": p["name"],
                    "description": p["desc"],
                    "exemples_sujets": _lines_to_list(p["sujets"]),
                }
                for p in pillars_data if p["name"]
            ],
            "frequence_recommandee": {
                "posts_par_semaine": int(posts_per_week),
                "distribution": distribution,
            },
        }
        _save_yaml(context_name, "pillars.yaml", data)
        st.success(f"Piliers sauvegardés pour '{context_name}'")

# ===================== FUNNEL =====================
with tab_funnel:
    st.subheader("Configuration du Funnel")

    existing_funnel = _load_existing(context_name, "funnel.yaml") if editing else None
    defaults_f = existing_funnel or _load_template("funnel.yaml")
    funnel_data = defaults_f.get("funnel", {})

    with st.form("funnel_form"):
        stages_data = {}
        for stage in ("tofu", "mofu", "bofu"):
            st.markdown(f"### {stage.upper()}")
            fd = funnel_data.get(stage, {})

            col1, col2 = st.columns(2)
            with col1:
                label = st.text_input("Label", value=fd.get("label", ""), key=f"f_label_{stage}")
                objectif = st.text_input("Objectif", value=fd.get("objectif", ""), key=f"f_obj_{stage}")
                ton = st.text_input("Ton", value=fd.get("ton", ""), key=f"f_ton_{stage}")
            with col2:
                profondeur = st.text_input("Profondeur", value=fd.get("profondeur", ""), key=f"f_prof_{stage}")
                longueur = st.text_input("Longueur", value=fd.get("longueur", ""), key=f"f_long_{stage}")
                cta_style = st.text_input("Style CTA", value=fd.get("cta_style", ""), key=f"f_cta_{stage}")

            regles = st.text_area(
                "Règles (1 par ligne)", height=80,
                value=_list_to_lines(fd.get("regles", [])),
                key=f"f_regles_{stage}",
            )
            stages_data[stage] = {
                "label": label, "objectif": objectif, "ton": ton,
                "profondeur": profondeur, "longueur": longueur,
                "cta_style": cta_style,
                "formats_preferes": fd.get("formats_preferes", []),
                "piliers_preferes": fd.get("piliers_preferes", []),
                "kpis": fd.get("kpis", []),
                "regles": _lines_to_list(regles),
            }

        st.markdown("### Distribution hebdo")
        distrib = defaults_f.get("distribution_hebdo", {"tofu": 2, "mofu": 1, "bofu": 1})
        col1, col2, col3 = st.columns(3)
        with col1:
            d_tofu = st.number_input("TOFU", min_value=0, max_value=7, value=distrib.get("tofu", 2))
        with col2:
            d_mofu = st.number_input("MOFU", min_value=0, max_value=7, value=distrib.get("mofu", 1))
        with col3:
            d_bofu = st.number_input("BOFU", min_value=0, max_value=7, value=distrib.get("bofu", 1))

        submitted_funnel = st.form_submit_button("Sauvegarder Funnel")

    if submitted_funnel:
        data = {
            "funnel": stages_data,
            "distribution_hebdo": {"tofu": int(d_tofu), "mofu": int(d_mofu), "bofu": int(d_bofu)},
        }
        _save_yaml(context_name, "funnel.yaml", data)
        st.success(f"Funnel sauvegardé pour '{context_name}'")

# ===================== PERSONAL =====================
with tab_personal:
    st.subheader("Personal Branding (optionnel)")

    existing_personal = _load_existing(context_name, "personal.yaml") if editing else None
    defaults_pe = existing_personal or {}

    with st.form("personal_form"):
        prenom = st.text_input("Prénom", value=defaults_pe.get("prenom", ""))
        role = st.text_input("Rôle", value=defaults_pe.get("role", ""))
        parcours = st.text_area("Parcours", value=defaults_pe.get("parcours", ""), height=80)

        st.markdown("**Convictions** (1 par ligne)")
        convictions = st.text_area(
            "Convictions",
            value=_list_to_lines(defaults_pe.get("convictions", [])),
            height=80,
        )

        submitted_personal = st.form_submit_button("Sauvegarder Personal")

    if submitted_personal:
        data = {
            "prenom": prenom,
            "role": role,
            "parcours": parcours,
            "convictions": _lines_to_list(convictions),
        }
        _save_yaml(context_name, "personal.yaml", data)
        st.success(f"Personal branding sauvegardé pour '{context_name}'")

    # Also ensure templates.yaml exists (copy from template if not)
    templates_path = CONTEXTS_DIR / context_name / "templates.yaml"
    if not templates_path.exists() and (TEMPLATE_DIR / "templates.yaml").exists():
        import shutil
        (CONTEXTS_DIR / context_name).mkdir(parents=True, exist_ok=True)
        shutil.copy(TEMPLATE_DIR / "templates.yaml", templates_path)
