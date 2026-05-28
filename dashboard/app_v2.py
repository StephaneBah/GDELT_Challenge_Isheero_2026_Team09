from pathlib import Path
from urllib.parse import urlparse
from datetime import timedelta
import io
import base64
import re

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from wordcloud import WordCloud
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# Nouvelles fonctions pour les relations internationales et anomalies détaillées
# ============================================================================
def get_country_relations(df: pd.DataFrame, target_country: str = "Benin") -> pd.DataFrame:
    """
    Extrait les pays ayant interagi avec le Bénin (comme acteur1 ou acteur2).
    Retourne un DataFrame avec le pays partenaire, le nombre d'événements, tonalité moyenne, etc.
    """
    if df.empty:
        return pd.DataFrame()
    # Normaliser les noms de pays
    target = target_country.lower()
    # Acteur1 = Bénin, Acteur2 = partenaire
    mask_benin_actor1 = df["actor1_country"].str.lower() == target
    partners_actor2 = df[mask_benin_actor1]["actor2_country"].copy() if "actor2_country" in df.columns else pd.Series()
    # Acteur2 = Bénin, Acteur1 = partenaire
    mask_benin_actor2 = df["actor2_country"].str.lower() == target if "actor2_country" in df.columns else pd.Series(False, index=df.index)
    partners_actor1 = df[mask_benin_actor2]["actor1_country"].copy() if "actor1_country" in df.columns else pd.Series()
    partners = pd.concat([partners_actor2, partners_actor1], ignore_index=True)
    partners = partners[partners.notna() & (partners.str.lower() != target) & (partners.str.strip() != "")]
    if partners.empty:
        return pd.DataFrame()
    # Agrégation
    partner_stats = partners.value_counts().reset_index()
    partner_stats.columns = ["pays", "volume"]
    # Ajouter tonalité moyenne pour chaque partenaire
    def get_avg_tone(pays):
        mask = ((df["actor1_country"] == pays) & (df["actor2_country"].str.lower() == target)) | \
               ((df["actor2_country"] == pays) & (df["actor1_country"].str.lower() == target))
        return df[mask]["AvgTone"].mean()
    partner_stats["tonalite"] = partner_stats["pays"].apply(get_avg_tone)
    partner_stats = partner_stats.sort_values("volume", ascending=False)
    return partner_stats

def get_articles_for_anomaly(df: pd.DataFrame, anomaly_date, metric: str) -> pd.DataFrame:
    """
    Retourne les articles (SOURCEURL, event_root, AvgTone, etc.) pour une date donnée
    et pour la métrique concernée (volume, avg_tone, avg_gold).
    """
    if df.empty or "event_date" not in df.columns:
        return pd.DataFrame()
    date_obj = pd.to_datetime(anomaly_date).date()
    day_df = df[df["event_date"].dt.date == date_obj].copy()
    if metric == "volume":
        # Tous les articles du jour
        return day_df[["SOURCEURL", "event_root", "AvgTone", "GoldsteinScale", "actor1_country"]].dropna(subset=["SOURCEURL"])
    elif metric == "avg_tone":
        # Articles avec tonalité extrême (hors norme)
        tone_mean = day_df["AvgTone"].mean()
        tone_std = day_df["AvgTone"].std()
        if tone_std == 0:
            return pd.DataFrame()
        threshold = 2 * tone_std
        extreme = day_df[(day_df["AvgTone"] < tone_mean - threshold) | (day_df["AvgTone"] > tone_mean + threshold)]
        return extreme[["SOURCEURL", "event_root", "AvgTone", "GoldsteinScale", "actor1_country"]].dropna(subset=["SOURCEURL"])
    elif metric == "avg_gold":
        gold_mean = day_df["GoldsteinScale"].mean()
        gold_std = day_df["GoldsteinScale"].std()
        if gold_std == 0:
            return pd.DataFrame()
        threshold = 2 * gold_std
        extreme = day_df[(day_df["GoldsteinScale"] < gold_mean - threshold) | (day_df["GoldsteinScale"] > gold_mean + threshold)]
        return extreme[["SOURCEURL", "event_root", "AvgTone", "GoldsteinScale", "actor1_country"]].dropna(subset=["SOURCEURL"])
    return pd.DataFrame()

def download_csv(df: pd.DataFrame, filename: str) -> str:
    """Génère un lien de téléchargement CSV à partir d'un DataFrame."""
    csv = df.to_csv(index=False).encode('utf-8')
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Télécharger CSV</a>'
    return href

