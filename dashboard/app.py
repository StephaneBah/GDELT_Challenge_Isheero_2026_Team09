from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Paramètres URL et Session State
if "initialized_url" not in st.session_state:
    st.session_state["scope"] = st.query_params.get("scope", "Couverture complète")
    roots_str = st.query_params.get("roots", "")
    st.session_state["roots_list"] = [r for r in roots_str.split(",") if r] if roots_str else None
    st.session_state["initialized_url"] = True

st.set_page_config(
    page_title="Observatoire médiatique du Bénin",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

:root {
  --bg: #f6f2ea;
  --paper: #fffdf8;
  --ink: #151515;
  --muted: #5c5c5c;
  --accent: #1e6f78;
  --accent-2: #d18f2b;
  --accent-3: #0d6b3f;
  --shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
}
html, body, [class*="css"] {
  background-color: var(--bg);
  color: var(--ink);
  font-family: 'Space Grotesk', sans-serif;
}
section, .block-container { padding-top: 2rem; }
.hero {
  background: radial-gradient(circle at 10% 20%, rgba(209, 143, 43, 0.25), transparent 45%),
              radial-gradient(circle at 80% 10%, rgba(30, 111, 120, 0.3), transparent 35%),
              linear-gradient(120deg, #fffdf8 0%, #f5efe5 60%, #f0ebe1 100%);
  border-radius: 20px;
  padding: 2.5rem 2.4rem;
  box-shadow: var(--shadow);
  animation: rise 0.7s ease;
}
.hero-eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.2rem;
  font-size: 0.8rem;
  color: var(--accent);
  font-weight: 600;
}
.hero-title {
  font-family: 'Fraunces', serif;
  font-size: 2.6rem;
  font-weight: 700;
  margin: 0.4rem 0 0.6rem;
}
.hero-subtitle {
  color: var(--muted);
  font-size: 1.1rem;
  max-width: 62rem;
}
.section-title {
  font-family: 'Fraunces', serif;
  font-size: 1.6rem;
  font-weight: 600;
  margin-top: 2.2rem;
  margin-bottom: 0.7rem;
}
.callout {
  background: #ffffff;
  border-left: 5px solid var(--accent);
  padding: 1rem 1.2rem;
  border-radius: 12px;
  color: var(--ink);
  box-shadow: var(--shadow);
}
.story-block {
  background: #ffffff;
  border-left: 5px solid var(--accent-2);
  padding: 1rem 1.2rem;
  border-radius: 12px;
  color: var(--ink);
  box-shadow: var(--shadow);
  margin-top: 1.5rem;
  margin-bottom: 1.5rem;
}
.kpi-card {
  background: var(--paper);
  border-radius: 16px;
  padding: 1rem 1.1rem;
  box-shadow: var(--shadow);
}
.kpi-label {
  color: var(--muted);
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08rem;
}
.kpi-value { font-size: 1.7rem; font-weight: 600; margin-top: 0.3rem; }
.kpi-note { color: var(--muted); font-size: 0.85rem; margin-top: 0.2rem; }
.note { color: var(--muted); font-size: 0.9rem; }
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
</style>
""",
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = (BASE_DIR / ".." / "data" / "GDELT_events_benin_2025_cleaned.csv").resolve()

ECONOMIC_CODES_INT = {
    61, 71, 85, 211, 231, 254, 311, 331, 354, 
    1011, 1031, 1054, 1211, 1221, 1244, 1312, 1621, 163
}
DIPLO_CODES_INT = {
    22, 32, 42, 43, 46, 50, 54, 57, 102, 105, 108, 
    125, 126, 134, 135, 161, 164, 165
}
COOP_ROOTS_INT = {3, 4, 5, 6, 7}
CONFLICT_ROOTS_INT = {13, 14, 15, 16, 17, 18, 19, 20}

ROOT_TRANSLATIONS = {
    "MAKE PUBLIC STATEMENT": "Déclarations publiques",
    "APPEAL": "Appels / Demandes",
    "EXPRESS INTENT TO COOPERATE": "Intentions de coopérer",
    "CONSULT": "Consultations / Visites",
    "ENGAGE IN DIPLOMATIC COOPERATION": "Coopération diplomatique",
    "ENGAGE IN MATERIAL COOPERATION": "Coopération matérielle",
    "PROVIDE AID": "Fourniture d'aide",
    "YIELD": "Cessions / Accords",
    "INVESTIGATE": "Enquêtes",
    "DEMAND": "Exigences",
    "DISAPPROVE": "Désapprobations",
    "REJECT": "Rejets / Refus",
    "THREATEN": "Menaces",
    "PROTEST": "Manifestations",
    "EXHIBIT FORCE POSTURE": "Démonstrations de force",
    "REDUCE RELATIONS": "Réductions de relations",
    "COERCE": "Coercitions",
    "ASSAULT": "Agressions",
    "FIGHT": "Combats",
    "USE UNCONVENTIONAL MASS VIOLENCE": "Violences de masse"
}

PIVOT_H1H2 = pd.Timestamp("2025-07-01")
_MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}

def metric_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
<div class="kpi-card">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  <div class="kpi-note">{note}</div>
</div>
""",
        unsafe_allow_html=True,
    )

