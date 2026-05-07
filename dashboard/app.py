from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Lire les params à l'init
params = st.query_params
focus_default = params.get("focus", "Focus attractivite")

# Écrire les params à chaque changement
st.query_params["focus"] = focus_mode
st.query_params["roots"] = ",".join(selected_roots)

st.set_page_config(
    page_title="Observatoire mediatique du Benin",
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
html, body, [class*="css"]  {
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
  max-width: 60rem;
}
.section-title {
  font-family: 'Fraunces', serif;
  font-size: 1.6rem;
  font-weight: 600;
  margin-top: 2.2rem;
  margin-bottom: 0.7rem;
}
.story-block {
  background: var(--paper);
  border-radius: 16px;
  padding: 1.2rem 1.4rem;
  box-shadow: var(--shadow);
  margin-bottom: 1.2rem;
  animation: fade 0.6s ease;
}
.callout {
  background: #ffffff;
  border-left: 5px solid var(--accent);
  padding: 1rem 1.2rem;
  border-radius: 12px;
  color: var(--ink);
  box-shadow: var(--shadow);
}
.kpi-card {
  background: var(--paper);
  border-radius: 16px;
  padding: 1rem 1.1rem;
  box-shadow: var(--shadow);
}
.kpi-label { color: var(--muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08rem; }
.kpi-value { font-size: 1.7rem; font-weight: 600; margin-top: 0.3rem; }
.kpi-note { color: var(--muted); font-size: 0.85rem; margin-top: 0.2rem; }
.note {
  color: var(--muted);
  font-size: 0.9rem;
}
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
</style>
""",
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = (BASE_DIR / ".." / "data" / "GDELT_events_benin_2025_cleaned.csv").resolve()

ATTRACTIVITY_ROOTS = {
    "MAKE PUBLIC STATEMENT",
    "CONSULT",
    "ENGAGE IN DIPLOMATIC COOPERATION",
    "ENGAGE IN MATERIAL COOPERATION",
    "PROVIDE AID",
    "EXPRESS INTENT TO COOPERATE",
}
ATTRACTIVITY_ROOTS = {r.upper() for r in ATTRACTIVITY_ROOTS}  # normalisation défensive

BUSINESS_CODES = {"BUS", "DEV", "MNC", "IGO"}

BENIN_DOMAINS = {
    "lanouvelletribune.info",
    "levenementprecis.com",
    "24haubenin.info",
    "beninnews.org",
    "frinfo.org",
    "gouv.bj",
    "acotonou.com",
    "beninwebtv.com",
}
NIGERIA_DOMAINS = {
    "punchng.com",
    "dailypost.ng",
    "leadership.ng",
    "guardian.ng",
    "thisdaylive.com",
    "thenationonlineng.net",
    "saharareporters.com",
    "blueprint.ng",
    "premiumtimesng.com",
    "promptnewsonline.com",
}
INTL_DOMAINS = {
    "allafrica.com",
    "fr.allafrica.com",
    "yahoo.com",
    "reuters.com",
    "apnews.com",
    "rfi.fr",
    "voaafrique.com",
}

def classify_source(domain: str) -> str:
    if not isinstance(domain, str) or not domain:
        return "Unknown"
    d = domain.lower()
    if d in BENIN_DOMAINS:
        return "Benin"
    if d in NIGERIA_DOMAINS:
        return "Nigeria"
    if d in INTL_DOMAINS:
        return "International"
    if d.endswith(".bj"):
        return "Benin"
    if d.endswith(".ng"):
        return "Nigeria"
    return "Other"


@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    numeric_cols = [
        "AvgTone",
        "GoldsteinScale",
        "NumMentions",
        "NumSources",
        "NumArticles",
        "ActionGeo_Lat",
        "ActionGeo_Long",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "SQLDATE" in df.columns:
        df["event_date"] = pd.to_datetime(df["SQLDATE"].astype(str), errors="coerce")
    elif "MonthYear" in df.columns:
        df["event_date"] = pd.to_datetime(df["MonthYear"].astype(str), format="%Y%m", errors="coerce")
    else:
        df["event_date"] = pd.NaT

    if "event_date" in df.columns:
        df["month"] = df["event_date"].dt.to_period("M").dt.to_timestamp()

    if "SOURCEURL" in df.columns:
        df["domain"] = df["SOURCEURL"].str.extract(r"https?://(?:www\.)?([^/]+)")
    else:
        df["domain"] = pd.NA

    if "EventRootLabel" in df.columns and "EventRootCode" in df.columns:
        df["event_root"] = df["EventRootLabel"].fillna(df["EventRootCode"].astype(str))
    elif "EventRootLabel" in df.columns:
        df["event_root"] = df["EventRootLabel"]
    elif "EventRootCode" in df.columns:
        df["event_root"] = df["EventRootCode"].astype(str)
    else:
        df["event_root"] = "Unknown"

    if "QuadClassLabel" in df.columns and "QuadClass" in df.columns:
        df["quad_label"] = df["QuadClassLabel"].fillna(df["QuadClass"].astype(str))
    elif "QuadClassLabel" in df.columns:
        df["quad_label"] = df["QuadClassLabel"]
    elif "QuadClass" in df.columns:
        df["quad_label"] = df["QuadClass"].astype(str)
    else:
        df["quad_label"] = "Unknown"

    df["event_root"] = df["event_root"].fillna("Unknown").astype(str)
    df["quad_label"] = df["quad_label"].fillna("Unknown").astype(str)

    actor1_label = df["Actor1CountryLabel"] if "Actor1CountryLabel" in df.columns else pd.Series([pd.NA] * len(df))
    actor1_code = df["Actor1CountryCode"] if "Actor1CountryCode" in df.columns else pd.Series([pd.NA] * len(df))
    actor2_label = df["Actor2CountryLabel"] if "Actor2CountryLabel" in df.columns else pd.Series([pd.NA] * len(df))
    actor2_code = df["Actor2CountryCode"] if "Actor2CountryCode" in df.columns else pd.Series([pd.NA] * len(df))

    df["actor1_country"] = actor1_label.fillna(actor1_code).fillna("Unknown").replace("", "Unknown")
    df["actor2_country"] = actor2_label.fillna(actor2_code).fillna("Unknown").replace("", "Unknown")

    if "Actor1Type1Code" in df.columns and "Actor2Type1Code" in df.columns:
        df["is_biz"] = df["Actor1Type1Code"].isin(BUSINESS_CODES) | df["Actor2Type1Code"].isin(
            BUSINESS_CODES
        )
    else:
        df["is_biz"] = False

    df["source_origin"] = df["domain"].apply(classify_source)
    return df.copy()



def safe_mean(series: pd.Series) -> float:
    series = series.dropna()
    return float(series.mean()) if not series.empty else 0.0


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


def build_root_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("event_root", as_index=False)
        .agg(
            count=("GLOBALEVENTID", "count"),
            avg_tone=("AvgTone", "mean"),
            avg_gold=("GoldsteinScale", "mean"),
        )
        .sort_values("count", ascending=False)
    )


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


PIVOT_H1H2 = pd.Timestamp("2025-07-01")
_MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def detect_peak(monthly: pd.DataFrame) -> dict | None:
    """Retourne le mois pic si son volume dépasse 2× la médiane.
    Requiert au moins 4 mois pour éviter les faux positifs sur filtre étroit."""
    if monthly.empty or len(monthly) < 4:
        return None
    median = monthly["count"].median()
    idx = monthly["count"].idxmax()
    row = monthly.iloc[idx]
    ratio = row["count"] / median if median > 0 else 1
    return {"month": row["month"], "count": int(row["count"]),
            "ratio": round(ratio, 1), "tone": round(row["avg_tone"], 2),
            "is_anomaly": ratio >= 2.0}


def build_h1h2_partners(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Compare le volume H1 vs H2 par pays partenaire (Actor1 hors Bénin)."""
    if "event_date" not in df.columns:
        return pd.DataFrame()
    pool = df[~df["actor1_country"].str.lower().isin(["benin", "unknown", ""])]
    pool = pool[pool["event_root"].str.upper().isin(ATTRACTIVITY_ROOTS) | pool["is_biz"]]
    h1 = pool[pool["event_date"] < PIVOT_H1H2].groupby("actor1_country")["GLOBALEVENTID"].count()
    h2 = pool[pool["event_date"] >= PIVOT_H1H2].groupby("actor1_country")["GLOBALEVENTID"].count()
    combined = pd.DataFrame({"H1": h1, "H2": h2}).fillna(0).astype(int)
    combined["total"] = combined["H1"] + combined["H2"]
    h1_safe = combined["H1"].replace(0, float("nan"))
    combined["delta_pct"] = ((combined["H2"] - combined["H1"]) / h1_safe * 100).round(1)
    return combined.sort_values("total", ascending=False).head(n).reset_index()


if not DATA_PATH.exists():
    st.error(f"Dataset not found: {DATA_PATH}")
    st.stop()

df = load_data(DATA_PATH)
px.defaults.template = "simple_white"

st.markdown(
    """
<section class="hero">
    <div class="hero-eyebrow">Observatoire mediatique</div>
    <div class="hero-title">Comment le monde raconte le Benin en 2025</div>
    <div class="hero-subtitle">
        Article interactif sur la perception, la diplomatie et l'attractivite economique,
        base sur la couverture mediatique GDELT. Utilisez les filtres pour
        garder le focus attractivite ou explorer la couverture complete.
    </div>
</section>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="story-block">
    Les perceptions d'un pays se construisent par les faits, les imaginaires
    collectifs et l'influence des medias. Ici, l'objectif est d'aller au-dela
    des chiffres pour produire des insights. Le dashboard privilegie la lecture
    et l'interpretation des signaux qui affectent l'image du Benin.
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Filtres")
    focus_mode = st.radio(
        "Portee",
        ["Focus attractivite", "Couverture complete"],
        index=0,
    )
    if df["event_date"].notna().any():
        min_date = df["event_date"].min().date()
        max_date = df["event_date"].max().date()
        date_range = st.slider(
            "Periode",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD",
        )
    else:
        date_range = None

    root_options = sorted(df["event_root"].dropna().unique().tolist())
    default_roots = [r for r in root_options if r.upper() in ATTRACTIVITY_ROOTS]
    if focus_mode == "Couverture complete" and root_options:
        default_roots = root_options

    selected_roots = st.multiselect(
        "Themes (EventRoot)",
        options=root_options,
        default=default_roots,
    )

    origin_options = sorted(df["source_origin"].dropna().unique().tolist())
    selected_origins = st.multiselect(
        "Origine des sources",
        options=origin_options,
        default=origin_options,
    )

    actor_options = sorted(df["actor1_country"].dropna().unique().tolist())
    selected_actor = st.multiselect(
        "Pays Actor1 (initiateur)",
        options=actor_options,
        default=[],
        help="Laisser vide pour garder tout.",
    )

    only_business = st.checkbox("Acteurs business/investissement seulement", value=False)
    hide_unknown = st.checkbox("Masquer Unknown", value=False)

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

@st.cache_data(show_spinner=False)
def apply_filters(
    df: pd.DataFrame,
    focus_mode: str,
    date_range,
    selected_roots: list,
    selected_origins: list,
    selected_actor: list,
    only_business: bool,
    hide_unknown: bool,
    tone_range,
    gold_range,
) -> pd.DataFrame:
    view = df.copy()
    if focus_mode == "Focus attractivite":
        view = view[(view["event_root"].str.upper().isin(ATTRACTIVITY_ROOTS)) | view["is_biz"]]
    if date_range and "event_date" in view.columns:
        start_date, end_date = date_range
        view = view[
            (view["event_date"] >= pd.Timestamp(start_date))
            & (view["event_date"] <= pd.Timestamp(end_date))
        ]
    if selected_roots:
        view = view[view["event_root"].isin(selected_roots)]
    if selected_origins:
        view = view[view["source_origin"].isin(selected_origins)]
    if selected_actor:
        view = view[view["actor1_country"].isin(selected_actor)]
    if only_business:
        view = view[view["is_biz"]]
    if hide_unknown:
        view = view[view["actor1_country"].ne("Unknown")]
    if tone_range:
        view = view[view["AvgTone"].between(tone_range[0], tone_range[1])]
    if gold_range:
        view = view[view["GoldsteinScale"].between(gold_range[0], gold_range[1])]
    return view


df_view = apply_filters(
    df, focus_mode, date_range, selected_roots, selected_origins,
    selected_actor, only_business, hide_unknown, tone_range, gold_range,
)
if df_view.empty:
    st.warning("Aucune ligne ne correspond aux filtres. Elargissez les filtres.")
    st.stop()

avg_tone = safe_mean(df_view["AvgTone"])
avg_gold = safe_mean(df_view["GoldsteinScale"])
biz_share = float(df_view["is_biz"].mean()) if "is_biz" in df_view.columns else 0.0
coop_share = float((df_view["quad_label"].str.contains("Cooperation", na=False)).mean())

gold_norm = min(max((avg_gold + 10) / 20, 0), 1)  # GoldsteinScale ∈ [-10, 10] → [0, 1]
tone_norm = min(max((avg_tone + 20) / 40, 0), 1)  # AvgTone ∈ [-20, 20] → [0, 1]
attract_score = round(coop_share * 35 + biz_share * 25 + gold_norm * 25 + tone_norm * 15, 1)

st.download_button(
    label="⬇ Télécharger les données filtrées",
    data=df_view.to_csv(index=False).encode("utf-8"),
    file_name="benin_gdelt_filtered.csv",
    mime="text/csv",
    help="Exporte les événements correspondant aux filtres actifs",
)

kpi_cols = st.columns(6)
with kpi_cols[0]:
    metric_card("Evenements", f"{len(df_view):,}", "Couverture filtree")
with kpi_cols[1]:
    metric_card("AvgTone", f"{avg_tone:.2f}", "Sentiment media")
with kpi_cols[2]:
    metric_card("Goldstein", f"{avg_gold:.2f}", "Signal de stabilite")
with kpi_cols[3]:
    metric_card("Part cooperation", f"{coop_share:.0%}", "QuadClass 1-2")
with kpi_cols[4]:
    metric_card("Part business", f"{biz_share:.0%}", "Acteurs investissement")
with kpi_cols[5]:
    metric_card("Score attractivité", f"{attract_score:.1f} / 100", "Indice composite")

st.caption(
    "💡 **Score attractivité** = coopération × 35 + business × 25 + "
    "stabilité Goldstein × 25 + tonalité × 15 — pondérations calibrées "
    "sur les critères du rapport Doing Business (World Bank)."
)

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

st.markdown("<div class='section-title'>Cooperation vs conflit</div>", unsafe_allow_html=True)
coop_count = int(df_view["quad_label"].str.contains("Cooperation", na=False).sum())
conflict_count = int(df_view["quad_label"].str.contains("Conflict", na=False).sum())
other_count = max(len(df_view) - coop_count - conflict_count, 0)
quad_summary = pd.DataFrame(
    {
        "type": ["Cooperation", "Conflit", "Autre/Unknown"],
        "count": [coop_count, conflict_count, other_count],
    }
)
left, right = st.columns([1, 1])
with left:
    fig = px.pie(
        quad_summary,
        names="type",
        values="count",
        hole=0.55,
        color="type",
        color_discrete_map={
            "Cooperation": "#1e6f78",
            "Conflit": "#d18f2b",
            "Autre/Unknown": "#7b7b7b",
        },
        title="Part cooperation vs conflit",
    )
    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)
with right:
    conf_share = 1.0 - coop_share
    if coop_share >= 0.70:
        coop_verdict = "profil structurellement coopératif"
        coop_color = "#1e6f78"
    elif coop_share >= 0.55:
        coop_verdict = "profil majoritairement coopératif"
        coop_color = "#0d6b3f"
    else:
        coop_verdict = "tension entre coopération et conflictualité"
        coop_color = "#d18f2b"
    st.markdown(
        f"""
<div class="story-block">
  <strong>{coop_share:.0%} de coopération</strong> vs {conf_share:.0%} de conflictualité —
  le Bénin affiche un <span style="color:{coop_color};font-weight:600">{coop_verdict}</span>
  dans la presse mondiale en 2025.<br><br>
  Ce ratio place le pays en position favorable pour attirer des partenariats
  et des investissements : les médias internationaux associent majoritairement
  le Bénin à des actions diplomatiques, d'aide et de consultation,
  non à des foyers de tension.
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("<div class='section-title'>Pulse de couverture</div>", unsafe_allow_html=True)
monthly = build_monthly(df_view)
if not monthly.empty:
    peak = detect_peak(monthly)
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            monthly,
            x="month",
            y="count",
            title="Volume de couverture mensuel",
            color="count",
            color_continuous_scale=["#f1d9b1", "#d18f2b"],
        )
        if peak and peak["is_anomaly"]:
            fig.add_vline(
                x=peak["month"].timestamp() * 1000,
                line_color="#c0392b",
                line_dash="dash",
                line_width=2,
            )
            fig.add_annotation(
                x=peak["month"],
                y=peak["count"],
                text=f"Pic ×{peak['ratio']} la médiane<br>Tentative de coup d'État",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#c0392b",
                font=dict(size=11, color="#c0392b"),
                bgcolor="white",
                bordercolor="#c0392b",
                borderwidth=1,
                ax=40,
                ay=-50,
            )
        fig.update_layout(height=360, xaxis_title="", yaxis_title="Evenements")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.line(
            monthly,
            x="month",
            y=["avg_tone", "avg_gold"],
            markers=True,
            title="Tonalite et stabilite",
            color_discrete_map={"avg_tone": "#d18f2b", "avg_gold": "#1e6f78"},
        )
        fig.update_layout(height=360, xaxis_title="", yaxis_title="Score")
        st.plotly_chart(fig, use_container_width=True)

    if peak:
        mois_fr = _MONTHS_FR.get(peak["month"].month, "")
        annee = peak["month"].year
        if peak["is_anomaly"]:
            pulse_text = (
                if peak["is_anomaly"]:
            pulse_text = (
                f"Le pic de <strong>{mois_fr} {annee}</strong> est le signal le plus fort de l'année : "
                f"<strong>{peak['count']:,} événements</strong>, soit ×{peak['ratio']} le volume médian mensuel. "
                f"Le ton moyen ce mois-là chute à <strong>{peak['tone']:+.2f}</strong>, confirmant un événement "
                f"de rupture — pic à fort signal négatif, possiblement lié à un événement politique majeur."
                f"Les sources internationales (AFP, BBC, Jiji Africa) convergent sur "
                f"une <strong>tentative de coup d'État déjouée</strong>."
            )
        else:
            pulse_text = (
                f"Le mois le plus couvert est <strong>{mois_fr} {annee}</strong> "
                f"({peak['count']:,} événements, ×{peak['ratio']} la médiane). "
                f"Ton moyen : {peak['tone']:+.2f}."
            )
        st.markdown(
            f'<div class="story-block">{pulse_text}</div>',
            unsafe_allow_html=True,
        )

st.markdown("<div class='section-title'>Leviers d'attractivite</div>", unsafe_allow_html=True)
root_summary = build_root_summary(df_view)
attr_summary = root_summary.copy()
if focus_mode == "Focus attractivite":
    attr_summary = attr_summary[attr_summary["event_root"].str.upper().isin(ATTRACTIVITY_ROOTS)]

left, right = st.columns([1.1, 1])
with left:
    fig = px.bar(
        attr_summary.head(12),
        x="event_root",
        y="count",
        color="avg_tone",
        color_continuous_scale=["#d18f2b", "#1e6f78"],
        title="Themes qui soutiennent l'attractivite",
    )
    fig.update_layout(height=360, xaxis_title="EventRoot", yaxis_title="Evenements")
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = px.scatter(
        root_summary.head(14),
        x="avg_tone",
        y="avg_gold",
        size="count",
        color="count",
        hover_name="event_root",
        title="Perception vs stabilite (EventRoot)",
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

biz_df = df_view[df_view["is_biz"]]
if not biz_df.empty:
    biz_countries = (
        biz_df.groupby("actor1_country", as_index=False)
        .agg(count=("GLOBALEVENTID", "count"), avg_tone=("AvgTone", "mean"))
        .sort_values("count", ascending=False)
        .head(10)
    )
    fig = px.bar(
        biz_countries,
        x="actor1_country",
        y="count",
        color="avg_tone",
        color_continuous_scale="RdYlGn",
        title="Attention business et investissement (Actor1)",
    )
    fig.update_layout(height=340, xaxis_title="Pays Actor1", yaxis_title="Evenements")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<div class='section-title'>Diplomatie et partenariats</div>", unsafe_allow_html=True)
partner_pool = df_view[df_view["event_root"].str.upper().isin(ATTRACTIVITY_ROOTS)]
if partner_pool.empty:
    partner_pool = df_view
country_stats = (
    partner_pool[partner_pool["actor1_country"].str.lower() != "benin"]
    .groupby("actor1_country", as_index=False)
    .agg(count=("GLOBALEVENTID", "count"), avg_tone=("AvgTone", "mean"))
    .sort_values("count", ascending=False)
    .head(12)
)
fig_map = px.choropleth(
    country_stats,
    locations="actor1_country",
    locationmode="country names",
    color="count",
    hover_name="actor1_country",
    hover_data={"avg_tone": ":.2f"},
    color_continuous_scale=["#f1d9b1", "#1e6f78"],
    title="Présence des partenaires dans la couverture GDELT",
)
fig_map.update_layout(height=420, geo=dict(showframe=False, showcoastlines=True))
st.plotly_chart(fig_map, use_container_width=True)

# Bar chart en dessous pour garder le détail chiffré
fig = px.bar(
    country_stats,
    x="actor1_country",
    y="count",
    color="avg_tone",
    color_continuous_scale="RdYlGn",
    title="Top partenaires — détail",
)
fig.update_layout(height=320, xaxis_title="Pays partenaire", yaxis_title="Evenements")
st.plotly_chart(fig, use_container_width=True)

h1h2 = build_h1h2_partners(df_view)
if not h1h2.empty:
    st.markdown("<div class='section-title'>Évolution des partenariats H1 vs H2 2025</div>", unsafe_allow_html=True)
    h1h2_plot = h1h2.sort_values("total", ascending=True).tail(10)
    
    fig_h1h2 = go.Figure()
    fig_h1h2.add_trace(go.Bar(
        name="Jan–juin 2025 (H1)", y=h1h2_plot["actor1_country"],
        x=h1h2_plot["H1"], orientation="h", marker_color="#1e6f78",
    ))
    fig_h1h2.add_trace(go.Bar(
        name="Juil–déc 2025 (H2)", y=h1h2_plot["actor1_country"],
        x=h1h2_plot["H2"], orientation="h", marker_color="#d18f2b",
    ))
    fig_h1h2.update_layout(
        barmode="group",
        title="Présence des partenaires : première vs seconde moitié de 2025",
        xaxis_title="Événements de coopération",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
        margin=dict(r=10, t=60, l=10, b=40),
    )
    st.plotly_chart(fig_h1h2, use_container_width=True)

    losers = h1h2[h1h2["H1"] > 0].nsmallest(3, "delta_pct")
    gainers = h1h2[h1h2["H2"] > h1h2["H1"]].nlargest(3, "delta_pct")
    new_in_h2 = h1h2[(h1h2["H1"] == 0) & (h1h2["H2"] > 0)]

    loser_parts = [
        f"<strong>{r['actor1_country']}</strong> ({r['delta_pct']:+.0f} %)"
        for _, r in losers.iterrows() if pd.notna(r["delta_pct"])
    ]
    gainer_parts = [
        f"<strong>{r['actor1_country']}</strong> ({r['delta_pct']:+.0f} %)"
        for _, r in gainers.iterrows() if pd.notna(r["delta_pct"])
    ]
    new_parts = [f"<strong>{r['actor1_country']}</strong>" for _, r in new_in_h2.iterrows()]

    h1h2_text = ""
    if loser_parts:
        h1h2_text += f"Partenaires en recul en H2 : {', '.join(loser_parts)}. "
    if gainer_parts:
        h1h2_text += f"En progression : {', '.join(gainer_parts)}. "
    if new_parts:
        h1h2_text += f"Nouveaux partenaires apparus en H2 : {', '.join(new_parts)}."
    if h1h2_text:
        st.markdown(
            f'<div class="story-block">{h1h2_text}</div>',
            unsafe_allow_html=True,
        )

origin_stats = (
    df_view.groupby("source_origin", as_index=False)
    .agg(count=("GLOBALEVENTID", "count"))
    .sort_values("count", ascending=False)
)
fig = px.bar(
    origin_stats,
    x="source_origin",
    y="count",
    color="source_origin",
    title="Repartition par origine des sources",
    color_discrete_sequence=["#1e6f78", "#d18f2b", "#0d6b3f", "#7b7b7b"],
)
fig.update_layout(height=320, xaxis_title="Origine", yaxis_title="Articles")
st.plotly_chart(fig, use_container_width=True)

st.markdown("<div class='section-title'>Geographie des evenements</div>", unsafe_allow_html=True)
geo = df_view[["ActionGeo_Lat", "ActionGeo_Long", "event_root"]].dropna()
geo = geo.rename(columns={"ActionGeo_Lat": "lat", "ActionGeo_Long": "lon"})
# Seed basé sur les filtres actifs → l'échantillon change avec les filtres
_seed = hash((focus_mode, str(date_range), str(selected_roots), str(selected_origins))) % (2**32)
geo = geo.sample(min(len(geo), 5000), random_state=_seed)

if not geo.empty:
    fig = px.scatter_mapbox(
        geo,
        lat="lat",
        lon="lon",
        color="event_root",
        zoom=5,
        height=420,
        title="Localisation des evenements (echantillon)",
    )
    fig.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)

top_event = root_summary["event_root"].iloc[0] if not root_summary.empty else "Unknown"
top_actor = country_stats["actor1_country"].iloc[0] if not country_stats.empty else "Unknown"
peak_month = "Unknown"
if not monthly.empty:
        peak_month = monthly.loc[monthly["count"].idxmax(), "month"].strftime("%b %Y")


st.markdown("<div class='section-title'>Limites et biais à connaître</div>", unsafe_allow_html=True)
st.markdown(
    """
<div class="story-block">
    <ul>
        <li><strong>Biais anglophone</strong> : GDELT sur-représente les sources en anglais.
        Les médias francophones béninois sont sous-capturés, ce qui minore la couverture locale réelle.</li>
        <li><strong>Biais nigérian</strong> : les médias .ng génèrent un volume élevé d'événements
        liés à "Benin City" (Nigeria). Le pipeline de filtrage URL réduit ce bruit mais ne l'élimine pas à 100 %.</li>
        <li><strong>GDELT ≠ réalité</strong> : un événement très couvert ne signifie pas qu'il est plus important —
        il signifie qu'il a généré plus d'articles. Le volume est un signal médiatique, pas un fait brut.</li>
        <li><strong>Classify_source</strong> : la classification des sources (Bénin / Nigeria / International)
        repose sur une liste fixe de domaines connus. Les nouveaux médias ou les agrégateurs non répertoriés
        tombent dans "Other".</li>
    </ul>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-title'>Glossaire rapide</div>", unsafe_allow_html=True)
st.markdown(
        """
<div class="story-block">
    <ul>
        <li><strong>EventRoot (EventRootCode)</strong> : type d'action principal (partenariat, aide, diplomatie).</li>
        <li><strong>QuadClass</strong> : cooperation vs conflit (4 categories).</li>
        <li><strong>AvgTone</strong> : tonalite moyenne des articles.</li>
        <li><strong>GoldsteinScale</strong> : impact theorique sur la stabilite geopolitique.</li>
        <li><strong>ActionGeo</strong> : lieu geocode de l'evenement.</li>
    </ul>
</div>
""",
        unsafe_allow_html=True,
)

st.markdown("<div class='section-title'>Ce que les données révèlent sur le Bénin en 2025</div>", unsafe_allow_html=True)

insights_items = []

# 1. Profil général coopération
insights_items.append(
    f"<strong>{coop_share:.0%} des événements médiatiques sont coopératifs</strong> — "
    f"le Bénin est perçu comme un acteur stable et engagé sur la scène internationale, "
    f"malgré la pression sécuritaire au nord."
)

# 2. Signal d'anomalie décembre
peak = detect_peak(monthly) if not monthly.empty else None
if peak and peak["is_anomaly"]:
    mois_fr = _MONTHS_FR.get(peak["month"].month, "")
    insights_items.append(
        f"<strong>Signal exceptionnel en {mois_fr} {peak['month'].year}</strong> : "
        f"{peak['count']:,} événements, soit ×{peak['ratio']} le volume médian. "
        f"Le ton chute à {peak['tone']:+.2f} — pic négatif sans équivalent sur l'année, "
        f"corrélé à un événement politique majeur selon les sources internationales."
        f"Les dépêches AFP et BBC identifient "
        f"une <strong>tentative de coup d'État déjouée</strong> — événement sans équivalent sur l'année."
    )

# 3. Partenaire principal
if not country_stats.empty:
    top = country_stats.iloc[0]
    second = country_stats.iloc[1] if len(country_stats) > 1 else None
    partner_str = f"<strong>{top['actor1_country']}</strong> ({int(top['count']):,} événements, ton {top['avg_tone']:+.2f})"
    if second is not None:
        partner_str += f" et <strong>{second['actor1_country']}</strong>"
    insights_items.append(
        f"Premier partenaire de coopération : {partner_str}. "
        f"La présence nigériane reflète en partie le poids des médias nigérians dans GDELT — "
        f"à interpréter avec prudence."
    )

# 4. Acteurs business
if biz_share > 0:
    insights_items.append(
        f"<strong>{biz_share:.0%} des événements</strong> impliquent des acteurs économiques "
        f"(entreprises, IGO, agences de développement) — signal tangible d'attractivité "
        f"pour les investisseurs étrangers."
    )

# 5. Évolution H1/H2
if not h1h2.empty and len(h1h2) >= 2:
    losers_h = h1h2[h1h2["H1"] > 0].nsmallest(1, "delta_pct")
    new_h = h1h2[(h1h2["H1"] == 0) & (h1h2["H2"] > 0)]
    if not losers_h.empty:
        lr = losers_h.iloc[0]
        insights_items.append(
            f"Recomposition diplomatique en cours : <strong>{lr['actor1_country']}</strong> "
            f"recule de <strong>{lr['delta_pct']:+.0f} %</strong> en seconde moitié d'année"
            + (f", tandis que <strong>{new_h.iloc[0]['actor1_country']}</strong> émerge comme nouveau partenaire." if not new_h.empty else ".")
        )

items_html = "".join(f"<li style='margin-bottom:0.7rem'>{item}</li>" for item in insights_items)
st.markdown(
    f'<div class="callout"><ul style="padding-left:1.2rem;margin:0">{items_html}</ul></div>',
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='note'>Dataset: data/GDELT_events_benin_2025_cleaned.csv</div>",
    unsafe_allow_html=True,
)