def cluster_partners(relations_df: pd.DataFrame) -> tuple:
    """
    Applique PCA + KMeans sur les partenaires du Bénin.
    Paramètres attendus dans relations_df : volume, tonalite, avg_gold (stabilité)
    Retourne (df avec cluster, figure PCA, modèle kmeans)
    """
    if relations_df.empty or len(relations_df) < 3:
        return relations_df, None, None
    # Préparer les features
    features = ['volume', 'tonalite', 'avg_gold']
    available = [f for f in features if f in relations_df.columns]
    if len(available) < 2:
        return relations_df, None, None
    X = relations_df[available].copy()
    # Normalisation
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    # PCA pour 2 composantes
    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(X_scaled)
    relations_df['pca1'] = pca_result[:, 0]
    relations_df['pca2'] = pca_result[:, 1]
    # Nombre de clusters (min 2, max 3 pour lisibilité)
    n_clusters = min(3, len(relations_df))
    if len(relations_df) >= 4:
        n_clusters = 3
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    relations_df['cluster'] = kmeans.fit_predict(X_scaled)
    # Interprétation des clusters (selon volume et tonalité moyens)
    cluster_means = relations_df.groupby('cluster')[available].mean()
    cluster_names = {}
    for c in cluster_means.index:
        vol = cluster_means.loc[c, 'volume']
        tone = cluster_means.loc[c, 'tonalite']
        if tone > 0:
            cluster_names[c] = f"🟢 Partenaires positifs (vol={vol:.0f})"
        else:
            cluster_names[c] = f"🔴 Partenaires sensibles (vol={vol:.0f})"
    relations_df['cluster_label'] = relations_df['cluster'].map(cluster_names)
    # Figure PCA
    fig = px.scatter(relations_df, x='pca1', y='pca2', color='cluster_label',
                     hover_name='pays', size='volume', text='pays',
                     title="Classification des partenaires (ACP + K‑means)",
                     labels={'pca1': 'Composante 1', 'pca2': 'Composante 2'})
    fig.update_traces(textposition='top center')
    return relations_df, fig, kmeans

# ============================================================================
# Configuration de la page et paramètres URL
# ============================================================================
if "initialized_url" not in st.session_state:
    st.session_state["scope"] = st.query_params.get("scope", "Couverture complète")
    roots_str = st.query_params.get("roots", "")
    st.session_state["roots_list"] = [r for r in roots_str.split(",") if r] if roots_str else None
    st.session_state["initialized_url"] = True