def safe_mean(series: pd.Series) -> float:
    s = series.dropna()
    return float(s.mean()) if not s.empty else 0.0

def normalize_event_code(series: pd.Series) -> pd.Series:
    code = series.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    return code.where(code != "nan", "")

def normalize_domain(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    raw = value.strip().lower()
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    host = parsed.netloc or parsed.path
    host = host.split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host

def domain_in(domain: str, known_domains: set[str]) -> bool:
    return any(domain == d or domain.endswith(f".{d}") for d in known_domains)

def build_monthly(df: pd.DataFrame) -> pd.DataFrame:
    if "month" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby("month", as_index=False)
        .agg(
            count=("GLOBALEVENTID", "count"),
            avg_tone=("AvgTone", "mean"),
            avg_gold=("GoldsteinScale", "mean"),
        )
        .sort_values("month")
    )

def build_h1h2_partners(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if "event_date" not in df.columns:
        return pd.DataFrame()
    pool = df[~df["actor1_country"].str.lower().isin(["benin", "bénin", "unknown", ""])]
    pool = pool[pool["is_cooperation"] | pool["is_diplomatic"] | pool["is_economic"]]
    h1 = pool[pool["event_date"] < PIVOT_H1H2].groupby("actor1_country")["GLOBALEVENTID"].count()
    h2 = pool[pool["event_date"] >= PIVOT_H1H2].groupby("actor1_country")["GLOBALEVENTID"].count()
    combined = pd.DataFrame({"H1": h1, "H2": h2}).fillna(0).astype(int)
    combined["total"] = combined["H1"] + combined["H2"]
    return combined.sort_values("total", ascending=False).head(n).reset_index()

@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)

    for col in ["AvgTone", "GoldsteinScale", "NumMentions", "NumSources", "NumArticles", "ActionGeo_Lat", "ActionGeo_Long"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "SQLDATE" in df.columns:
        df["event_date"] = pd.to_datetime(df["SQLDATE"].astype(str), errors="coerce")
    elif "MonthYear" in df.columns:
        df["event_date"] = pd.to_datetime(df["MonthYear"].astype(str), format="%Y%m", errors="coerce")
    else:
        df["event_date"] = pd.NaT

    df["month"] = df["event_date"].dt.to_period("M").dt.to_timestamp()

    if "EventRootLabel" in df.columns and "EventRootCode" in df.columns:
        df["event_root"] = df["EventRootLabel"].fillna(df["EventRootCode"].astype(str))
    elif "EventRootLabel" in df.columns:
        df["event_root"] = df["EventRootLabel"]
    elif "EventRootCode" in df.columns:
        df["event_root"] = df["EventRootCode"].astype(str)
    else:
        df["event_root"] = "Inconnu"

    if "QuadClassLabel" in df.columns and "QuadClass" in df.columns:
        df["quad_label"] = df["QuadClassLabel"].fillna(df["QuadClass"].astype(str))
    elif "QuadClassLabel" in df.columns:
        df["quad_label"] = df["QuadClassLabel"]
    elif "QuadClass" in df.columns:
        df["quad_label"] = df["QuadClass"].astype(str)
    else:
        df["quad_label"] = "Inconnu"

    df["event_root"] = df["event_root"].fillna("Inconnu").astype(str).replace(ROOT_TRANSLATIONS)
    df["quad_label"] = df["quad_label"].fillna("Inconnu").astype(str)

    actor1_label = df["Actor1CountryLabel"] if "Actor1CountryLabel" in df.columns else pd.Series([pd.NA] * len(df))
    actor1_code = df["Actor1CountryCode"] if "Actor1CountryCode" in df.columns else pd.Series([pd.NA] * len(df))
    df["actor1_country"] = actor1_label.fillna(actor1_code).fillna("Inconnu").replace("", "Inconnu")

    root_codes = pd.to_numeric(df["EventRootCode"], errors="coerce").fillna(-1).astype(int) if "EventRootCode" in df.columns else pd.Series([-1] * len(df))
    event_codes = pd.to_numeric(df["EventCode"], errors="coerce").fillna(-1).astype(int) if "EventCode" in df.columns else pd.Series([-1] * len(df))

    df["is_economic"] = event_codes.isin(ECONOMIC_CODES_INT)
    df["is_diplomatic"] = event_codes.isin(DIPLO_CODES_INT) | root_codes.isin({4, 5})
    df["is_cooperation"] = root_codes.isin(COOP_ROOTS_INT)
    df["is_conflict"] = root_codes.isin(CONFLICT_ROOTS_INT)

    q = df["quad_label"].str.lower()
    df["is_coop_quad"] = q.str.contains("cooper")
    df["is_conf_quad"] = q.str.contains("conflict")

    return df.copy()

@st.cache_data(show_spinner=False)
def apply_filters(
    df: pd.DataFrame,
    scope_filters: list[str],
    date_range,
    selected_roots: list[str],
    selected_actor: list[str],
    hide_unknown: bool,
    tone_range,
    gold_range,
) -> pd.DataFrame:
    view = df.copy()

    effective_scope = [s for s in scope_filters if s != "Couverture complète"]
    if effective_scope:
        mask = False
        if "Économique" in effective_scope:
            mask = mask | view["is_economic"]
        if "Diplomatique" in effective_scope:
            mask = mask | view["is_diplomatic"]
        if "Coopération internationale" in effective_scope:
            mask = mask | view["is_cooperation"]
        if "Conflits" in effective_scope:
            mask = mask | view["is_conflict"]
        view = view[mask]

    if date_range and "event_date" in view.columns:
        start_date, end_date = date_range
        view = view[(view["event_date"] >= pd.Timestamp(start_date)) & (view["event_date"] <= pd.Timestamp(end_date))]

    if selected_roots:
        view = view[view["event_root"].isin(selected_roots)]
    if selected_actor:
        view = view[view["actor1_country"].isin(selected_actor)]
    if hide_unknown:
        view = view[view["actor1_country"].ne("Inconnu")]
    if tone_range:
        view = view[view["AvgTone"].between(tone_range[0], tone_range[1])]
    if gold_range:
        view = view[view["GoldsteinScale"].between(gold_range[0], gold_range[1])]

    return view

if not DATA_PATH.exists():
    st.error(f"Fichier introuvable: {DATA_PATH}")
    st.stop()

df = load_data(DATA_PATH)
px.defaults.template = "simple_white"

st.markdown(
    """
<section class="hero">
    <div class="hero-eyebrow">Observatoire médiatique</div>
    <div class="hero-title">Comment le monde raconte le Bénin en 2025</div>
    <div class="hero-subtitle">
        Tableau de bord interactif analysant la perception, la stabilité et les dynamiques thématiques à partir de la base GDELT. Sélectionnez une portée (économie, diplomatie, conflits) pour cibler votre analyse et explorer le narratif médiatique.
    </div>
</section>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="story-block">
    L'image d'un pays se construit par les faits et leur résonance dans les médias. 
    Plutôt que de simples volumes, ce dashboard décrypte la <strong>tonalité</strong> des articles 
    et les <strong>signaux de stabilité</strong>. L'objectif est de dégager des insights sur les 
    leviers (coopération, économie) qui façonnent la perception internationale du Bénin.
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Filtres")
    scope_options = [
        "Couverture complète",
        "Économique",
        "Diplomatique",
        "Coopération internationale",
        "Conflits",
    ]
    # Initialisation de la portée
    if st.session_state.get("scope") not in scope_options:
        st.session_state["scope"] = "Couverture complète"
        
    selected_scope = st.selectbox("Portée", options=scope_options, key="scope")
    scope_filters = [selected_scope]
    st.query_params["scope"] = selected_scope

    if df["event_date"].notna().any():
        min_date = df["event_date"].min().date()
        max_date = df["event_date"].max().date()
        date_range = st.slider(
            "Période",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD",
        )
    else:
        date_range = None

    root_options = sorted(df["event_root"].dropna().unique().tolist())
    
    # Initialisation des roots à partir de l'URL
    if st.session_state.get("roots_list") is not None:
        preferred = [r for r in root_options if r in st.session_state["roots_list"]]
        st.session_state["roots_widget"] = preferred
        st.session_state["roots_list"] = None
    elif "roots_widget" not in st.session_state:
        st.session_state["roots_widget"] = []

    selected_roots = st.multiselect(
        "Types d’événements", 
        options=root_options, 
        key="roots_widget",
        placeholder="Tous les types (cliquez pour filtrer)"
    )
    st.query_params["roots"] = ",".join(selected_roots)

    actor_options = sorted(df["actor1_country"].dropna().unique().tolist())
    selected_actor = st.multiselect(
        "Pays le plus cité (acteur principal)",
        options=actor_options,
        default=[],
        help="Laissez vide pour tout garder.",
    )

    hide_unknown = st.checkbox("Masquer les valeurs inconnues", value=False)

    tone_range = None
    if df["AvgTone"].notna().any():
        tone_min = float(df["AvgTone"].min())
        tone_max = float(df["AvgTone"].max())
        if tone_min < tone_max:
            tone_range = st.slider(
                "Plage AvgTone",
                min_value=round(tone_min, 2),
                max_value=round(tone_max, 2),
                value=(round(tone_min, 2), round(tone_max, 2)),
            )
        else:
            tone_range = (round(tone_min, 2), round(tone_max, 2))

    gold_range = None
    if df["GoldsteinScale"].notna().any():
        gold_min = float(df["GoldsteinScale"].min())
        gold_max = float(df["GoldsteinScale"].max())
        if gold_min < gold_max:
            gold_range = st.slider(
                "Plage GoldsteinScale",
                min_value=round(gold_min, 2),
                max_value=round(gold_max, 2),
                value=(round(gold_min, 2), round(gold_max, 2)),
            )
        else:
            gold_range = (round(gold_min, 2), round(gold_max, 2))

df_view = apply_filters(
    df=df,
    scope_filters=scope_filters,
    date_range=date_range,
    selected_roots=selected_roots,
    selected_actor=selected_actor,
    hide_unknown=hide_unknown,
    tone_range=tone_range,
    gold_range=gold_range,
)

if df_view.empty:
    st.warning("Aucune donnée pour ces filtres. Élargissez la sélection.")
    st.stop()

avg_tone = safe_mean(df_view["AvgTone"])
avg_gold = safe_mean(df_view["GoldsteinScale"])
biz_share = float(df_view["is_economic"].mean()) if "is_economic" in df_view.columns else 0.0
coop_share = float((df_view["quad_label"].str.contains("Cooperation", na=False)).mean())

gold_norm = min(max((avg_gold + 10) / 20, 0), 1)  # GoldsteinScale ∈ [-10, 10] → [0, 1]
tone_norm = min(max((avg_tone + 20) / 40, 0), 1)  # AvgTone ∈ [-20, 20] → [0, 1]
attract_score = round(coop_share * 35 + biz_share * 25 + gold_norm * 25 + tone_norm * 15, 1)


kpi_cols = st.columns(6)
with kpi_cols[0]:
    metric_card("Volume", f"{len(df_view):,}", "Événements filtrés")
with kpi_cols[1]:
    metric_card("AvgTone", f"{avg_tone:.2f}", "Sentiment media")
with kpi_cols[2]:
    metric_card("Goldstein", f"{avg_gold:.2f}", "Signal de stabilite")
with kpi_cols[3]:
    metric_card("Coopération", f"{coop_share:.0%}", "Actions pacifiques")
with kpi_cols[4]:
    metric_card("Économie", f"{biz_share:.0%}", "Actions économiques")
with kpi_cols[5]:
    metric_card("Score attractivité", f"{attract_score:.1f} / 100", "Indice composite")


st.markdown(
    """
<div class="callout">
AvgTone mesure la tonalite des articles, tandis que GoldsteinScale estime
l'impact theorique sur la stabilite geopolitique. Un ton negatif avec un
Goldstein positif signale souvent une couverture critique d'actions stables.
</div>
""",
    unsafe_allow_html=True,
)

# 1) Vue d'ensemble: coopération vs conflits (labels non techniques)
st.markdown("<div class='section-title'>Nature des événements couverts</div>", unsafe_allow_html=True)
cc_pool = df_view[df_view["is_coop_quad"] | df_view["is_conf_quad"]]
if cc_pool.empty:
    st.info("Aucun événement coopératif ou conflictuel dans la sélection.")
else:
    coop_count = int(cc_pool["is_coop_quad"].sum())
    conf_count = int(cc_pool["is_conf_quad"].sum())
    part_df = pd.DataFrame(
        {"Catégorie": ["Coopération", "Conflit"], "Volume": [coop_count, conf_count]}
    )
    c1, c2 = st.columns([1, 1])
    with c1:
        fig = px.pie(
            part_df,
            names="Catégorie",
            values="Volume",
            hole=0.55,
            color="Catégorie",
            color_discrete_map={"Coopération": "#1e6f78", "Conflit": "#d18f2b"},
            title="Répartition des dynamiques",
        )
        fig.update_layout(height=340)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        monthly_cc = (
            cc_pool.groupby("month", as_index=False)
            .agg(cooperation=("is_coop_quad", "sum"), conflit=("is_conf_quad", "sum"))
            .sort_values("month")
        )
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Coopération", x=monthly_cc["month"], y=monthly_cc["cooperation"], marker_color="#1e6f78"))
        fig.add_trace(go.Bar(name="Conflit", x=monthly_cc["month"], y=monthly_cc["conflit"], marker_color="#d18f2b"))
        fig.update_layout(barmode="stack", height=340, title="Évolution mensuelle des dynamiques", xaxis_title="", yaxis_title="Événements")
        st.plotly_chart(fig, use_container_width=True)

# 2) Couverture dans le temps
st.markdown("<div class='section-title'>Rythme de la couverture dans le temps</div>", unsafe_allow_html=True)
monthly = build_monthly(df_view)
if not monthly.empty:
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            monthly,
            x="month",
            y="count",
            color="count",
            color_continuous_scale=["#f1d9b1", "#d18f2b"],
            title="Volume mensuel",
        )
        fig.update_layout(height=350, xaxis_title="", yaxis_title="Événements")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        monthly_plot = monthly.rename(columns={"avg_tone": "Tonalité", "avg_gold": "Stabilité"})
        fig = px.line(
            monthly_plot,
            x="month",
            y=["Tonalité", "Stabilité"],
            markers=True,
            title="Tonalité et impact",
            color_discrete_map={"Tonalité": "#d18f2b", "Stabilité": "#1e6f78"},
        )
        fig.update_layout(height=350, xaxis_title="", yaxis_title="Niveau", legend_title="Indicateur")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("<div class='section-title'>Analyse Thématique : Perception et Stabilité</div>", unsafe_allow_html=True)
root_summary = (
    df_view.groupby("event_root", as_index=False)
    .agg(
        count=("GLOBALEVENTID", "count"),
        avg_tone=("AvgTone", "mean"),
        avg_gold=("GoldsteinScale", "mean")
    )
    .sort_values("count", ascending=False)
)
attr_summary = root_summary.copy()

left, right = st.columns([1.1, 1])
with left:
    fig = px.bar(
        attr_summary.head(12),
        x="event_root",
        y="count",
        color="avg_tone",
        color_continuous_scale=["#d18f2b", "#1e6f78"],
        labels={"event_root": "Thématique", "count": "Volume", "avg_tone": "Tonalité"},
        title="Thèmes les plus médiatisés et leur tonalité",
    )
    fig.update_layout(height=360, xaxis_title="", yaxis_title="Événements")
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = px.scatter(
        root_summary.head(14),
        x="avg_tone",
        y="avg_gold",
        size="count",
        color="count",
        hover_name="event_root",
        labels={"avg_tone": "Tonalité", "avg_gold": "Stabilité", "count": "Volume", "event_root": "Thématique"},
        title="Perception vs stabilité (Thématiques)",
        color_continuous_scale="Teal",
    )
    fig.update_layout(height=360)
    st.plotly_chart(fig, use_container_width=True)

if not root_summary.empty:
    top_attr = attr_summary.iloc[0] if not attr_summary.empty else None
    if top_attr is not None:
        tone_label = "positif" if top_attr["avg_tone"] > 0 else "légèrement négatif" if top_attr["avg_tone"] > -1 else "négatif"
        st.markdown(
            f"""
<div class="story-block">
  Le levier d'attractivité dominant est <strong>{top_attr['event_root']}</strong>
  ({int(top_attr['count']):,} événements, ton {tone_label} à {top_attr['avg_tone']:+.2f}).
  Le graphique "Perception vs Stabilité" permet de repérer les thèmes à la fois bien perçus
  <em>et</em> stabilisateurs — le quadrant supérieur-droit est le plus porteur
  pour l'image d'attractivité du Bénin.
</div>
""",
            unsafe_allow_html=True,
        )

# 3) Selon la portée choisie
effective_scope = [s for s in scope_filters if s != "Couverture complète"]

if not effective_scope or "Économique" in effective_scope:
    st.markdown("<div class='section-title'>Focus économie</div>", unsafe_allow_html=True)
    eco = df_view[df_view["is_economic"]]
    if eco.empty:
        st.info("Aucun événement économique dans la sélection.")
    else:
        eco_root = (
            eco.groupby("event_root", as_index=False)
            .agg(volume=("GLOBALEVENTID", "count"))
            .sort_values("volume", ascending=False)
            .head(12)
        )
        fig = px.bar(
            eco_root,
            x="event_root",
            y="volume",
            color="volume",
            color_continuous_scale=["#f1d9b1", "#1e6f78"],
            title="Actions économiques les plus couvertes",
        )
        fig.update_layout(height=360, xaxis_title="Type d’action", yaxis_title="Événements")
        st.plotly_chart(fig, use_container_width=True)

if not effective_scope or "Diplomatique" in effective_scope or "Coopération internationale" in effective_scope:
    st.markdown("<div class='section-title'>Focus relations internationales</div>", unsafe_allow_html=True)
    partner_pool = df_view[df_view["is_cooperation"] | df_view["is_diplomatic"]]
    if partner_pool.empty:
        st.info("Aucune donnée de relation internationale dans la sélection.")
    else:
        country_stats = (
            partner_pool[~partner_pool["actor1_country"].str.lower().isin(["benin", "bénin", "inconnu", "unknown", ""])]
            .groupby("actor1_country", as_index=False)
            .agg(volume=("GLOBALEVENTID", "count"), tonalite=("AvgTone", "mean"))
            .sort_values("volume", ascending=False)
            .head(12)
        )
        c1, c2 = st.columns(2)
        with c1:
            fig = px.choropleth(
                country_stats,
                locations="actor1_country",
                locationmode="country names",
                color="volume",
                hover_name="actor1_country",
                hover_data={"tonalite": ":.2f"},
                color_continuous_scale=["#f1d9b1", "#1e6f78"],
                title="Pays les plus présents dans la couverture",
            )
            fig.update_layout(height=400, geo=dict(showframe=False, showcoastlines=True))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.bar(
                country_stats,
                x="actor1_country",
                y="volume",
                color="volume",
                color_continuous_scale="RdYlGn",
                title="Top partenaires — détail",
            )
            fig.update_layout(height=320, xaxis_title="Pays partenaire", yaxis_title="Événements")
            st.plotly_chart(fig, use_container_width=True)



if "Conflits" in effective_scope and "Coopération internationale" not in effective_scope:
    st.markdown("<div class='section-title'>Focus conflits</div>", unsafe_allow_html=True)
    conf = df_view[df_view["is_conf_quad"]]
    if conf.empty:
        st.info("Aucun événement conflictuel dans la sélection.")
    else:
        conf_root = (
            conf.groupby("event_root", as_index=False)
            .agg(volume=("GLOBALEVENTID", "count"))
            .sort_values("volume", ascending=False)
            .head(12)
        )
        fig = px.bar(
            conf_root,
            x="event_root",
            y="volume",
            color="volume",
            color_continuous_scale=["#f7c6c7", "#b71c1c"],
            title="Types d’événements conflictuels les plus couverts",
        )
        fig.update_layout(height=360, xaxis_title="Type d’action", yaxis_title="Événements")
        st.plotly_chart(fig, use_container_width=True)

st.markdown(
    "<div class='note'>Source des données: data/GDELT_events_benin_2025_cleaned.csv</div>",
    unsafe_allow_html=True,
)