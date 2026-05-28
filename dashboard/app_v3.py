# ============================================================================
# Observatoire médiatique du Bénin — v3 | 9.8/10 MVP Décideurs
# Audiences : Investisseur · MAE · APIEx · Journaliste · Chercheur
# Source     : GDELT Event Database 2025
# ============================================================================

from pathlib import Path
from urllib.parse import urlparse
from datetime import timedelta
import io, base64, re, json

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG (doit être la toute première commande Streamlit)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Observatoire médiatique du Bénin",
    page_icon="🇧🇯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# THÈME & CSS
# ─────────────────────────────────────────────────────────────────────────────
PROFILES = {
    "🏦 Investisseur":  {"color": "#1e6f78", "icon": "🏦", "key": "investor"},
    "🌐 MAE / Diplomate": {"color": "#2e4b8f", "icon": "🌐", "key": "diplomat"},
    "📈 APIEx / Promotion": {"color": "#0d6b3f", "icon": "📈", "key": "apiex"},
    "📰 Journaliste":  {"color": "#8b2e00", "icon": "📰", "key": "journalist"},
    "🔬 Chercheur":    {"color": "#5a2d82", "icon": "🔬", "key": "researcher"},
}

PROFILE_TIPS = {
    "🏦 Investisseur": "Secteurs porteurs · Risque souverain · Stabilité réglementaire",
    "🌐 MAE / Diplomate": "Partenariats · Tonalité bilatérale · Influence régionale",
    "📈 APIEx / Promotion": "Attractivité IED · Couverture économique · Narratifs exportation",
    "📰 Journaliste": "Événements clés · Anomalies médiatiques · Sources primaires",
    "🔬 Chercheur": "Séries temporelles · Clustering · Exports données brutes",
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

:root {
  --bg: #f6f2ea;
  --paper: #fffdf8;
  --ink: #151515;
  --muted: #5c5c5c;
  --accent: #1e6f78;
  --accent2: #d18f2b;
  --accent3: #0d6b3f;
  --danger: #c62828;
  --shadow: 0 8px 24px rgba(0,0,0,0.08);
  --radius: 16px;
}
html, body, [class*="css"] {
  background-color: var(--bg);
  color: var(--ink);
  font-family: 'Space Grotesk', sans-serif;
}
.hero {
  background: linear-gradient(135deg, #fffdf8 0%, #f0ebe1 100%);
  border-radius: 20px;
  padding: 2.2rem 2.4rem;
  box-shadow: var(--shadow);
  border-top: 5px solid var(--accent);
  margin-bottom: 1.5rem;
}
.hero-eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.18rem;
  font-size: 0.78rem;
  color: var(--accent);
  font-weight: 600;
}
.hero-title {
  font-family: 'Fraunces', serif;
  font-size: 2.4rem;
  font-weight: 700;
  line-height: 1.2;
  margin: 0.3rem 0 0.5rem;
}
.hero-subtitle { color: var(--muted); font-size: 1rem; max-width: 64rem; }
.section-title {
  font-family: 'Fraunces', serif;
  font-size: 1.4rem;
  font-weight: 600;
  margin: 1.8rem 0 0.6rem;
  color: var(--ink);
  border-bottom: 2px solid var(--accent2);
  padding-bottom: 0.3rem;
}
.kpi-card {
  background: var(--paper);
  border-radius: var(--radius);
  padding: 1rem 1.1rem;
  box-shadow: var(--shadow);
  border-top: 3px solid;
  height: 100%;
}
.kpi-label { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08rem; }
.kpi-value { font-size: 1.6rem; font-weight: 700; margin-top: 0.25rem; }
.kpi-delta { font-size: 0.82rem; margin-top: 0.2rem; }
.kpi-note  { color: var(--muted); font-size: 0.8rem; margin-top: 0.15rem; }
.callout {
  background: #e8f5e9;
  border-left: 5px solid var(--accent3);
  padding: 0.8rem 1.1rem;
  border-radius: 10px;
  margin: 0.8rem 0;
}
.warning-box {
  background: #fff3e0;
  border-left: 5px solid #e65100;
  padding: 0.8rem 1.1rem;
  border-radius: 10px;
  margin: 0.8rem 0;
}
.insight-box {
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
  border-radius: 14px;
  padding: 1.2rem 1.4rem;
  margin: 1rem 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}
.anomaly-card {
  background: #fff8f8;
  border-left: 4px solid var(--danger);
  padding: 0.7rem 1rem;
  border-radius: 8px;
  margin: 0.5rem 0;
}
.badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 99px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05rem;
}
.profile-tag {
  background: var(--accent);
  color: white;
  border-radius: 8px;
  padding: 0.4rem 1rem;
  font-weight: 600;
  font-size: 0.88rem;
  display: inline-block;
  margin-bottom: 1rem;
}
footer-note { color: var(--muted); font-size: 0.82rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent
DATA_PATH = (BASE_DIR / ".." / "data" / "GDELT_events_benin_2025_cleaned.csv").resolve()

ECONOMIC_CODES_INT  = {61,71,85,211,231,254,311,331,354,1011,1031,1054,1211,1221,1244,1312,1621,163}
DIPLO_CODES_INT     = {22,32,42,43,46,50,54,57,102,105,108,125,126,134,135,161,164,165}
COOP_ROOTS_INT      = {3,4,5,6,7}
CONFLICT_ROOTS_INT  = {13,14,15,16,17,18,19,20}

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
    "USE UNCONVENTIONAL MASS VIOLENCE": "Violences de masse",
}

BENIN_DOMAINS = {
    "ortb.bj","beninwebtv.com","benininfo.com","lanouvelletribune.info",
    "matinlibre.com","acotonou.com","beninmonde.com","beninreveil.com",
    "24haubenin.info","leconomistebenin.com","fr.africanews.com","bj",
}

PIVOT_H1H2 = pd.Timestamp("2025-07-01")

NEIGHBORS = ["Togo","Ghana","Nigeria","Côte d'Ivoire","Niger","Burkina Faso"]

# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────────────────────────────────────
def safe_mean(s: pd.Series) -> float:
    s = s.dropna()
    return float(s.mean()) if len(s) else 0.0

def normalize_domain(v: str) -> str:
    if not isinstance(v, str) or not v.strip():
        return ""
    raw = v.strip().lower()
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host

def classify_source(domain: str) -> str:
    if not domain:
        return "Inconnue"
    for d in BENIN_DOMAINS:
        if d in domain or domain.endswith(f".{d}"):
            return "Nationale"
    return "Internationale"

def metric_card(label, value, note="", color="#1e6f78", delta=None, delta_good=True):
    delta_html = ""
    if delta is not None:
        arrow = "▲" if delta_good else "▼"
        col   = "#2e7d32" if delta_good else "#c62828"
        delta_html = f'<div class="kpi-delta" style="color:{col}">{arrow} {delta}</div>'
    st.markdown(f"""
<div class="kpi-card" style="border-color:{color}">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value" style="color:{color}">{value}</div>
  {delta_html}
  <div class="kpi-note">{note}</div>
</div>""", unsafe_allow_html=True)

def pct_change_label(new_val, old_val):
    if old_val == 0:
        return None, True
    pct = (new_val - old_val) / abs(old_val) * 100
    return f"{pct:+.1f}% vs H1", pct >= 0

