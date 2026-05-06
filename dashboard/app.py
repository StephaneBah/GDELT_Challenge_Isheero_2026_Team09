from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Benin 2025 - Decision Report",
    layout="wide",
)

st.markdown(
    """
<style>
:root {
  --bg: #f7f4ef;
  --ink: #1b1b1b;
  --muted: #6b6b6b;
  --accent: #1f6f78;
  --accent-2: #c84b31;
}
html, body, [class*="css"]  {
  background-color: var(--bg);
  color: var(--ink);
}
.report-title {
  font-size: 2.2rem;
  font-weight: 700;
  margin-bottom: 0.2rem;
}
.report-subtitle {
  color: var(--muted);
  margin-bottom: 1.5rem;
}
.section-title {
  font-size: 1.4rem;
  font-weight: 700;
  margin-top: 2rem;
  margin-bottom: 0.5rem;
}
.callout {
  background: #ffffff;
  border-left: 4px solid var(--accent);
  padding: 0.8rem 1rem;
  border-radius: 8px;
  color: var(--ink);
}
.note {
  color: var(--muted);
  font-size: 0.9rem;
}
</style>
""",
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = (BASE_DIR / ".." / "data" / "GDELT_events_benin_2025_cleaned.csv").resolve()


@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in [
        "AvgTone",
        "GoldsteinScale",
        "NumMentions",
        "NumSources",
        "NumArticles",
        "ActionGeo_Lat",
        "ActionGeo_Long",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "MonthYear" in df.columns:
        df["MonthYearDate"] = pd.to_datetime(df["MonthYear"] + "-01", errors="coerce")
    return df


def safe_mean(series: pd.Series) -> float:
    series = series.dropna()
    return float(series.mean()) if not series.empty else 0.0


def build_root_summary(df: pd.DataFrame) -> pd.DataFrame:
    root_label = df["EventRootLabel"].fillna(df["EventRootCode"].astype(str))
    out = (
        df.assign(root_label=root_label)
        .groupby("root_label", as_index=False)
        .agg(
            count=("GLOBALEVENTID", "count"),
            avg_tone=("AvgTone", "mean"),
            avg_gold=("GoldsteinScale", "mean"),
        )
        .sort_values("count", ascending=False)
    )
    return out


def build_quad_share(df: pd.DataFrame) -> pd.DataFrame:
    quad = df["QuadClassLabel"].fillna(df["QuadClass"].astype(str))
    out = quad.value_counts(dropna=True).rename_axis("quad").reset_index(name="count")
    total = out["count"].sum()
    out["share"] = out["count"] / total if total else 0.0
    return out


st.markdown("<div class='report-title'>Benin 2025 - Decision Report</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='report-subtitle'>Perception internationale, diplomatie et attractivite economique basees sur GDELT</div>",
    unsafe_allow_html=True,
)

if not DATA_PATH.exists():
    st.error(f"Dataset not found: {DATA_PATH}")
    st.stop()

df = load_data(DATA_PATH)

# Optional time filter
if "MonthYearDate" in df.columns:
    min_date = df["MonthYearDate"].min().date()
    max_date = df["MonthYearDate"].max().date()
    start_date, end_date = st.slider(
        "Periode d'analyse",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM",
    )
    df = df[
        (df["MonthYearDate"] >= pd.Timestamp(start_date))
        & (df["MonthYearDate"] <= pd.Timestamp(end_date))
    ]

# KPIs
avg_tone = safe_mean(df["AvgTone"]) if "AvgTone" in df.columns else 0.0
avg_gold = safe_mean(df["GoldsteinScale"]) if "GoldsteinScale" in df.columns else 0.0
quad_share = build_quad_share(df)
verbal_share = 0.0
if not quad_share.empty:
    verbal = quad_share[quad_share["quad"].str.contains("Verbal Cooperation", na=False)]
    if not verbal.empty:
        verbal_share = float(verbal["share"].iloc[0])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Events", f"{len(df):,}")
col2.metric("AvgTone", f"{avg_tone:.2f}")
col3.metric("Goldstein", f"{avg_gold:.2f}")
col4.metric("Verbal Cooperation", f"{verbal_share:.0%}")

st.markdown(
    "<div class='callout'>Lecture rapide: AvgTone mesure le ton mediatico-editorial, tandis que Goldstein mesure l'impact theorique sur la stabilite. Un AvgTone negatif avec un Goldstein positif indique une couverture critique mais des actions stables.</div>",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-title'>Perception globale</div>", unsafe_allow_html=True)
root_summary = build_root_summary(df).head(12)
fig = px.scatter(
    root_summary,
    x="avg_tone",
    y="avg_gold",
    size="count",
    color="count",
    hover_name="root_label",
    title="Perception vs stabilite (EventRoot)",
    color_continuous_scale="Teal",
)
fig.update_layout(height=420)
st.plotly_chart(fig, use_container_width=True)

st.markdown("<div class='section-title'>Diplomatie: pays les plus engages</div>", unsafe_allow_html=True)
country_stats = (
    df.assign(actor_country=df["Actor1CountryLabel"].fillna(""))
    .query("actor_country != '' and actor_country.str.lower() != 'benin'", engine="python")
    .groupby("actor_country", as_index=False)
    .agg(count=("GLOBALEVENTID", "count"), avg_tone=("AvgTone", "mean"))
    .sort_values("count", ascending=False)
    .head(10)
)
fig = px.bar(
    country_stats,
    x="actor_country",
    y="count",
    color="avg_tone",
    color_continuous_scale="RdYlGn",
    title="Top pays - volume et tonalite moyenne",
)
fig.update_layout(height=420, xaxis_title="Pays", yaxis_title="Events")
st.plotly_chart(fig, use_container_width=True)

st.markdown("<div class='section-title'>Attractivite economique</div>", unsafe_allow_html=True)
attr_roots = {
    "MAKE PUBLIC STATEMENT",
    "CONSULT",
    "ENGAGE IN DIPLOMATIC COOPERATION",
    "ENGAGE IN MATERIAL COOPERATION",
    "PROVIDE AID",
    "EXPRESS INTENT TO COOPERATE",
}
attr_summary = root_summary[root_summary["root_label"].str.upper().isin(attr_roots)]
fig = px.bar(
    attr_summary,
    x="root_label",
    y="count",
    color="avg_tone",
    color_continuous_scale="GnBu",
    title="Actions favorables a l'attractivite (EventRoot)",
)
fig.update_layout(height=400, xaxis_title="EventRoot", yaxis_title="Events")
st.plotly_chart(fig, use_container_width=True)

biz_codes = {"BUS", "DEV", "MNC", "IGO"}
mask_biz = df["Actor1Type1Code"].isin(biz_codes) | df["Actor2Type1Code"].isin(biz_codes)
biz = (
    df[mask_biz]
    .assign(actor_country=df["Actor1CountryLabel"].fillna(""))
    .query("actor_country != '' and actor_country.str.lower() != 'benin'", engine="python")
    .groupby("actor_country", as_index=False)
    .agg(count=("GLOBALEVENTID", "count"), avg_tone=("AvgTone", "mean"))
    .sort_values("count", ascending=False)
    .head(8)
)
fig = px.bar(
    biz,
    x="actor_country",
    y="count",
    color="avg_tone",
    color_continuous_scale="Teal",
    title="Pays lies au business et investissements",
)
fig.update_layout(height=380, xaxis_title="Pays", yaxis_title="Events")
st.plotly_chart(fig, use_container_width=True)

st.markdown("<div class='section-title'>Tendance mensuelle</div>", unsafe_allow_html=True)
if "MonthYearDate" in df.columns:
    monthly = (
        df.groupby("MonthYearDate", as_index=False)
        .agg(count=("GLOBALEVENTID", "count"), avg_tone=("AvgTone", "mean"))
        .sort_values("MonthYearDate")
    )
    fig = px.line(
        monthly,
        x="MonthYearDate",
        y="avg_tone",
        markers=True,
        title="Tonalite moyenne par mois",
    )
    fig.update_layout(height=320, yaxis_title="AvgTone", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        monthly,
        x="MonthYearDate",
        y="count",
        title="Volume de couverture par mois",
    )
    fig.update_layout(height=300, yaxis_title="Events", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<div class='section-title'>Geographie des evenements</div>", unsafe_allow_html=True)
geo = df[["ActionGeo_Lat", "ActionGeo_Long"]].dropna()
geo = geo.rename(columns={"ActionGeo_Lat": "lat", "ActionGeo_Long": "lon"})
geo = geo.sample(min(len(geo), 4000), random_state=7)
if not geo.empty:
    st.map(geo, size=6)

st.markdown("<div class='section-title'>Synthese executive</div>", unsafe_allow_html=True)
st.markdown(
    """
<div class='callout'>
<ul>
  <li>La cooperation verbale domine, ce qui renforce la lecture d'une diplomatie active.</li>
  <li>Les signaux d'attractivite economique sont plus stables que la tonalite globale.</li>
  <li>Les pays voisins restent les plus visibles, avec un role structurant du Nigeria.</li>
</ul>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='note'>Dataset: GDELT_events_benin_2025_cleaned.csv</div>", unsafe_allow_html=True)