st.set_page_config(
    page_title="Observatoire médiatique du Bénin | Attractivité territoriale",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Styles CSS personnalisés (conservés et enrichis)
# ============================================================================
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
.anomaly-highlight {
  background-color: #fff0f0;
  border-left: 4px solid #d32f2f;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  margin: 0.5rem 0;
}
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# Constantes et chemins
# ============================================================================
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

# Liste indicative de domaines nationaux béninois (à enrichir)
BENIN_DOMAINS = {
    "ortb.bj", "beninwebtv.com", "benininfo.com", "lanouvelletribune.info",
    "matinlibre.com", "acotonou.com", "beninmonde.com", "beninreveil.com",
    "24haubenin.info", "leconomistebenin.com", "fr.africanews.com", "bj"
}

# ============================================================================
# Fonctions utilitaires
# ============================================================================
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

def classify_source_type(domain: str) -> str:
    """Classifie une source comme 'Nationale' ou 'Internationale'."""
    if not domain:
        return "Inconnue"
    for benin_domain in BENIN_DOMAINS:
        if benin_domain in domain or domain.endswith(f".{benin_domain}"):
            return "Nationale"
    return "Internationale"

def detect_anomalies(df: pd.DataFrame, column: str = "GLOBALEVENTID", date_col: str = "event_date", method: str = "iqr") -> pd.DataFrame:
    """Détecte les anomalies quotidiennes sur le volume, la tonalité et le goldstein."""
    if df.empty or date_col not in df.columns:
        return pd.DataFrame()
    df_daily = df.groupby(df[date_col].dt.date).agg(
        volume=(column, "count"),
        avg_tone=("AvgTone", "mean"),
        avg_gold=("GoldsteinScale", "mean")
    ).reset_index()
    df_daily.columns = ["date", "volume", "avg_tone", "avg_gold"]
    
    anomalies = []
    for metric in ["volume", "avg_tone", "avg_gold"]:
        series = df_daily[metric].dropna()
        if len(series) < 2:
            continue
        if method == "iqr":
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            mask = (df_daily[metric] < lower) | (df_daily[metric] > upper)
        else:
            mean = series.mean()
            std = series.std()
            if std == 0:
                continue
            mask = (df_daily[metric] - mean).abs() > 2 * std
        for idx in df_daily[mask].index:
            anomalies.append({
                "date": df_daily.loc[idx, "date"],
                "métrique": metric,
                "valeur": df_daily.loc[idx, metric],
                "seuil_sup": upper if method == "iqr" else mean + 2*std,
                "seuil_inf": lower if method == "iqr" else mean - 2*std,
            })
    return pd.DataFrame(anomalies)

def compute_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule un score de risque mensuel (0=faible risque, 100=risque élevé)."""
    if df.empty or "event_date" not in df.columns:
        return pd.DataFrame()
    df_month = df.copy()
    df_month["month"] = df_month["event_date"].dt.to_period("M")
    monthly = df_month.groupby("month").agg(
        avg_tone=("AvgTone", "mean"),
        avg_gold=("GoldsteinScale", "mean"),
        conflict_volume=("is_conflict", "sum")
    ).reset_index()
    monthly["month"] = monthly["month"].astype(str)
    
    # Normalisation min-max
    tone_norm = (monthly["avg_tone"] - monthly["avg_tone"].min()) / (monthly["avg_tone"].max() - monthly["avg_tone"].min())
    gold_norm = (monthly["avg_gold"] - monthly["avg_gold"].min()) / (monthly["avg_gold"].max() - monthly["avg_gold"].min())
    conflict_norm = (monthly["conflict_volume"] - monthly["conflict_volume"].min()) / (monthly["conflict_volume"].max() - monthly["conflict_volume"].min())
    
    # Le risque est élevé quand tonalité négative (inverse de tone_norm), goldstein négatif (inverse) et conflits élevés
    risk = ( (1 - tone_norm) * 0.4 + (1 - gold_norm) * 0.3 + conflict_norm * 0.3 ) * 100
    monthly["risk_score"] = risk.fillna(0)
    return monthly[["month", "risk_score"]]

def generate_wordcloud(df: pd.DataFrame, text_column: str = "event_root", title: str = "Nuage de mots") -> plt.Figure:
    """Génère un wordcloud à partir des valeurs d'une colonne texte."""
    if df.empty or text_column not in df.columns:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Données insuffisantes", ha="center", va="center")
        ax.axis("off")
        return fig
    text = " ".join(df[text_column].astype(str).fillna(""))
    if not text.strip():
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Aucun texte disponible", ha="center", va="center")
        ax.axis("off")
        return fig
    wordcloud = WordCloud(width=800, height=400, background_color="white", colormap="viridis").generate(text)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(title, fontsize=14)
    return fig

def render_articles_table(df: pd.DataFrame) -> None:
    """Affiche un tableau interactif des articles avec liens et filtres."""
    if df.empty:
        st.info("Aucun article à afficher.")
        return
    cols = ["event_date", "actor1_country", "actor2_country", "event_root", "source_type", "language", "SOURCEURL", "AvgTone", "GoldsteinScale"]
    available = [c for c in cols if c in df.columns]
    if not available:
        st.warning("Colonnes nécessaires manquantes pour le tableau.")
        return
    table_df = df[available].copy()
    if "event_date" in table_df.columns:
        table_df["event_date"] = table_df["event_date"].dt.date
    rename_map = {
        "event_date": "Date",
        "actor1_country": "Acteur principal",
        "actor2_country": "Acteur secondaire",
        "event_root": "Thématique",
        "source_type": "Type source",
        "language": "Langue",
        "SOURCEURL": "Lien",
        "AvgTone": "Tonalité",
        "GoldsteinScale": "Stabilité",
    }
    table_df.rename(columns={k: v for k, v in rename_map.items() if k in table_df.columns}, inplace=True)
    column_config = {}
    if "Lien" in table_df.columns:
        column_config["Lien"] = st.column_config.LinkColumn(
            label="Lien",
            help="Cliquer pour ouvrir l'article",
            display_text="🔗 Voir l'article"
        )
    st.dataframe(table_df, use_container_width=True, height=400, column_config=column_config)

def export_to_html(df_view: pd.DataFrame, kpi_data: dict, risk_df: pd.DataFrame) -> str:
    """Génère un rapport HTML simplifié pour impression/PDF."""
    html = f"""
    <html>
    <head><title>Rapport attractivité Bénin</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2rem; }}
        .kpi {{ display: flex; gap: 1rem; flex-wrap: wrap; }}
        .card {{ border: 1px solid #ccc; padding: 1rem; border-radius: 8px; width: 200px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f2f2f2; }}
    </style>
    </head>
    <body>
    <h1>Observatoire médiatique du Bénin</h1>
    <p>Généré le {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>
    <div class="kpi">
        <div class="card"><b>Volume</b><br>{kpi_data.get('volume', 'N/A')}</div>
        <div class="card"><b>AvgTone</b><br>{kpi_data.get('avg_tone', 'N/A')}</div>
        <div class="card"><b>Goldstein</b><br>{kpi_data.get('avg_gold', 'N/A')}</div>
        <div class="card"><b>Score attractivité</b><br>{kpi_data.get('attract_score', 'N/A')}</div>
    </div>
    <h2>Score de risque mensuel</h2>
    {risk_df.to_html(index=False) if not risk_df.empty else "<p>Non disponible</p>"}
    <h2>Données filtrées (extrait)</h2>
    {df_view.head(100).to_html()}
    </body>
    </html>
    """
    return html

def generate_weekly_insight(df: pd.DataFrame, last_n_days: int = 7) -> str:
    """Génère un résumé textuel des tendances de la dernière période."""
    if df.empty or "event_date" not in df.columns:
        return "Données insuffisantes pour générer un résumé."
    max_date = df["event_date"].max()
    start_date = max_date - timedelta(days=last_n_days)
    recent = df[df["event_date"] >= start_date]
    if recent.empty:
        return "Aucune donnée récente disponible."
    volume = len(recent)
    tone_avg = recent["AvgTone"].mean()
    gold_avg = recent["GoldsteinScale"].mean()
    top_themes = recent["event_root"].value_counts().head(3).index.tolist()
    coop_share = recent["is_cooperation"].mean() if "is_cooperation" in recent.columns else 0
    insight = f"""
    **Résumé IA (derniers {last_n_days} jours) :**  
    - {volume} événements recensés.  
    - Tonalité moyenne : {tone_avg:.2f} → {'plutôt positive' if tone_avg > 0 else 'plutôt négative'}.  
    - Stabilité (Goldstein) : {gold_avg:.2f}.  
    - Thèmes dominants : {', '.join(top_themes)}.  
    - Part d'actions coopératives : {coop_share:.0%}.  
    → Dynamique générale : {"favorable à l'attractivité" if tone_avg > 0 and gold_avg > 0 else 'vigilance requise sur certains signaux'}.
    """
    return insight

def recommendations_for_profile(profile: str, attract_score: float, risk_score: float, tone: float, gold: float) -> str:
    """Recommandations pré-rédigées selon le profil décideur."""
    if profile == "Investisseur":
        if attract_score > 70:
            return "🔹 **Opportunité** : L'attractivité est forte. Envisagez des investissements dans les secteurs économiques les plus médiatisés (voir onglet Analyse)."
        elif attract_score > 40:
            return "🔸 **Potentiel modéré** : Surveillez l'évolution de la tonalité. Un climat des affaires en construction, privilégiez les partenariats à faible risque."
        else:
            return "⚠️ **Prudence** : La perception est dégradée. Attendez des signaux de stabilisation avant tout engagement lourd."
    elif profile == "Diplomate":
        if tone > 0 and gold > 0:
            return "🤝 **Climat favorable** : Renforcez les initiatives de coopération bilatérale. La couverture médiatique soutient l'image du Bénin."
        else:
            return "🌍 **Dialogue nécessaire** : Les indicateurs suggèrent des tensions. Proposez des programmes de coopération culturelle ou économique pour inverser la tendance."
    else:  # Décideur local
        if risk_score < 30:
            return "✅ **Stabilité appréciable** : Communiquez sur les réussites en matière de sécurité et de développement. Utilisez les données comme preuve."
        else:
            return "📢 **Urgence de communication** : Le risque perçu est élevé. Lancez des campagnes ciblant les thématiques les plus négatives (voir onglet Analyse)."
    return "Aucune recommandation disponible."

# ============================================================================
# Chargement et préparation des données (avec enrichissement)
# ============================================================================
@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)

    for col in ["AvgTone", "GoldsteinScale", "NumMentions", "NumSources", "NumArticles", "ActionGeo_Lat", "ActionGeo_Long"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Date
    if "SQLDATE" in df.columns:
        df["event_date"] = pd.to_datetime(df["SQLDATE"].astype(str), errors="coerce")
    elif "MonthYear" in df.columns:
        df["event_date"] = pd.to_datetime(df["MonthYear"].astype(str), format="%Y%m", errors="coerce")
    else:
        df["event_date"] = pd.NaT
    df["month"] = df["event_date"].dt.to_period("M").dt.to_timestamp()

    # Événements roots
    if "EventRootLabel" in df.columns and "EventRootCode" in df.columns:
        df["event_root"] = df["EventRootLabel"].fillna(df["EventRootCode"].astype(str))
    elif "EventRootLabel" in df.columns:
        df["event_root"] = df["EventRootLabel"]
    elif "EventRootCode" in df.columns:
        df["event_root"] = df["EventRootCode"].astype(str)
    else:
        df["event_root"] = "Inconnu"
    df["event_root"] = df["event_root"].fillna("Inconnu").astype(str).replace(ROOT_TRANSLATIONS)

    # Quadrant
    if "QuadClassLabel" in df.columns and "QuadClass" in df.columns:
        df["quad_label"] = df["QuadClassLabel"].fillna(df["QuadClass"].astype(str))
    elif "QuadClassLabel" in df.columns:
        df["quad_label"] = df["QuadClassLabel"]
    elif "QuadClass" in df.columns:
        df["quad_label"] = df["QuadClass"].astype(str)
    else:
        df["quad_label"] = "Inconnu"
    df["quad_label"] = df["quad_label"].fillna("Inconnu").astype(str)

    # Acteur principal
    actor1_label = df["Actor1CountryLabel"] if "Actor1CountryLabel" in df.columns else pd.Series([pd.NA] * len(df))
    actor1_code = df["Actor1CountryCode"] if "Actor1CountryCode" in df.columns else pd.Series([pd.NA] * len(df))
    df["actor1_country"] = actor1_label.fillna(actor1_code).fillna("Inconnu").replace("", "Inconnu")
    
    # Acteur secondaire
    actor2_label = df["Actor2CountryLabel"] if "Actor2CountryLabel" in df.columns else pd.Series([pd.NA] * len(df))
    actor2_code = df["Actor2CountryCode"] if "Actor2CountryCode" in df.columns else pd.Series([pd.NA] * len(df))
    df["actor2_country"] = actor2_label.fillna(actor2_code).fillna("Inconnu").replace("", "Inconnu")
    
    # Type d'acteur secondaire (pour classification)
    if "Actor2Type1Label" in df.columns:
        df["actor2_type_label"] = df["Actor2Type1Label"].fillna("Inconnu")
    elif "Actor2Type1Code" in df.columns:
        df["actor2_type_label"] = df["Actor2Type1Code"].fillna("Inconnu")
    else:
        df["actor2_type_label"] = "Inconnu"

    # Codes pour coop/économie/conflit
    root_codes = pd.to_numeric(df["EventRootCode"], errors="coerce").fillna(-1).astype(int) if "EventRootCode" in df.columns else pd.Series([-1] * len(df))
    event_codes = pd.to_numeric(df["EventCode"], errors="coerce").fillna(-1).astype(int) if "EventCode" in df.columns else pd.Series([-1] * len(df))
    df["is_economic"] = event_codes.isin(ECONOMIC_CODES_INT)
    df["is_diplomatic"] = event_codes.isin(DIPLO_CODES_INT) | root_codes.isin({4, 5})
    df["is_cooperation"] = root_codes.isin(COOP_ROOTS_INT)
    df["is_conflict"] = root_codes.isin(CONFLICT_ROOTS_INT)
    q = df["quad_label"].str.lower()
    df["is_coop_quad"] = q.str.contains("cooper")
    df["is_conf_quad"] = q.str.contains("conflict")

    # Enrichissement : source_type, langue, domaine
    if "SOURCEURL" in df.columns:
        df["domain"] = df["SOURCEURL"].apply(lambda x: normalize_domain(x) if pd.notna(x) else "")
        df["source_type"] = df["domain"].apply(classify_source_type)
    else:
        df["source_type"] = "Inconnue"
        df["domain"] = ""
    
    # Langue – on suppose une colonne "Language" ou on déduit du domaine (ex: .fr)
    if "Language" in df.columns:
        df["language"] = df["Language"].fillna("inconnu")
    else:
        # Déduction simple : domaine .fr → français, .bj → français, .com → anglais par défaut
        df["language"] = "inconnu"
        if "domain" in df.columns:
            df.loc[df["domain"].str.endswith((".fr", ".bj")), "language"] = "français"
            df.loc[df["domain"].str.contains(".com"), "language"] = "anglais"
    
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
    source_types: list[str],
    languages: list[str],
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
    if source_types:
        view = view[view["source_type"].isin(source_types)]
    if languages:
        view = view[view["language"].isin(languages)]

    return view

# ============================================================================
# Initialisation
# ============================================================================
if not DATA_PATH.exists():
    st.error(f"Fichier introuvable: {DATA_PATH}")
    st.stop()

df = load_data(DATA_PATH)
px.defaults.template = "simple_white"

# En-tête
st.markdown(
    """
<section class="hero">
    <div class="hero-eyebrow">Observatoire médiatique</div>
    <div class="hero-title">Attractivité territoriale du Bénin<br>Pilotée par les médias</div>
    <div class="hero-subtitle">
        Analysez la perception, les risques et les opportunités à partir de 100 000+ événements GDELT.
        Filtres dynamiques, word clouds, anomalies et recommandations pour décideurs.
    </div>
</section>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# Sidebar – Filtres enrichis
# ============================================================================
with st.sidebar:
    st.markdown("## Filtres")
    scope_options = [
        "Couverture complète",
        "Économique",
        "Diplomatique",
        "Coopération internationale",
        "Conflits",
    ]
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
        placeholder="Tous les types"
    )
    st.query_params["roots"] = ",".join(selected_roots)

    actor_options = sorted(df["actor1_country"].dropna().unique().tolist())
    selected_actor = st.multiselect("Pays acteur principal", options=actor_options)

    # Nouveaux filtres
    source_type_options = ["Nationale", "Internationale", "Inconnue"]
    selected_source_types = st.multiselect("Type de source", options=source_type_options)
    lang_options = sorted(df["language"].dropna().unique().tolist())
    selected_languages = st.multiselect("Langue de l'article", options=lang_options)

    hide_unknown = st.checkbox("Masquer les acteurs inconnus", value=False)

    tone_range = None
    if df["AvgTone"].notna().any():
        tone_min = float(df["AvgTone"].min())
        tone_max = float(df["AvgTone"].max())
        if tone_min < tone_max:
            tone_range = st.slider(
                "Plage AvgTone", min_value=round(tone_min,2), max_value=round(tone_max,2),
                value=(round(tone_min,2), round(tone_max,2))
            )
    gold_range = None
    if df["GoldsteinScale"].notna().any():
        gold_min = float(df["GoldsteinScale"].min())
        gold_max = float(df["GoldsteinScale"].max())
        if gold_min < gold_max:
            gold_range = st.slider(
                "Plage GoldsteinScale", min_value=round(gold_min,2), max_value=round(gold_max,2),
                value=(round(gold_min,2), round(gold_max,2))
            )
    

# Appliquer tous les filtres
df_view = apply_filters(
    df=df,
    scope_filters=scope_filters,
    date_range=date_range,
    selected_roots=selected_roots,
    selected_actor=selected_actor,
    hide_unknown=hide_unknown,
    tone_range=tone_range,
    gold_range=gold_range,
    source_types=selected_source_types,
    languages=selected_languages,
)

if df_view.empty:
    st.warning("Aucune donnée avec ces filtres. Élargissez la sélection.")
    st.stop()

# ============================================================================
# KPI principaux
# ============================================================================
avg_tone = safe_mean(df_view["AvgTone"])
avg_gold = safe_mean(df_view["GoldsteinScale"])
biz_share = float(df_view["is_economic"].mean()) if "is_economic" in df_view.columns else 0.0
coop_share = float((df_view["quad_label"].str.contains("Cooperation", na=False)).mean())
gold_norm = min(max((avg_gold + 10) / 20, 0), 1)
tone_norm = min(max((avg_tone + 20) / 40, 0), 1)
attract_score = round(coop_share * 35 + biz_share * 25 + gold_norm * 25 + tone_norm * 15, 1)

kpi_cols = st.columns(6)
with kpi_cols[0]: metric_card("Volume", f"{len(df_view):,}", "Événements filtrés")
with kpi_cols[1]: metric_card("AvgTone", f"{avg_tone:.2f}", "Sentiment média")
with kpi_cols[2]: metric_card("Goldstein", f"{avg_gold:.2f}", "Signal stabilité")
with kpi_cols[3]: metric_card("Coopération", f"{coop_share:.0%}", "Actions pacifiques")
with kpi_cols[4]: metric_card("Économie", f"{biz_share:.0%}", "Actions économiques")
with kpi_cols[5]: metric_card("Score attractivité", f"{attract_score:.1f} / 100", "Indice composite")

# ============================================================================
# Organisation en onglets
# ============================================================================
tab_overview, tab_articles, tab_analysis, tab_recommendations = st.tabs(
    ["📊 Vue d'ensemble", "📰 Articles & Sources", "📈 Analyse avancée", "💡 Recommandations décideurs"]
)

# ------------------ ONGLET VUE D'ENSEMBLE ------------------
with tab_overview:
    st.markdown("<div class='section-title'>Évolution temporelle</div>", unsafe_allow_html=True)
    monthly = df_view.groupby("month", as_index=False).agg(
        count=("GLOBALEVENTID", "count"),
        avg_tone=("AvgTone", "mean"),
        avg_gold=("GoldsteinScale", "mean")
    ).sort_values("month")
    if not monthly.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(monthly, x="month", y="count", title="Volume mensuel", color="count", color_continuous_scale="Viridis")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.line(monthly, x="month", y=["avg_tone", "avg_gold"], markers=True, title="Tonalité et Stabilité")
            st.plotly_chart(fig, use_container_width=True)

    # Export PDF (bouton dans l'onglet)
    st.markdown("---")
    if st.button("📄 Exporter le rapport (HTML/PDF)", key="export_btn"):
        with st.spinner("Génération du rapport..."):
            kpi_data = {
                "volume": f"{len(df_view):,}",
                "avg_tone": f"{safe_mean(df_view['AvgTone']):.2f}",
                "avg_gold": f"{safe_mean(df_view['GoldsteinScale']):.2f}",
                "attract_score": f"{attract_score:.1f}"
            }
            risk_df = compute_risk_score(df_view)
            html_report = export_to_html(df_view, kpi_data, risk_df)
            b64 = base64.b64encode(html_report.encode()).decode()
            href = f'<a href="data:text/html;base64,{b64}" download="rapport_attractivite_benin.html">Télécharger le rapport HTML (imprimable en PDF)</a>'
            st.markdown(href, unsafe_allow_html=True)

    st.markdown("<div class='section-title'>Top 10 thématiques</div>", unsafe_allow_html=True)
    top_themes = df_view["event_root"].value_counts().reset_index().head(10)
    top_themes.columns = ["Thématique", "Volume"]
    fig = px.bar(top_themes, x="Volume", y="Thématique", orientation="h", color="Volume", color_continuous_scale="Blues")
    st.plotly_chart(fig, use_container_width=True)

        # Top partenaires internationaux
    st.markdown("<div class='section-title'>🌍 Top partenaires internationaux</div>", unsafe_allow_html=True)
    relations = get_country_relations(df_view, "Benin")
    if not relations.empty:
        # Ajouter la stabilité moyenne (Goldstein) pour chaque partenaire
        def get_avg_gold(pays):
            mask = ((df_view["actor1_country"] == pays) & (df_view["actor2_country"].str.lower() == "benin")) | \
                   ((df_view["actor2_country"] == pays) & (df_view["actor1_country"].str.lower() == "benin"))
            return df_view[mask]["GoldsteinScale"].mean()
        relations["stabilite"] = relations["pays"].apply(get_avg_gold)
        top10 = relations.head(10).copy()
        
        # Graphique à barres avec tonalité en couleur
        fig = px.bar(top10, x="pays", y="volume", color="tonalite",
                     color_continuous_scale="RdYlGn", title="Top 10 partenaires (volume et tonalité)",
                     labels={"pays": "Pays partenaire", "volume": "Volume d'événements", "tonalite": "Tonalité moyenne"})
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Court commentaire
        top_positive = top10[top10["tonalite"] > 0].iloc[0]["pays"] if (top10["tonalite"] > 0).any() else None
        if top_positive:
            st.caption(f"💡 **Point d'attractivité** : {top_positive} affiche la meilleure tonalité parmi les partenaires majeurs.")
    else:
        st.info("Aucun partenaire international détecté dans les filtres actuels.")

# ------------------ ONGLET ARTICLES & SOURCES ------------------
with tab_articles:
    st.markdown("<div class='section-title'>Tableau interactif des articles</div>", unsafe_allow_html=True)
    render_articles_table(df_view)
    
    st.markdown("<div class='section-title'>Word Cloud par type de source</div>", unsafe_allow_html=True)
    col_wc1, col_wc2 = st.columns(2)
    with col_wc1:
        national_df = df_view[df_view["source_type"] == "Nationale"]
        if not national_df.empty:
            fig_wc = generate_wordcloud(national_df, text_column="event_root", title="Sources nationales")
            st.pyplot(fig_wc)
        else:
            st.info("Aucune source nationale détectée")
    with col_wc2:
        international_df = df_view[df_view["source_type"] == "Internationale"]
        if not international_df.empty:
            fig_wc = generate_wordcloud(international_df, text_column="event_root", title="Sources internationales")
            st.pyplot(fig_wc)
        else:
            st.info("Aucune source internationale détectée")
    
    st.markdown("<div class='section-title'>Répartition par type de source</div>", unsafe_allow_html=True)
    source_counts = df_view["source_type"].value_counts().reset_index()
    source_counts.columns = ["Type", "Nombre"]
    fig = px.pie(source_counts, names="Type", values="Nombre", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

# ------------------ ONGLET ANALYSE AVANCÉE ------------------
with tab_analysis:
    st.markdown("<div class='section-title'>📉 Score de risque pays mensuel</div>", unsafe_allow_html=True)
    risk_df = compute_risk_score(df_view)
    if not risk_df.empty:
        fig = px.line(risk_df, x="month", y="risk_score", markers=True, title="Risque territorial (0=faible, 100=élevé)", color_discrete_sequence=["#d32f2f"])
        fig.update_layout(yaxis_range=[0,100])
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Indice combinant : tonalité négative (40%), goldstein négatif (30%) et volume de conflits (30%).")
    
    # Cartographie des relations internationales
    st.markdown("<div class='section-title'>🗺️ Relations internationales du Bénin</div>", unsafe_allow_html=True)
    relations = get_country_relations(df_view, "Benin")
    if not relations.empty:
        # Carte choroplèthe (ou scattergeo)
        fig = px.choropleth(
            relations,
            locations="pays",
            locationmode="country names",
            color="volume",
            hover_name="pays",
            hover_data={"tonalite": ":.2f"},
            color_continuous_scale="Teal",
            title="Pays partenaires du Bénin (volume d'événements)"
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau des partenaires
        st.dataframe(relations, use_container_width=True)
    else:
        st.info("Aucune relation internationale détectée dans les filtres actuels.")

        # Classification des partenaires (type d'acteur secondaire)
    st.markdown("<div class='section-title'>🏷️ Classification des partenaires (type d'acteur)</div>", unsafe_allow_html=True)
    if "actor2_type_label" in df_view.columns:
        # On filtre les événements où le second acteur n'est pas le Bénin et a un type connu
        mask_partner = (df_view["actor2_country"] != "Inconnu") & (df_view["actor2_country"].str.lower() != "benin")
        partner_types = df_view[mask_partner]["actor2_type_label"].value_counts().reset_index()
        partner_types.columns = ["Type d'acteur", "Nombre d'événements"]
        if not partner_types.empty:
            fig = px.bar(partner_types, x="Type d'acteur", y="Nombre d'événements", title="Types d'acteurs interagissant avec le Bénin", color="Nombre d'événements")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée de type d'acteur disponible.")
    else:
        st.info("Colonne 'actor2_type_label' manquante – classification non disponible.")

    # Classification avancée des partenaires (ACP + clustering)
    st.markdown("<div class='section-title'>🏷️ Classification des partenaires (ACP + Clustering)</div>", unsafe_allow_html=True)
    relations = get_country_relations(df_view, "Benin")
    if not relations.empty and len(relations) >= 3:
        # Ajouter la moyenne de GoldsteinScale pour chaque partenaire
        def get_avg_gold(pays):
            mask = ((df_view["actor1_country"] == pays) & (df_view["actor2_country"].str.lower() == "benin")) | \
                   ((df_view["actor2_country"] == pays) & (df_view["actor1_country"].str.lower() == "benin"))
            return df_view[mask]["GoldsteinScale"].mean()
        relations["avg_gold"] = relations["pays"].apply(get_avg_gold)
        relations_clustered, fig_pca, _ = cluster_partners(relations)
        if fig_pca:
            st.plotly_chart(fig_pca, use_container_width=True)
            st.dataframe(relations_clustered[['pays', 'volume', 'tonalite', 'avg_gold', 'cluster_label']], use_container_width=True)
            st.markdown("""
            **Interprétation des groupes :**
            - 🟢 **Partenaires positifs** : tonalité moyenne positive, volume d'échanges élevé → favorables à l'attractivité.
            - 🔴 **Partenaires sensibles** : tonalité négative, à surveiller.
            *(D’autres clusters peuvent apparaître selon les données)*
            """)
        else:
            st.info("Nombre insuffisant de partenaires pour une classification robuste.")
    else:
        st.info("Données insuffisantes pour la classification des partenaires (minimum 3 pays requis).")

        # Anomalies avec liens vers les articles et export CSV
    st.markdown("<div class='section-title'>🔍 Alertes & Anomalies (avec articles et export)</div>", unsafe_allow_html=True)
    anomalies = detect_anomalies(df_view)
    if not anomalies.empty:
        for idx, row in anomalies.iterrows():
            st.markdown(f'<div class="anomaly-highlight">📅 **{row["date"]}** – {row["métrique"]} = {row["valeur"]:.2f} (norme: entre {row["seuil_inf"]:.2f} et {row["seuil_sup"]:.2f})</div>', unsafe_allow_html=True)
            articles = get_articles_for_anomaly(df_view, row["date"], row["métrique"])
            if not articles.empty:
                st.markdown("**Articles liés à cette anomalie :**")
                for _, art in articles.iterrows():
                    url = art["SOURCEURL"]
                    if pd.notna(url) and url.startswith("http"):
                        st.markdown(f"- [{art['event_root']} - Tonalité {art['AvgTone']:.2f}]({url})")
                    else:
                        st.markdown(f"- {art['event_root']} (lien non disponible)")
                # Bouton de téléchargement CSV
                csv_link = download_csv(articles, f"anomalie_{row['date']}_{row['métrique']}.csv")
                st.markdown(csv_link, unsafe_allow_html=True)
                st.markdown("---")
            else:
                st.markdown("*Aucun article détaillé disponible pour cette anomalie.*")
                st.markdown("---")
    else:
        st.success("Aucune anomalie détectée sur la période.")

    st.markdown("<div class='section-title'>🌍 Comparaison avec pays voisins</div>", unsafe_allow_html=True)
    st.info("Pour comparer le Bénin avec le Togo, Ghana, Côte d'Ivoire, Nigeria, veuillez charger un fichier CSV contenant les mêmes colonnes pour ces pays.")
    uploaded = st.file_uploader("Charger données voisins (CSV)", type="csv")
    if uploaded is not None:
        df_neighbors = pd.read_csv(uploaded)
        st.success("Données chargées – affichage des scores synthétiques")
        # Ici on pourrait calculer un score similaire
        st.dataframe(df_neighbors.head())
    
    st.markdown("<div class='section-title'>📰 Résumé IA hebdomadaire</div>", unsafe_allow_html=True)
    insight = generate_weekly_insight(df_view, last_n_days=7)
    st.markdown(insight)

# ------------------ ONGLET RECOMMANDATIONS ------------------
with tab_recommendations:
    st.markdown("<div class='section-title'>Mode Décideur</div>", unsafe_allow_html=True)
    profile = st.selectbox("Choisissez votre profil", ["Investisseur", "Diplomate", "Décideur local"])
    # Calcul d'un score de risque global (moyenne mensuelle)
    risk_global = risk_df["risk_score"].mean() if not risk_df.empty else 50
    recommendation = recommendations_for_profile(profile, attract_score, risk_global, avg_tone, avg_gold)
    st.markdown(f'<div class="story-block">{recommendation}</div>', unsafe_allow_html=True)
    
    st.markdown("### Tableau de bord personnalisé")
    st.metric("Score attractivité Bénin", f"{attract_score:.1f}/100", delta="+2" if attract_score > 50 else "-1")
    st.metric("Niveau de risque", f"{risk_global:.1f}/100", delta="Élevé" if risk_global > 60 else "Modéré")
    
    st.markdown("### Actions suggérées")
    if profile == "Investisseur":
        st.write("- Privilégier les secteurs avec une tonalité positive (ex: coopération économique).")
        st.write("- Utiliser le dashboard pour identifier les partenaires les plus stables.")
    elif profile == "Diplomate":
        st.write("- Intensifier les campagnes de communication sur les réussites du Bénin.")
        st.write("- Organiser des sommets avec les pays ayant une couverture favorable.")
    else:
        st.write("- Lancer une veille quotidienne sur les anomalies détectées.")
        st.write("- Renforcer la communication autour des actions de stabilisation.")

# Pied de page
st.markdown(
    "<div class='note'>Source : GDELT Event Database – enrichi par l'Observatoire. Dernière mise à jour : {}</div>".format(pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")),
    unsafe_allow_html=True,
)