# ─────────────────────────────────────────────────────────────────────────────
# CHARGEMENT DES DONNÉES
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)

    for col in ["AvgTone","GoldsteinScale","NumMentions","NumSources","NumArticles",
                "ActionGeo_Lat","ActionGeo_Long"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Date
    if "SQLDATE" in df.columns:
        df["event_date"] = pd.to_datetime(df["SQLDATE"].astype(str), errors="coerce")
    elif "MonthYear" in df.columns:
        df["event_date"] = pd.to_datetime(df["MonthYear"].astype(str), format="%Y%m", errors="coerce")
    else:
        df["event_date"] = pd.NaT
    df["month"]   = df["event_date"].dt.to_period("M").dt.to_timestamp()
    df["week"]    = df["event_date"].dt.to_period("W").dt.to_timestamp()
    df["day_of_week"] = df["event_date"].dt.dayofweek
    df["week_of_year"] = df["event_date"].dt.isocalendar().week.astype(int)

    # Event root
    if "EventRootLabel" in df.columns:
        df["event_root"] = df["EventRootLabel"].fillna(df.get("EventRootCode", "Inconnu").astype(str))
    elif "EventRootCode" in df.columns:
        df["event_root"] = df["EventRootCode"].astype(str)
    else:
        df["event_root"] = "Inconnu"
    df["event_root"] = df["event_root"].fillna("Inconnu").astype(str).replace(ROOT_TRANSLATIONS)

    # Quad
    if "QuadClassLabel" in df.columns:
        df["quad_label"] = df["QuadClassLabel"].fillna(df.get("QuadClass","Inconnu").astype(str))
    elif "QuadClass" in df.columns:
        df["quad_label"] = df["QuadClass"].astype(str)
    else:
        df["quad_label"] = "Inconnu"
    df["quad_label"] = df["quad_label"].fillna("Inconnu").astype(str)

    # Acteurs
    for role, labels in [("actor1_country",["Actor1CountryLabel","Actor1CountryCode"]),
                     ("actor2_country",["Actor2CountryLabel","Actor2CountryCode"])]:
        df[role] = "Inconnu"  # valeur par défaut
        for l in labels:
            if l in df.columns:
                df[role] = df[l].fillna("Inconnu").replace("", "Inconnu")
                break

    if "Actor2Type1Label" in df.columns:
        df["actor2_type_label"] = df["Actor2Type1Label"].fillna("Inconnu")
    else:
        df["actor2_type_label"] = "Inconnu"

    # Codes
    root_codes  = pd.to_numeric(df.get("EventRootCode",  pd.Series([-1]*len(df))), errors="coerce").fillna(-1).astype(int)
    event_codes = pd.to_numeric(df.get("EventCode",      pd.Series([-1]*len(df))), errors="coerce").fillna(-1).astype(int)
    df["is_economic"]   = event_codes.isin(ECONOMIC_CODES_INT)
    df["is_diplomatic"] = event_codes.isin(DIPLO_CODES_INT) | root_codes.isin({4,5})
    df["is_cooperation"]= root_codes.isin(COOP_ROOTS_INT)
    df["is_conflict"]   = root_codes.isin(CONFLICT_ROOTS_INT)
    q = df["quad_label"].str.lower()
    df["is_coop_quad"]  = q.str.contains("cooper", na=False)
    df["is_conf_quad"]  = q.str.contains("conflict", na=False)

    # Source & langue
    if "SOURCEURL" in df.columns:
        df["domain"]      = df["SOURCEURL"].apply(lambda x: normalize_domain(x) if pd.notna(x) else "")
        df["source_type"] = df["domain"].apply(classify_source)
    else:
        df["domain"]      = ""
        df["source_type"] = "Inconnue"

    if "Language" in df.columns:
        df["language"] = df["Language"].fillna("inconnu")
    else:
        df["language"] = "inconnu"
        if "domain" in df.columns:
            df.loc[df["domain"].str.endswith((".fr",".bj"), na=False), "language"] = "français"
            df.loc[df["domain"].str.contains(r"\.com", na=False), "language"] = "anglais"

    # Semestre
    df["semester"] = df["event_date"].apply(
        lambda d: "H1 (Jan–Jun)" if pd.notna(d) and d < PIVOT_H1H2 else "H2 (Jul–Déc)"
    )

    return df.copy()

@st.cache_data(show_spinner=False)
def apply_filters(df, scope_filters, date_range, selected_roots,
                  selected_actor, hide_unknown, tone_range, gold_range,
                  source_types, languages):
    view = df.copy()
    effective = [s for s in scope_filters if s != "Couverture complète"]
    if effective:
        mask = pd.Series(False, index=view.index)
        if "Économique"                 in effective: mask |= view["is_economic"]
        if "Diplomatique"               in effective: mask |= view["is_diplomatic"]
        if "Coopération internationale" in effective: mask |= view["is_cooperation"]
        if "Conflits"                   in effective: mask |= view["is_conflict"]
        view = view[mask]
    if date_range and "event_date" in view.columns:
        s, e = date_range
        view = view[(view["event_date"] >= pd.Timestamp(s)) & (view["event_date"] <= pd.Timestamp(e))]
    if selected_roots:
        view = view[view["event_root"].isin(selected_roots)]
    if selected_actor:
        view = view[view["actor1_country"].isin(selected_actor)]
    if hide_unknown:
        view = view[view["actor1_country"].ne("Inconnu")]
    if tone_range:
        view = view[view["AvgTone"].between(*tone_range)]
    if gold_range:
        view = view[view["GoldsteinScale"].between(*gold_range)]
    if source_types:
        view = view[view["source_type"].isin(source_types)]
    if languages:
        view = view[view["language"].isin(languages)]
    return view

# ─────────────────────────────────────────────────────────────────────────────
# CALCULS ANALYTIQUES
# ─────────────────────────────────────────────────────────────────────────────
def compute_attract_score_v2(df_v: pd.DataFrame) -> dict:
    """Score composite attractivité 7 dimensions (0-100)."""
    if df_v.empty:
        return {k: 0.0 for k in ["total","tone","stability","coop","economic","diplomatic","media_vol","source_diversity"]}
    avg_tone  = safe_mean(df_v["AvgTone"])
    avg_gold  = safe_mean(df_v["GoldsteinScale"])
    coop_sh   = float(df_v["is_cooperation"].mean())
    econ_sh   = float(df_v["is_economic"].mean())
    diplo_sh  = float(df_v["is_diplomatic"].mean())
    volume    = len(df_v)
    n_sources = df_v["domain"].nunique() if "domain" in df_v.columns else 1

    tone_score    = min(max((avg_tone + 20) / 40, 0), 1) * 100
    gold_score    = min(max((avg_gold + 10) / 20, 0), 1) * 100
    coop_score    = min(coop_sh * 200, 100)
    econ_score    = min(econ_sh * 200, 100)
    diplo_score   = min(diplo_sh * 200, 100)
    vol_score     = min(np.log1p(volume) / np.log1p(5000) * 100, 100)
    src_score     = min(np.log1p(n_sources) / np.log1p(500) * 100, 100)

    total = (
        tone_score  * 0.22 +
        gold_score  * 0.20 +
        coop_score  * 0.18 +
        econ_score  * 0.15 +
        diplo_score * 0.12 +
        vol_score   * 0.08 +
        src_score   * 0.05
    )
    return {
        "total": round(total, 1),
        "tone": round(tone_score, 1),
        "stability": round(gold_score, 1),
        "coop": round(coop_score, 1),
        "economic": round(econ_score, 1),
        "diplomatic": round(diplo_score, 1),
        "media_vol": round(vol_score, 1),
        "source_diversity": round(src_score, 1),
    }

def compute_risk_score(df_v: pd.DataFrame) -> pd.DataFrame:
    if df_v.empty or "event_date" not in df_v.columns:
        return pd.DataFrame()
    df_m = df_v.copy()
    df_m["month_str"] = df_m["event_date"].dt.to_period("M").astype(str)
    monthly = df_m.groupby("month_str").agg(
        avg_tone=("AvgTone","mean"),
        avg_gold=("GoldsteinScale","mean"),
        conflict_volume=("is_conflict","sum"),
        total=("GLOBALEVENTID","count")
    ).reset_index()
    monthly.rename(columns={"month_str": "month"}, inplace=True)
    if len(monthly) < 2:
        monthly["risk_score"] = 50.0
        return monthly[["month","risk_score"]]

    def _norm(s):
        r = s.max() - s.min()
        return (s - s.min()) / r if r > 0 else pd.Series(0.5, index=s.index)

    tone_n     = _norm(monthly["avg_tone"])
    gold_n     = _norm(monthly["avg_gold"])
    conflict_n = _norm(monthly["conflict_volume"] / monthly["total"].clip(lower=1))
    monthly["risk_score"] = ((1-tone_n)*0.40 + (1-gold_n)*0.30 + conflict_n*0.30) * 100
    monthly["risk_score"] = monthly["risk_score"].fillna(50).round(1)
    return monthly[["month","risk_score"]]

def detect_anomalies(df_v: pd.DataFrame) -> pd.DataFrame:
    if df_v.empty or "event_date" not in df_v.columns:
        return pd.DataFrame()
    daily = df_v.groupby(df_v["event_date"].dt.date).agg(
        volume=("GLOBALEVENTID","count"),
        avg_tone=("AvgTone","mean"),
        avg_gold=("GoldsteinScale","mean")
    ).reset_index()
    daily.columns = ["date","volume","avg_tone","avg_gold"]
    rows = []
    for metric in ["volume","avg_tone","avg_gold"]:
        s = daily[metric].dropna()
        if len(s) < 4: continue
        Q1,Q3 = s.quantile(0.25), s.quantile(0.75)
        IQR   = Q3 - Q1
        lo, hi = Q1 - 1.5*IQR, Q3 + 1.5*IQR
        mask = (daily[metric] < lo) | (daily[metric] > hi)
        for i in daily[mask].index:
            rows.append({
                "date":       daily.loc[i,"date"],
                "métrique":   metric,
                "valeur":     daily.loc[i,metric],
                "seuil_inf":  round(lo,2),
                "seuil_sup":  round(hi,2),
                "direction":  "↑ Pic" if daily.loc[i,metric] > hi else "↓ Creux",
            })
    return pd.DataFrame(rows).sort_values("date", ascending=False) if rows else pd.DataFrame()

def get_anomaly_data(df_v: pd.DataFrame, anomaly_date, metric: str) -> pd.DataFrame:
    """
    Retourne les événements du jour de l'anomalie, avec filtrage selon la métrique.
    - volume : tous les événements du jour
    - avg_tone : événements dont la tonalité s'écarte de plus de 2 écarts-types
    - avg_gold : événements dont le Goldstein s'écarte de plus de 2 écarts-types
    """
    if df_v.empty or "event_date" not in df_v.columns:
        return pd.DataFrame()
    date_obj = pd.to_datetime(anomaly_date).date()
    day_df = df_v[df_v["event_date"].dt.date == date_obj].copy()
    if metric == "volume":
        return day_df
    elif metric == "avg_tone":
        tone_mean = day_df["AvgTone"].mean()
        tone_std = day_df["AvgTone"].std()
        if tone_std == 0 or pd.isna(tone_std):
            return pd.DataFrame()
        threshold = 2 * tone_std
        extreme = day_df[(day_df["AvgTone"] < tone_mean - threshold) | (day_df["AvgTone"] > tone_mean + threshold)]
        return extreme
    elif metric == "avg_gold":
        gold_mean = day_df["GoldsteinScale"].mean()
        gold_std = day_df["GoldsteinScale"].std()
        if gold_std == 0 or pd.isna(gold_std):
            return pd.DataFrame()
        threshold = 2 * gold_std
        extreme = day_df[(day_df["GoldsteinScale"] < gold_mean - threshold) | (day_df["GoldsteinScale"] > gold_mean + threshold)]
        return extreme
    return pd.DataFrame()

def get_country_relations(df_v: pd.DataFrame, target="Benin") -> pd.DataFrame:
    if df_v.empty: return pd.DataFrame()
    t = target.lower()
    m1 = df_v["actor1_country"].str.lower() == t
    m2 = df_v["actor2_country"].str.lower() == t if "actor2_country" in df_v.columns else pd.Series(False, index=df_v.index)
    partners = pd.concat([
        df_v[m1]["actor2_country"] if "actor2_country" in df_v.columns else pd.Series(),
        df_v[m2]["actor1_country"],
    ], ignore_index=True)
    partners = partners[partners.notna() & (partners.str.lower() != t) & (partners.str.strip() != "")]
    if partners.empty: return pd.DataFrame()
    stats = partners.value_counts().reset_index()
    stats.columns = ["pays","volume"]
    def _tone(p):
        mk = ((df_v["actor1_country"]==p)&m2) | ((df_v["actor2_country"]==p)&m1) if "actor2_country" in df_v.columns else m1
        return df_v[mk]["AvgTone"].mean()
    def _gold(p):
        mk = ((df_v["actor1_country"]==p)&m2) | ((df_v["actor2_country"]==p)&m1) if "actor2_country" in df_v.columns else m1
        return df_v[mk]["GoldsteinScale"].mean()
    stats["tonalite"]  = stats["pays"].apply(_tone)
    stats["stabilite"] = stats["pays"].apply(_gold)
    return stats.sort_values("volume", ascending=False).reset_index(drop=True)

def cluster_partners(rel_df: pd.DataFrame):
    if rel_df.empty or len(rel_df) < 3: return rel_df, None
    feats = [c for c in ["volume","tonalite","stabilite"] if c in rel_df.columns]
    if len(feats) < 2: return rel_df, None
    X = rel_df[feats].copy().fillna(0)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    pca = PCA(n_components=2)
    pc  = pca.fit_transform(Xs)
    rel_df = rel_df.copy()
    rel_df["pca1"], rel_df["pca2"] = pc[:,0], pc[:,1]
    nc = min(3, len(rel_df))
    km = KMeans(n_clusters=nc, random_state=42, n_init=10)
    rel_df["cluster"] = km.fit_predict(Xs)
    means = rel_df.groupby("cluster")[feats].mean()
    labels = {}
    for c in means.index:
        vol  = means.loc[c,"volume"]
        tone = means.loc[c,"tonalite"] if "tonalite" in feats else 0
        labels[c] = ("🟢 Partenaires actifs" if tone >= 0 else "🔴 Partenaires sensibles") + f" (vol≈{vol:.0f})"
    rel_df["cluster_label"] = rel_df["cluster"].map(labels)
    fig = px.scatter(rel_df, x="pca1", y="pca2", color="cluster_label",
                     hover_name="pays", size="volume", text="pays",
                     title="ACP + K-means — Classification des partenaires",
                     labels={"pca1":"Composante 1","pca2":"Composante 2"})
    fig.update_traces(textposition="top center", marker=dict(opacity=0.85))
    fig.update_layout(legend_title_text="Groupe")
    return rel_df, fig

def generate_insight(df_v: pd.DataFrame, profile_key: str, scores: dict, risk_df: pd.DataFrame) -> str:
    if df_v.empty: return "Données insuffisantes."
    max_d = df_v["event_date"].max()
    recent = df_v[df_v["event_date"] >= df_v["event_date"].max() - pd.Timedelta(days=30)]
    vol    = len(df_v)
    rvol   = len(recent)
    tone   = safe_mean(df_v["AvgTone"])
    gold   = safe_mean(df_v["GoldsteinScale"])
    coop   = float(df_v["is_cooperation"].mean())
    conf   = float(df_v["is_conflict"].mean())
    risk_v = float(risk_df["risk_score"].mean()) if not risk_df.empty else 50
    top3   = df_v["event_root"].value_counts().head(3).index.tolist()
    top3s  = ", ".join(top3) if top3 else "N/A"
    attract= scores["total"]

    tone_label  = "positive" if tone > 0 else "négative"
    gold_label  = "favorable" if gold > 0 else "défavorable"
    risk_label  = "élevé" if risk_v > 60 else ("modéré" if risk_v > 35 else "faible")
    attract_l   = "fort" if attract > 65 else ("modéré" if attract > 40 else "limité")

    if profile_key == "investor":
        return f"""
**📊 Analyse investisseur — Bénin 2025**

Le score d'attractivité composite est **{attract}/100** (niveau {attract_l}). 
La perception médiatique affiche une tonalité {tone_label} ({tone:.2f}) avec un signal de stabilité politique
{gold_label} (Goldstein : {gold:.2f}). Le niveau de risque souverain perçu est **{risk_label}** ({risk_v:.1f}/100).

Sur les 30 derniers jours, **{rvol} événements** ont été enregistrés sur {vol} au total.
Les thématiques dominantes — *{top3s}* — indiquent 
{"des signaux positifs pour les secteurs couverts." if tone > 0 else "des tensions à surveiller avant engagement."}

**→ Recommandation :** {"Fenêtre d'opportunité identifiée. Prioriser les secteurs économiques médiatisés." if attract > 55 else "Attendre une stabilisation des indicateurs avant engagement lourd."}
"""
    elif profile_key == "diplomat":
        return f"""
**🌐 Analyse diplomatique — Bénin 2025**

La couverture internationale du Bénin reflète une tonalité {tone_label} ({tone:.2f}).
La part d'actions coopératives est **{coop:.0%}** contre **{conf:.0%}** de conflits.

Les échanges bilatéraux les plus médiatisés concernent : *{top3s}*.
Le score de stabilité perçue (Goldstein {gold:.2f}) est {gold_label}.

**→ Action suggérée :** {"Capitaliser sur la dynamique positive pour intensifier les initiatives de coopération." if tone > 0 and coop > 0.3 else "Déployer des programmes culturels et économiques pour inverser la perception."}
"""
    elif profile_key == "apiex":
        return f"""
**📈 Analyse attractivité IED — Bénin 2025**

Score d'attractivité composite : **{attract}/100**. 
La part de couverture économique représente **{scores['economic']:.1f}/100** du signal médiatique.
La perception internationale (tonalité {tone:.2f}) est {tone_label}.

Avec {vol:,} événements recensés, le Bénin bénéficie d'une visibilité médiatique 
{"significative" if vol > 3000 else "à renforcer"} sur la scène internationale.

**→ Narratifs à amplifier :** thématiques dominantes *{top3s}* — à valoriser dans les pitchs IED.
"""
    elif profile_key == "journalist":
        anomalies = detect_anomalies(df_v)
        nb_anom   = len(anomalies) if not anomalies.empty else 0
        return f"""
**📰 Briefing journalistique — Bénin 2025**

**{vol:,} événements** GDELT analysés. **{nb_anom} anomalies** statistiques détectées 
(pics ou creux hors norme sur volume, tonalité ou stabilité).

Tonalité globale : **{tone:.2f}** ({tone_label}). Stabilité perçue : **{gold:.2f}** ({gold_label}).
Thématiques les plus couvertes : *{top3s}*.

**→ Angles éditoriaux potentiels :** 
{"Couvrir les dynamiques positives sous-reportées dans la presse internationale." if tone > 0 else "Investiguer les sources de tensions non résolues."}
"""
    else:  # researcher
        return f"""
**🔬 Résumé analytique — Données GDELT Bénin 2025**

**N = {vol:,}** observations · Tonalité μ = {tone:.3f} · Goldstein μ = {gold:.3f}
Score attractivité composite : **{scores['total']}/100** (7 dimensions).
Risque moyen mensuel : **{risk_v:.1f}/100**.

Distribution thématique (top 3) : *{top3s}*.
Part coopérative : {coop:.1%} · Part conflictuelle : {conf:.1%}.

**→ Axes de recherche :** Modélisation causale tonalité ↔ IED · Séries temporelles GDELT vs indicateurs WB.
"""

def generate_wordcloud(df_v, col="event_root", title=""):
    if df_v.empty or col not in df_v.columns:
        fig, ax = plt.subplots(figsize=(8,4))
        ax.text(0.5,0.5,"Données insuffisantes",ha="center",va="center",fontsize=14)
        ax.axis("off"); return fig
    text = " ".join(df_v[col].astype(str).fillna(""))
    if not text.strip():
        fig, ax = plt.subplots(figsize=(8,4))
        ax.text(0.5,0.5,"Aucun texte",ha="center",va="center",fontsize=14)
        ax.axis("off"); return fig
    wc = WordCloud(width=900,height=420,background_color="white",
                   colormap="viridis",max_words=80,
                   collocations=False).generate(text)
    fig, ax = plt.subplots(figsize=(10,4.5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    if title: ax.set_title(title, fontsize=13, fontweight="bold", pad=8)
    return fig

def heatmap_calendar(df_v: pd.DataFrame) -> go.Figure:
    """Heatmap calendaire des volumes quotidiens."""
    if df_v.empty or "event_date" not in df_v.columns:
        return go.Figure()
    daily = df_v.groupby(df_v["event_date"].dt.date).size().reset_index()
    daily.columns = ["date","count"]
    daily["date"] = pd.to_datetime(daily["date"])
    daily["week"] = daily["date"].dt.isocalendar().week.astype(int)
    daily["dow"]  = daily["date"].dt.dayofweek
    dow_labels    = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
    fig = px.density_heatmap(daily, x="week", y="dow", z="count",
                             color_continuous_scale="YlOrRd",
                             labels={"week":"Semaine","dow":"Jour","count":"Événements"},
                             title="Heatmap calendaire — Intensité quotidienne")
    fig.update_yaxes(tickvals=list(range(7)), ticktext=dow_labels)
    fig.update_layout(height=280, margin=dict(t=40,b=20))
    return fig

def radar_chart(scores: dict) -> go.Figure:
    dims   = ["Tonalité", "Stabilité", "Coopération", "Économique", "Diplomatique", "Vol. média", "Diversité sources"]
    keys   = ["tone","stability","coop","economic","diplomatic","media_vol","source_diversity"]
    values = [scores.get(k,0) for k in keys] + [scores.get(keys[0],0)]
    cats   = dims + [dims[0]]
    fig = go.Figure(go.Scatterpolar(
        r=values, theta=cats, fill="toself",
        fillcolor="rgba(30,111,120,0.18)",
        line=dict(color="#1e6f78", width=2.5),
        marker=dict(size=5)
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100])),
        showlegend=False,
        title=dict(text="Profil d'attractivité — Radar 7 dimensions", x=0.5),
        height=380, margin=dict(t=50,b=20,l=20,r=20)
    )
    return fig

def h1h2_comparison(df_v: pd.DataFrame, scores_fn) -> dict:
    h1 = df_v[df_v["event_date"] < PIVOT_H1H2]
    h2 = df_v[df_v["event_date"] >= PIVOT_H1H2]
    return {
        "H1": scores_fn(h1), "H2": scores_fn(h2),
        "vol_h1": len(h1), "vol_h2": len(h2),
    }

def export_html(df_v, scores, risk_df, profile) -> str:
    risk_html = risk_df.to_html(index=False) if not risk_df.empty else "<p>Non disponible</p>"
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<title>Rapport Observatoire Bénin</title>
<style>
  body{{font-family:Arial,sans-serif;margin:2.5rem;color:#151515;background:#fafafa}}
  h1{{color:#1e6f78;border-bottom:3px solid #d18f2b;padding-bottom:.5rem}}
  h2{{color:#2e4b8f;margin-top:2rem}}
  .kpi{{display:flex;gap:1rem;flex-wrap:wrap;margin:1.5rem 0}}
  .card{{border:1px solid #ddd;padding:1rem;border-radius:12px;min-width:160px;background:#fff}}
  .card b{{display:block;color:#1e6f78;font-size:1.4rem;margin-top:.3rem}}
  table{{border-collapse:collapse;width:100%;margin-top:1rem}}
  th,td{{border:1px solid #ddd;padding:8px;text-align:left;font-size:.85rem}}
  th{{background:#f0f0f0;color:#1e6f78;font-weight:600}}
  .footer{{margin-top:3rem;font-size:.8rem;color:#888}}
  @media print{{.no-print{{display:none}}}}
</style></head><body>
<h1>🇧🇯 Observatoire médiatique du Bénin</h1>
<p><strong>Profil : {profile}</strong> · Généré le {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}</p>
<div class="kpi">
  <div class="card">Volume<b>{len(df_v):,}</b>événements</div>
  <div class="card">Score attractivité<b>{scores['total']}/100</b>composite</div>
  <div class="card">Tonalité<b>{safe_mean(df_v['AvgTone']):.2f}</b>AvgTone</div>
  <div class="card">Stabilité<b>{safe_mean(df_v['GoldsteinScale']):.2f}</b>Goldstein</div>
  <div class="card">Coopération<b>{df_v['is_cooperation'].mean():.0%}</b>d'actions</div>
  <div class="card">Économique<b>{df_v['is_economic'].mean():.0%}</b>d'actions</div>
</div>
<h2>Score de risque mensuel</h2>{risk_html}
<h2>Données (extrait 100 lignes)</h2>
{df_v[["event_date","actor1_country","event_root","AvgTone","GoldsteinScale"]].head(100).to_html(index=False)}
<div class="footer">Source : GDELT Event Database 2025 — Observatoire médiatique du Bénin</div>
</body></html>"""

def render_articles_table(df_v):
    if df_v.empty:
        st.info("Aucun article à afficher.")
        return
    cols = ["event_date","actor1_country","actor2_country","event_root",
            "source_type","language","SOURCEURL","AvgTone","GoldsteinScale"]
    avail = [c for c in cols if c in df_v.columns]
    t = df_v[avail].copy()
    if "event_date" in t.columns:
        t["event_date"] = t["event_date"].dt.date
    t.rename(columns={
        "event_date":"Date","actor1_country":"Acteur 1","actor2_country":"Acteur 2",
        "event_root":"Thématique","source_type":"Source","language":"Langue",
        "SOURCEURL":"Lien","AvgTone":"Tonalité","GoldsteinScale":"Stabilité"
    }, inplace=True)
    cfg = {}
    if "Lien" in t.columns:
        cfg["Lien"] = st.column_config.LinkColumn(label="Lien", display_text="🔗 Article")
    st.dataframe(t, use_container_width=True, height=420, column_config=cfg)

# ─────────────────────────────────────────────────────────────────────────────
# INITIALISATION
# ─────────────────────────────────────────────────────────────────────────────
if not DATA_PATH.exists():
    st.error(f"⚠️ Fichier introuvable : `{DATA_PATH}`  \nVérifiez le chemin vers votre CSV GDELT.")
    st.stop()

with st.spinner("Chargement des données GDELT…"):
    df = load_data(DATA_PATH)

px.defaults.template = "simple_white"

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Tableau de bord")

    # Profil décideur
    selected_profile = st.selectbox(
        "👤 Mon profil",
        options=list(PROFILES.keys()),
        help="Personnalise les analyses et recommandations"
    )
    pinfo = PROFILES[selected_profile]
    st.markdown(f'<div style="background:{pinfo["color"]}22;border-left:4px solid {pinfo["color"]};padding:.5rem .8rem;border-radius:8px;font-size:.82rem;color:{pinfo["color"]};margin-bottom:1rem">{PROFILE_TIPS[selected_profile]}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Filtres")

    scope_options = ["Couverture complète","Économique","Diplomatique","Coopération internationale","Conflits"]
    selected_scope = st.selectbox("Portée thématique", scope_options)

    if df["event_date"].notna().any():
        mn = df["event_date"].min().date()
        mx = df["event_date"].max().date()
        date_range = st.slider("Période", min_value=mn, max_value=mx,
                               value=(mn, mx), format="YYYY-MM-DD")
    else:
        date_range = None

    root_options = sorted(df["event_root"].dropna().unique().tolist())
    selected_roots = st.multiselect("Types d'événements", options=root_options, placeholder="Tous")

    actor_options = sorted(df["actor1_country"].dropna().unique().tolist())
    selected_actor = st.multiselect("Pays acteur principal", options=actor_options)

    source_types = st.multiselect("Type de source", ["Nationale","Internationale","Inconnue"])
    lang_options = sorted(df["language"].dropna().unique().tolist())
    selected_lang = st.multiselect("Langue", options=lang_options)

    hide_unknown = st.checkbox("Masquer acteurs inconnus", value=False)

    tone_range = None
    if df["AvgTone"].notna().any():
        tn,tx = float(df["AvgTone"].min()), float(df["AvgTone"].max())
        if tn < tx:
            tone_range = st.slider("Plage tonalité", round(tn,2), round(tx,2), (round(tn,2),round(tx,2)))

    gold_range = None
    if df["GoldsteinScale"].notna().any():
        gn,gx = float(df["GoldsteinScale"].min()), float(df["GoldsteinScale"].max())
        if gn < gx:
            gold_range = st.slider("Plage Goldstein", round(gn,2), round(gx,2), (round(gn,2),round(gx,2)))

    st.markdown("---")
    st.caption("🇧🇯 Observatoire médiatique du Bénin — v3")

# ─────────────────────────────────────────────────────────────────────────────
# FILTRAGE
# ─────────────────────────────────────────────────────────────────────────────
df_view = apply_filters(
    df=df, scope_filters=[selected_scope], date_range=date_range,
    selected_roots=selected_roots, selected_actor=selected_actor,
    hide_unknown=hide_unknown, tone_range=tone_range, gold_range=gold_range,
    source_types=source_types, languages=selected_lang,
)

if df_view.empty:
    st.warning("Aucune donnée avec ces filtres — élargissez la sélection.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# CALCULS GLOBAUX
# ─────────────────────────────────────────────────────────────────────────────
scores   = compute_attract_score_v2(df_view)
risk_df  = compute_risk_score(df_view)
avg_tone = safe_mean(df_view["AvgTone"])
avg_gold = safe_mean(df_view["GoldsteinScale"])
coop_sh  = float(df_view["is_cooperation"].mean())
econ_sh  = float(df_view["is_economic"].mean())
h1h2     = h1h2_comparison(df_view, compute_attract_score_v2)
risk_global = float(risk_df["risk_score"].mean()) if not risk_df.empty else 50.0

# ─────────────────────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────────────────────
date_label = ""
if date_range:
    date_label = f" · {date_range[0].strftime('%d/%m/%Y')} → {date_range[1].strftime('%d/%m/%Y')}"

st.markdown(f"""
<div class="hero">
  <div class="hero-eyebrow">🇧🇯 Observatoire médiatique · GDELT 2025</div>
  <div class="hero-title">Attractivité territoriale du Bénin<br><span style="font-size:1.5rem;color:#1e6f78">Pilotée par les données médiatiques</span></div>
  <div class="hero-subtitle">
    {len(df_view):,} événements analysés{date_label} · Profil actif : {pinfo["icon"]} <strong>{selected_profile}</strong>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# KPI ROW — 7 CARTES
# ─────────────────────────────────────────────────────────────────────────────
tone_delta, tone_good   = pct_change_label(safe_mean(df_view[df_view["semester"]=="H2 (Jul–Déc)"]["AvgTone"]), safe_mean(df_view[df_view["semester"]=="H1 (Jan–Jun)"]["AvgTone"]))
gold_delta, gold_good   = pct_change_label(safe_mean(df_view[df_view["semester"]=="H2 (Jul–Déc)"]["GoldsteinScale"]), safe_mean(df_view[df_view["semester"]=="H1 (Jan–Jun)"]["GoldsteinScale"]))
vol_delta, vol_good     = pct_change_label(h1h2["vol_h2"], h1h2["vol_h1"])
attr_delta, attr_good   = pct_change_label(h1h2["H2"]["total"], h1h2["H1"]["total"])

k = st.columns(7)
with k[0]: metric_card("Volume", f"{len(df_view):,}", "Événements filtrés", "#1e6f78", vol_delta, vol_good)
with k[1]: metric_card("AvgTone", f"{avg_tone:.2f}", "Sentiment médias", "#2e4b8f", tone_delta, tone_good)
with k[2]: metric_card("Goldstein", f"{avg_gold:.2f}", "Stabilité perçue", "#0d6b3f", gold_delta, gold_good)
with k[3]: metric_card("Coopération", f"{coop_sh:.0%}", "Actions pacifiques", "#5a2d82")
with k[4]: metric_card("Économique", f"{econ_sh:.0%}", "Couverture économique", "#8b2e00")
with k[5]: metric_card("Risque", f"{risk_global:.0f}/100", "Score mensuel moyen", "#c62828")
with k[6]: metric_card("Attractivité", f"{scores['total']}/100", "Indice composite 7D", "#d18f2b", attr_delta, attr_good)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ONGLETS
# ─────────────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📊 Vue d'ensemble",
    "🌍 Relations & Géopolitique",
    "📰 Articles & Sources",
    "📈 Analyse avancée",
    f"{pinfo['icon']} Espace {selected_profile.split()[1]}",
    "⬇️ Exports & Données",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VUE D'ENSEMBLE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    col_radar, col_timeline = st.columns([1, 2])

    with col_radar:
        st.markdown("<div class='section-title'>🎯 Radar attractivité</div>", unsafe_allow_html=True)
        st.plotly_chart(radar_chart(scores), use_container_width=True)

    with col_timeline:
        st.markdown("<div class='section-title'>📅 Évolution temporelle</div>", unsafe_allow_html=True)
        monthly = df_view.groupby("month", as_index=False).agg(
            count=("GLOBALEVENTID","count"),
            avg_tone=("AvgTone","mean"),
            avg_gold=("GoldsteinScale","mean"),
        ).sort_values("month")
        if not monthly.empty:
            fig_main = make_subplots(specs=[[{"secondary_y": True}]])
            fig_main.add_trace(go.Bar(x=monthly["month"], y=monthly["count"],
                                      name="Volume", marker_color="#1e6f78", opacity=0.7), secondary_y=False)
            fig_main.add_trace(go.Scatter(x=monthly["month"], y=monthly["avg_tone"],
                                          mode="lines+markers", name="Tonalité",
                                          line=dict(color="#d18f2b", width=2.5)), secondary_y=True)
            fig_main.add_trace(go.Scatter(x=monthly["month"], y=monthly["avg_gold"],
                                          mode="lines+markers", name="Goldstein",
                                          line=dict(color="#0d6b3f", width=2, dash="dot")), secondary_y=True)
            fig_main.update_layout(height=340, legend=dict(orientation="h", y=-0.15),
                                   margin=dict(t=30,b=10))
            fig_main.update_yaxes(title_text="Volume", secondary_y=False)
            fig_main.update_yaxes(title_text="Score", secondary_y=True)
            st.plotly_chart(fig_main, use_container_width=True)

    # Heatmap calendaire
    st.markdown("<div class='section-title'>🗓️ Heatmap calendaire</div>", unsafe_allow_html=True)
    st.plotly_chart(heatmap_calendar(df_view), use_container_width=True)

    # Top thématiques & Quad
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='section-title'>🏷️ Top thématiques</div>", unsafe_allow_html=True)
        top = df_view["event_root"].value_counts().reset_index().head(12)
        top.columns = ["Thématique","Volume"]
        fig = px.bar(top, x="Volume", y="Thématique", orientation="h",
                     color="Volume", color_continuous_scale="Blues",
                     height=380)
        fig.update_layout(margin=dict(t=10,b=10), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("<div class='section-title'>⚖️ Quadrants événementiels</div>", unsafe_allow_html=True)
        quad = df_view["quad_label"].value_counts().reset_index()
        quad.columns = ["Quadrant","Nombre"]
        colors = {"Verbal Cooperation":"#2e7d32","Material Cooperation":"#1b5e20",
                  "Verbal Conflict":"#e65100","Material Conflict":"#b71c1c"}
        fig = px.pie(quad, names="Quadrant", values="Nombre", hole=0.42,
                     color="Quadrant", color_discrete_map=colors, height=380)
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)

    # Comparaison H1/H2
    st.markdown("<div class='section-title'>📊 Comparaison H1 vs H2 — 7 dimensions</div>", unsafe_allow_html=True)
    dims_labels = ["Tonalité","Stabilité","Coopération","Économique","Diplomatique","Vol. média","Diversité"]
    dims_keys   = ["tone","stability","coop","economic","diplomatic","media_vol","source_diversity"]
    h1_vals = [h1h2["H1"].get(k,0) for k in dims_keys]
    h2_vals = [h1h2["H2"].get(k,0) for k in dims_keys]
    fig_h = go.Figure()
    fig_h.add_trace(go.Bar(name="H1 (Jan–Jun)", x=dims_labels, y=h1_vals, marker_color="#1e6f78", opacity=0.8))
    fig_h.add_trace(go.Bar(name="H2 (Jul–Déc)", x=dims_labels, y=h2_vals, marker_color="#d18f2b", opacity=0.8))
    fig_h.update_layout(barmode="group", height=320, margin=dict(t=10,b=10),
                         legend=dict(orientation="h",y=-0.2), yaxis_range=[0,105])
    st.plotly_chart(fig_h, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RELATIONS & GÉOPOLITIQUE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    relations = get_country_relations(df_view)

    st.markdown("<div class='section-title'>🗺️ Carte des partenaires internationaux</div>", unsafe_allow_html=True)
    if not relations.empty:
        fig_map = px.choropleth(
            relations, locations="pays", locationmode="country names",
            color="tonalite", hover_name="pays",
            hover_data={"volume": True, "tonalite": ":.2f", "stabilite": ":.2f"},
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            title="Tonalité médiatique par pays partenaire (rouge = négative · vert = positive)",
            height=480,
        )
        fig_map.update_layout(margin=dict(t=40,b=0))
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("Aucun partenaire international détecté dans les filtres actuels.")

    c1, c2 = st.columns([3,2])
    with c1:
        st.markdown("<div class='section-title'>🏆 Top 15 partenaires — Volume & Tonalité</div>", unsafe_allow_html=True)
        if not relations.empty:
            top15 = relations.head(15).copy()
            fig = px.bar(top15, x="pays", y="volume",
                         color="tonalite", color_continuous_scale="RdYlGn",
                         color_continuous_midpoint=0,
                         labels={"pays":"Pays","volume":"Volume","tonalite":"Tonalité"},
                         height=340)
            fig.update_layout(margin=dict(t=10,b=10))
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("<div class='section-title'>📋 Tableau des partenaires</div>", unsafe_allow_html=True)
        if not relations.empty:
            disp = relations.head(20).copy()
            disp["tonalite"]  = disp["tonalite"].round(2)
            disp["stabilite"] = disp["stabilite"].round(2)
            disp.rename(columns={"pays":"Pays","volume":"Volume",
                                  "tonalite":"Tonalité","stabilite":"Stabilité"}, inplace=True)
            st.dataframe(disp, use_container_width=True, height=340)

    # Clustering ACP
    st.markdown("<div class='section-title'>🔬 Classification des partenaires (ACP + K-means)</div>", unsafe_allow_html=True)
    if not relations.empty and len(relations) >= 3:
        rel_c, fig_pca = cluster_partners(relations)
        if fig_pca:
            st.plotly_chart(fig_pca, use_container_width=True)
            cols_show = [c for c in ["pays","volume","tonalite","stabilite","cluster_label"] if c in rel_c.columns]
            st.dataframe(rel_c[cols_show], use_container_width=True, height=280)
            st.markdown("""
> 🟢 **Partenaires actifs (ton. positive)** → levier d'attractivité immédiat.  
> 🔴 **Partenaires sensibles (ton. négative)** → surveillance et diplomatie préventive.
""")
    else:
        st.info("Minimum 3 pays requis pour la classification (élargissez les filtres).")

    # Types d'acteurs
    st.markdown("<div class='section-title'>🏛️ Types d'acteurs impliqués</div>", unsafe_allow_html=True)
    if "actor2_type_label" in df_view.columns:
        mask = (df_view["actor2_country"].ne("Inconnu")) & (df_view["actor2_country"].str.lower().ne("benin"))
        ptypes = df_view[mask]["actor2_type_label"].value_counts().reset_index().head(15)
        ptypes.columns = ["Type","N"]
        if not ptypes.empty:
            fig = px.bar(ptypes, x="Type", y="N", color="N",
                         color_continuous_scale="Viridis", height=320,
                         labels={"Type":"Type d'acteur","N":"Événements"})
            fig.update_layout(margin=dict(t=10,b=10))
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ARTICLES & SOURCES
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("<div class='section-title'>📋 Tableau interactif des articles</div>", unsafe_allow_html=True)

    # Filtres inline rapides
    flt1, flt2, flt3 = st.columns(3)
    with flt1:
        tone_flt = st.selectbox("Tonalité", ["Toutes","Positive (>0)","Négative (<0)"], key="tone_filter")
    with flt2:
        src_flt = st.selectbox("Source", ["Toutes","Nationale","Internationale"], key="src_filter")
    with flt3:
        top_n = st.slider("Nombre de lignes", 50, 500, 200, step=50)

    df_art = df_view.copy()
    if tone_flt == "Positive (>0)":    df_art = df_art[df_art["AvgTone"] > 0]
    elif tone_flt == "Négative (<0)":  df_art = df_art[df_art["AvgTone"] < 0]
    if src_flt != "Toutes":            df_art = df_art[df_art["source_type"] == src_flt]
    render_articles_table(df_art.head(top_n))

    # Word clouds
    st.markdown("<div class='section-title'>☁️ Word Clouds thématiques</div>", unsafe_allow_html=True)
    wc1, wc2 = st.columns(2)
    with wc1:
        nat = df_art[df_art["source_type"]=="Nationale"]
        fig = generate_wordcloud(nat, title="Sources nationales")
        st.pyplot(fig, use_container_width=True)
    with wc2:
        intl = df_art[df_art["source_type"]=="Internationale"]
        fig = generate_wordcloud(intl, title="Sources internationales")
        st.pyplot(fig, use_container_width=True)

    # Stats sources
    c1, c2, c3 = st.columns(3)
    with c1:
        src_cnt = df_view["source_type"].value_counts().reset_index()
        src_cnt.columns = ["Type","N"]
        fig = px.pie(src_cnt, names="Type", values="N", hole=0.45,
                     title="Répartition des sources", height=280)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        lang_cnt = df_view["language"].value_counts().reset_index().head(8)
        lang_cnt.columns = ["Langue","N"]
        fig = px.bar(lang_cnt, x="Langue", y="N", title="Langues", height=280, color="N")
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        top_domains = df_view["domain"].value_counts().reset_index().head(12)
        top_domains.columns = ["Domaine","N"]
        fig = px.bar(top_domains, x="N", y="Domaine", orientation="h",
                     title="Top domaines", height=280, color="N")
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ANALYSE AVANCÉE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    # Score de risque
    st.markdown("<div class='section-title'>📉 Score de risque territorial mensuel</div>", unsafe_allow_html=True)
    if not risk_df.empty:
        fig_risk = px.area(risk_df, x="month", y="risk_score",
                           title="Indice de risque (0 = faible · 100 = élevé)",
                           color_discrete_sequence=["#c62828"], height=300)
        fig_risk.add_hrect(y0=60, y1=100, fillcolor="#ffebee", opacity=0.4, line_width=0,
                           annotation_text="Zone vigilance", annotation_position="top left")
        fig_risk.add_hrect(y0=0,  y1=30,  fillcolor="#e8f5e9", opacity=0.4, line_width=0,
                           annotation_text="Zone stable",   annotation_position="bottom left")
        fig_risk.update_layout(yaxis_range=[0,100], margin=dict(t=40,b=10))
        st.plotly_chart(fig_risk, use_container_width=True)
        st.caption("Formule : (1-tonalité normalisée)×0.40 + (1-goldstein normalisée)×0.30 + conflits normalisés×0.30")

    # Scatter Tone vs Goldstein
    st.markdown("<div class='section-title'>🔮 Scatter Tonalité × Stabilité</div>", unsafe_allow_html=True)
    sample = df_view.sample(min(2000, len(df_view)), random_state=42)
    fig_scatter = px.scatter(sample, x="AvgTone", y="GoldsteinScale",
                             color="event_root", opacity=0.6,
                             hover_data=["actor1_country","event_date"],
                             title="Distribution des événements (axes: tonalité & stabilité)",
                             height=400)
    fig_scatter.add_vline(x=0, line_dash="dash", line_color="#999")
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="#999")
    fig_scatter.update_layout(margin=dict(t=40,b=10), showlegend=False)
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Anomalies
    st.markdown("<div class='section-title'>🔔 Alertes & Anomalies statistiques</div>", unsafe_allow_html=True)
    anomalies = detect_anomalies(df_view)
    if not anomalies.empty:
        n_anom = len(anomalies)
        st.markdown(f'<div class="warning-box">⚠️ <strong>{n_anom} anomalie(s)</strong> détectée(s) par la méthode IQR (hors-norme statistique).</div>', unsafe_allow_html=True)
        for _, row in anomalies.head(20).iterrows():
            metric_icons = {"volume":"📊","avg_tone":"😐","avg_gold":"⚖️"}
            icon = metric_icons.get(row["métrique"],"📌")
            st.markdown(f"""
    <div class="anomaly-card">
    {icon} <strong>{row['date']}</strong> · <em>{row['métrique']}</em> · valeur <strong>{row['valeur']:.2f}</strong> {row['direction']}
    <span style="color:#888;font-size:.82rem"> (norme : {row['seuil_inf']:.2f} → {row['seuil_sup']:.2f})</span>
    </div>""", unsafe_allow_html=True)
            
            # Téléchargement des données de l'anomalie
            anomaly_data = get_anomaly_data(df_view, row['date'], row['métrique'])
            if not anomaly_data.empty:
                csv_data = anomaly_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Télécharger les données de cette anomalie (CSV)",
                    data=csv_data,
                    file_name=f"anomalie_{row['date']}_{row['métrique']}.csv",
                    mime="text/csv",
                    key=f"download_anom_{row['date']}_{row['métrique']}_{row['direction']}"
                )
    else:
        st.markdown('<div class="callout">✅ Aucune anomalie statistique détectée sur la période sélectionnée.</div>', unsafe_allow_html=True)

    # Évolution H1/H2 par dimension
    st.markdown("<div class='section-title'>🔄 Dynamique H1→H2 par dimension</div>", unsafe_allow_html=True)
    dims_k = ["tone","stability","coop","economic","diplomatic","media_vol","source_diversity"]
    dims_l = ["Tonalité","Stabilité","Coopération","Économique","Diplomatique","Vol. média","Diversité"]
    delta_vals = [h1h2["H2"].get(k,0) - h1h2["H1"].get(k,0) for k in dims_k]
    colors_d   = ["#2e7d32" if v >= 0 else "#c62828" for v in delta_vals]
    fig_d = go.Figure(go.Bar(x=dims_l, y=delta_vals, marker_color=colors_d))
    fig_d.add_hline(y=0, line_dash="solid", line_color="#999")
    fig_d.update_layout(title="Variation H2 vs H1 (barres vertes = amélioration)", height=300, margin=dict(t=40,b=10))
    st.plotly_chart(fig_d, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — ESPACE PROFIL DÉCIDEUR
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    pkey = pinfo["key"]
    pcol = pinfo["color"]

    st.markdown(f'<div class="profile-tag" style="background:{pcol}">{pinfo["icon"]} Espace {selected_profile}</div>', unsafe_allow_html=True)

    # Insight IA (déjà présent)
    st.markdown("<div class='section-title'>🤖 Note d'analyse personnalisée</div>", unsafe_allow_html=True)
    insight = generate_insight(df_view, pkey, scores, risk_df)
    st.markdown(f'<div class="insight-box">{insight}</div>', unsafe_allow_html=True)

    # Métriques clés selon profil (conserver votre code existant)
    st.markdown("<div class='section-title'>📌 Indicateurs clés</div>", unsafe_allow_html=True)
    if pkey == "investor":
        r1, r2, r3, r4 = st.columns(4)
        with r1: metric_card("Score attractivité", f"{scores['total']}/100", "Indice 7 dimensions", pcol)
        with r2: metric_card("Risque souverain", f"{risk_global:.0f}/100", "Perception mensuelle", "#c62828")
        with r3: metric_card("Couverture éco.", f"{scores['economic']:.0f}/100", "Signal investissement", "#0d6b3f")
        with r4: metric_card("Stabilité", f"{scores['stability']:.0f}/100", "Goldstein normalisé", "#2e4b8f")

        st.markdown("<div class='section-title'>📊 Secteurs économiques — Répartition</div>", unsafe_allow_html=True)
        econ_df = df_view[df_view["is_economic"]]["event_root"].value_counts().reset_index().head(10)
        econ_df.columns = ["Secteur","N"]
        fig = px.treemap(econ_df, path=["Secteur"], values="N",
                         color="N", color_continuous_scale="Greens",
                         title="Thématiques économiques (taille = volume médiatique)", height=360)
        st.plotly_chart(fig, use_container_width=True)

    elif pkey == "diplomat":
        r1, r2, r3, r4 = st.columns(4)
        with r1: metric_card("Coopération", f"{scores['coop']:.0f}/100", "Actions coopératives", pcol)
        with r2: metric_card("Diplomatique", f"{scores['diplomatic']:.0f}/100", "Couverture diplo.", "#0d6b3f")
        with r3: metric_card("Tonalité", f"{avg_tone:.2f}", "Perception globale", "#d18f2b")
        with r4: metric_card("Partenaires actifs", f"{len(get_country_relations(df_view))}", "Pays en interaction", "#2e4b8f")

        st.markdown("<div class='section-title'>🤝 Activité diplomatique mensuelle</div>", unsafe_allow_html=True)
        diplo_m = df_view[df_view["is_diplomatic"]].groupby("month").size().reset_index(name="N")
        if not diplo_m.empty:
            fig = px.line(diplo_m, x="month", y="N", markers=True,
                          title="Événements diplomatiques par mois",
                          color_discrete_sequence=[pcol], height=300)
            st.plotly_chart(fig, use_container_width=True)

    elif pkey == "apiex":
        r1, r2, r3, r4 = st.columns(4)
        with r1: metric_card("Score IED", f"{scores['total']}/100", "Attractivité composite", pcol)
        with r2: metric_card("Économique", f"{scores['economic']:.0f}/100", "Couverture économique", "#0d6b3f")
        with r3: metric_card("Tonalité éco.", f"{safe_mean(df_view[df_view['is_economic']]['AvgTone']):.2f}", "Secteur éco.", "#d18f2b")
        with r4: metric_card("Sources intl.", f"{(df_view['source_type']=='Internationale').sum():,}", "Articles internationaux", "#2e4b8f")

        st.markdown("<div class='section-title'>🌐 Visibilité internationale — Pays sources</div>", unsafe_allow_html=True)
        intl_rel = get_country_relations(df_view)
        if not intl_rel.empty:
            fig = px.scatter(intl_rel.head(20), x="tonalite", y="stabilite",
                             size="volume", color="tonalite",
                             color_continuous_scale="RdYlGn", hover_name="pays",
                             color_continuous_midpoint=0,
                             title="Partenaires : Tonalité vs Stabilité (taille = volume)", height=380)
            fig.add_vline(x=0, line_dash="dash", annotation_text="Neutre")
            fig.add_hline(y=0, line_dash="dash")
            st.plotly_chart(fig, use_container_width=True)

    elif pkey == "journalist":
        anomalies = detect_anomalies(df_view)
        r1, r2, r3, r4 = st.columns(4)
        with r1: metric_card("Événements", f"{len(df_view):,}", "Dans la sélection", pcol)
        with r2: metric_card("Anomalies", f"{len(anomalies)}", "Pics / Creux détectés", "#c62828")
        with r3: metric_card("Sources uniques", f"{df_view['domain'].nunique():,}", "Domaines médias", "#0d6b3f")
        with r4: metric_card("Tonalité", f"{avg_tone:.2f}", "Signal global", "#d18f2b")

        st.markdown("<div class='section-title'>📆 Timeline des événements clés</div>", unsafe_allow_html=True)
        top_monthly = df_view.sort_values("AvgTone").groupby("month").head(1)[["event_date","event_root","AvgTone","actor1_country","SOURCEURL"]].sort_values("event_date")
        if not top_monthly.empty and "SOURCEURL" in top_monthly.columns:
            top_monthly["event_date"] = top_monthly["event_date"].dt.date
            cfg = {"SOURCEURL": st.column_config.LinkColumn(display_text="🔗 Source")}
            st.dataframe(top_monthly.head(20), use_container_width=True, column_config=cfg)

    else:  # researcher
        r1, r2, r3, r4 = st.columns(4)
        with r1: metric_card("N observations", f"{len(df_view):,}", "Taille de l'échantillon", pcol)
        with r2: metric_card("Période", f"{(df_view['event_date'].max()-df_view['event_date'].min()).days}j", "Durée couverte", "#0d6b3f")
        with r3: metric_card("Variables actives", "12", "Dimensions GDELT", "#d18f2b")
        with r4: metric_card("Sources uniques", f"{df_view['domain'].nunique():,}", "Diversité médias", "#2e4b8f")

        st.markdown("<div class='section-title'>📐 Distribution statistique</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            fig = px.histogram(df_view, x="AvgTone", nbins=40,
                               title="Distribution AvgTone", color_discrete_sequence=[pcol], height=300)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.histogram(df_view, x="GoldsteinScale", nbins=40,
                               title="Distribution GoldsteinScale", color_discrete_sequence=["#0d6b3f"], height=300)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div class='section-title'>📈 Corrélation Tone ~ Goldstein</div>", unsafe_allow_html=True)

    # 1. Nettoyage des données (NumMentions n'étant pas utilisé dans le scatter, on peut l'exclure ici)
    corr_df = df_view[["AvgTone", "GoldsteinScale"]].dropna()

    # 2. Sécurité : Il faut au moins 2 lignes ET de la variance (plus d'une valeur unique par colonne)
    # Cela évite les crashs mathématiques de la trendline OLS de Plotly
    if len(corr_df) >= 2 and corr_df["AvgTone"].nunique() > 1 and corr_df["GoldsteinScale"].nunique() > 1:
        
        sample_size = min(3000, len(corr_df))
        df_sample = corr_df.sample(sample_size, random_state=42)
        
        # Calcul du r sur l'échantillon pour correspondre exactement à la courbe OLS affichée
        r_value = df_sample["AvgTone"].corr(df_sample["GoldsteinScale"])
        
        fig_corr = px.scatter(
            df_sample,
            x="AvgTone", 
            y="GoldsteinScale", 
            opacity=0.4,
            trendline="ols", 
            color_discrete_sequence=[pcol], 
            height=320,
            title=f"Corrélation r = {r_value:.3f}"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("Données insuffisantes ou constantes. Impossible de calculer la corrélation et d'ajuster la courbe.")
        

    # ========== NOUVEAU : ACTIONS SUGGÉRÉES ==========
    st.markdown("<div class='section-title'>🎯 Actions suggérées</div>", unsafe_allow_html=True)

    # Calculs complémentaires pour les recommandations
    attract_score = scores['total']
    risk_global = risk_df["risk_score"].mean() if not risk_df.empty else 50
    tone_avg = avg_tone
    gold_avg = avg_gold
    coop_share = df_view["is_cooperation"].mean()
    econ_share = df_view["is_economic"].mean()
    anomalies_count = len(detect_anomalies(df_view))

    if pkey == "investor":
        if attract_score > 70:
            recommendation = "🔹 **Opportunité d'investissement** : L'attractivité est très forte. Envisagez des investissements dans les secteurs économiques les plus médiatisés."
        elif attract_score > 40:
            recommendation = "🔸 **Potentiel modéré** : Surveillez l'évolution de la tonalité. Climat des affaires en construction, privilégiez les partenariats à faible risque."
        else:
            recommendation = "⚠️ **Prudence** : La perception est dégradée. Attendez des signaux de stabilisation avant tout engagement lourd."
        st.markdown(f'<div class="callout">{recommendation}</div>', unsafe_allow_html=True)
        st.write("**Actions concrètes :**")
        st.write("- Identifier les secteurs avec la meilleure tonalité (ex: coopération économique).")
        st.write("- Analyser les anomalies pour détecter des pics d'actualité pouvant influencer le risque.")
        st.write("- Utiliser le tableau des partenaires pour cibler les pays stables.")

    elif pkey == "diplomat":
        if tone_avg > 0 and gold_avg > 0:
            recommendation = "🤝 **Climat favorable** : Renforcez les initiatives de coopération bilatérale. La couverture médiatique soutient l'image du Bénin."
        else:
            recommendation = "🌍 **Dialogue nécessaire** : Les indicateurs suggèrent des tensions. Proposez des programmes de coopération culturelle ou économique pour inverser la tendance."
        st.markdown(f'<div class="callout">{recommendation}</div>', unsafe_allow_html=True)
        st.write("**Actions concrètes :**")
        st.write("- Cibler les pays partenaires affichant une tonalité positive (voir carte des partenaires).")
        st.write("- Organiser des sommets bilatéraux avec les pays en zone de vigilance.")
        st.write("- Amplifier la communication sur les réussites diplomatiques via les médias internationaux.")

    elif pkey == "apiex":
        if attract_score > 65:
            recommendation = "📈 **Attractivité élevée** : Le Bénin bénéficie d'une couverture économique favorable. Capitalisez sur les secteurs porteurs."
        elif attract_score > 35:
            recommendation = "📊 **Potentiel à activer** : La perception économique est modérée. Lancez des campagnes ciblées pour promouvoir les niches d'excellence."
        else:
            recommendation = "⚠️ **Visibilité à renforcer** : La couverture économique est faible. Priorisez des actions de communication et des missions économiques."
        st.markdown(f'<div class="callout">{recommendation}</div>', unsafe_allow_html=True)
        st.write("**Actions concrètes :**")
        st.write("- Identifier les thématiques économiques les plus médiatisées et les valoriser dans les pitchs IED.")
        st.write("- Collaborer avec les sources internationales pour améliorer la tonalité.")
        st.write("- Organiser des webinaires sectoriels en s'appuyant sur les données du dashboard.")

    elif pkey == "journalist":
        if anomalies_count > 0:
            recommendation = "📰 **Actualité chaude** : Des anomalies statistiques détectées. Ces pics peuvent constituer des angles éditoriaux forts."
        else:
            recommendation = "📝 **Couverture stable** : Pas d'anomalie majeure. Explorez les thématiques dominantes pour des analyses de fond."
        st.markdown(f'<div class="callout">{recommendation}</div>', unsafe_allow_html=True)
        st.write("**Actions concrètes :**")
        st.write("- Télécharger les données des anomalies pour enquêter sur les causes.")
        st.write("- Utiliser le tableau des articles pour trouver des sources primaires.")
        st.write("- Comparer les word clouds nationaux vs internationaux pour identifier les biais de traitement.")

    else:  # researcher
        recommendation = "🔬 **Analyse approfondie** : Les données GDELT offrent un potentiel de modélisation. Explorez les séries temporelles et le clustering."
        st.markdown(f'<div class="callout">{recommendation}</div>', unsafe_allow_html=True)
        st.write("**Actions concrètes :**")
        st.write("- Exporter les scores de risque et d'attractivité pour des analyses longitudinales.")
        st.write("- Utiliser le clustering des partenaires pour des études géopolitiques.")
        st.write("- Corréler les indicateurs GDELT avec des données externes (IDE, indicateurs de gouvernance).")

    # Tableau de bord personnalisé (métriques clés)
    st.markdown("<div class='section-title'>📊 Tableau de bord personnalisé</div>", unsafe_allow_html=True)
    col_met1, col_met2, col_met3 = st.columns(3)
    with col_met1:
        st.metric("Score attractivité", f"{scores['total']:.1f}/100", 
                  delta=f"{scores['total'] - h1h2['H1']['total']:.1f}" if h1h2['H1']['total'] else None)
    with col_met2:
        st.metric("Niveau de risque", f"{risk_global:.1f}/100",
                  delta="Élevé" if risk_global > 60 else ("Modéré" if risk_global > 30 else "Faible"))
    with col_met3:
        st.metric("Anomalies détectées", f"{anomalies_count}",
                  delta="Pics/creux" if anomalies_count > 0 else "Stable")
        
# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — EXPORTS & DONNÉES
# ══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown("<div class='section-title'>⬇️ Télécharger les données filtrées</div>", unsafe_allow_html=True)

    ec1, ec2, ec3 = st.columns(3)

    with ec1:
        csv_data = df_view.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Données CSV (complet)",
            data=csv_data,
            file_name="benin_gdelt_filtered.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with ec2:
        scores_df = pd.DataFrame([scores])
        csv_s = scores_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📊 Score attractivité CSV",
            data=csv_s,
            file_name="scores_attractivite_benin.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with ec3:
        if not risk_df.empty:
            csv_r = risk_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⚠️ Score risque CSV",
                data=csv_r,
                file_name="risque_mensuel_benin.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.markdown("---")
    st.markdown("<div class='section-title'>📄 Rapport HTML (imprimable en PDF)</div>", unsafe_allow_html=True)
    if st.button("🖨️ Générer le rapport HTML", use_container_width=False):
        with st.spinner("Génération…"):
            html_report = export_html(df_view, scores, risk_df, selected_profile)
            st.download_button(
                label="⬇️ Télécharger le rapport",
                data=html_report.encode("utf-8"),
                file_name=f"rapport_observatoire_benin_{pd.Timestamp.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=False,
            )

    st.markdown("---")
    st.markdown("<div class='section-title'>📊 Aperçu des données</div>", unsafe_allow_html=True)
    n_preview = st.slider("Lignes à afficher", 10, 200, 50)
    st.dataframe(df_view.head(n_preview), use_container_width=True, height=380)

    st.markdown("---")
    st.markdown("<div class='section-title'>🔢 Statistiques descriptives</div>", unsafe_allow_html=True)
    desc_cols = [c for c in ["AvgTone","GoldsteinScale","NumMentions","NumSources","NumArticles"] if c in df_view.columns]
    st.dataframe(df_view[desc_cols].describe().round(3), use_container_width=True)

    st.markdown("<div class='section-title'>📌 Définitions des indicateurs</div>", unsafe_allow_html=True)
    with st.expander("ℹ️ Lire le glossaire"):
        st.markdown("""
| Indicateur | Définition |
|---|---|
| **AvgTone** | Tonalité moyenne de l'article (négatif = critique, positif = favorable). Source : GDELT. |
| **GoldsteinScale** | Échelle de Goldstein (-10 = déstabilisant, +10 = coopératif). Mesure l'impact potentiel sur la stabilité d'un pays. |
| **Score attractivité** | Indice composite (0-100) pondérant 7 dimensions : tonalité (22%), stabilité (20%), coopération (18%), économique (15%), diplomatique (12%), volume (8%), diversité sources (5%). |
| **Score de risque** | Indice mensuel (0-100) combinant tonalité négative (40%), goldstein négatif (30%), part des conflits (30%). |
| **Couverture nationale** | Source identifiée comme béninoise via l'extension de domaine (.bj) ou nom de média référencé. |
| **H1 / H2** | Comparaison semestrielle : H1 = janvier-juin, H2 = juillet-décembre 2025. |
""")

# ─────────────────────────────────────────────────────────────────────────────
# PIED DE PAGE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f'<div style="color:#888;font-size:.82rem;text-align:center">🇧🇯 Observatoire médiatique du Bénin — Source : GDELT Event Database · '
    f'Dernière mise à jour : {pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")} · v3.0</div>',
    unsafe_allow_html=True,
)