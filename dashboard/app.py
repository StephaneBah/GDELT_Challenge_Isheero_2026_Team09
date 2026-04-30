"""Bénin Risk Map — dashboard Streamlit.

Architecture en 3 onglets (cf. doctrine) :
1. Tableau de bord — vue exécutive (5 chiffres + carte simplifiée + top stories)
2. Explorer — exploration libre (filtres complets, tableau, carte zoomable)
3. Méthodologie — pipeline, requêtes, limites, validations

Lancement local : streamlit run dashboard/app.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import DOMAINS, PROCESSED_DIR

st.set_page_config(
    page_title="Bénin Risk Map",
    page_icon=":world_map:",
    layout="wide",
)


@st.cache_data(show_spinner="Chargement des données...")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge events enrichis et stories depuis data/processed/."""
    events_path = PROCESSED_DIR / "events_enriched.parquet"
    stories_path = PROCESSED_DIR / "stories.parquet"
    if not events_path.exists() or not stories_path.exists():
        st.error(
            "Données manquantes. Lancer d'abord :\n"
            "```\npython -m src.pipeline.extract\npython -m src.pipeline.clean\n"
            "python -m src.pipeline.enrich\npython -m src.pipeline.stories\n```"
        )
        st.stop()
    events = pd.read_parquet(events_path)
    stories = pd.read_parquet(stories_path)
    return events, stories


def sidebar_filters(events: pd.DataFrame) -> dict:
    """Filtres globaux dans la sidebar — partagés par les 3 onglets."""
    st.sidebar.title("Filtres")

    confidence = st.sidebar.radio(
        "Confiance",
        options=["strict", "large"],
        index=1,
        help="Strict : ≥3 sources et géoloc renseignée. Large : tout.",
    )

    countries = st.sidebar.multiselect(
        "Pays",
        options=sorted(events["ActionGeo_CountryCode"].dropna().unique()),
        default=["BC"],
    )

    domains = st.sidebar.multiselect(
        "Domaines de risque",
        options=list(DOMAINS),
        default=list(DOMAINS),
    )

    date_min = events["SQLDATE"].min().date()
    date_max = events["SQLDATE"].max().date()
    date_range = st.sidebar.date_input(
        "Période",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
    )

    return {
        "confidence": confidence,
        "countries": countries,
        "domains": domains,
        "date_range": date_range,
    }


def apply_filters(events: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Applique les filtres sidebar."""
    df = events.copy()
    if filters["confidence"] == "strict":
        df = df[df["confidence_tier"] == "strict"]
    if filters["countries"]:
        df = df[df["ActionGeo_CountryCode"].isin(filters["countries"])]
    if filters["domains"]:
        df = df[df["risk_domain"].isin(filters["domains"])]
    if len(filters["date_range"]) == 2:
        d0, d1 = filters["date_range"]
        df = df[(df["SQLDATE"].dt.date >= d0) & (df["SQLDATE"].dt.date <= d1)]
    return df


def main() -> None:
    st.title("Bénin Risk Map")
    st.caption(
        "Cartographie départementale du risque opérationnel à partir de 12 mois "
        "de signaux GDELT — Équipe Team09 · Hackathon iSHEERO 2026"
    )

    events, stories = load_data()
    filters = sidebar_filters(events)
    filtered = apply_filters(events, filters)

    tab1, tab2, tab3 = st.tabs(
        ["Tableau de bord", "Explorer", "Méthodologie"]
    )

    with tab1:
        st.subheader("Vue exécutive")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Events filtrés", f"{len(filtered):,}")
        col2.metric("Stories", f"{len(stories):,}")
        col3.metric(
            "Ton moyen", f"{filtered['AvgTone'].mean():.2f}"
        ) if len(filtered) else col3.metric("Ton moyen", "—")
        col4.metric("Mentions", f"{int(filtered['NumMentions'].sum()):,}")
        col5.metric("Pays", len(filtered['ActionGeo_CountryCode'].unique()))

        st.info(
            "🚧 Visualisations à compléter par le Data Analyst : "
            "carte choroplèthe par département, top stories du mois, "
            "courbe de ton 12 mois."
        )

    with tab2:
        st.subheader("Exploration des stories")
        st.dataframe(stories.head(100), use_container_width=True)
        st.info("🚧 À compléter : filtres avancés, carte zoomable, profils d'acteurs.")

    with tab3:
        st.subheader("Méthodologie et limites")
        st.markdown(
            """
            - **Source** : GDELT v2 (BigQuery), fenêtre 12 mois, 3 pays (Bénin, Burkina, Niger).
            - **Doctrine** : story-as-unit, confidence-as-slider, domains-not-codes, admin1-first.
            - **Validations croisées** : ACLED + GDELT Cloud (free tier).
            - **Limites GDELT** documentées : géocodage imprécis, sur-comptage, biais anglophone, AvgTone grossier.

            👉 Voir [docs/01_doctrine.md](../docs/01_doctrine.md), [docs/05_limitations.md](../docs/05_limitations.md).
            """
        )


if __name__ == "__main__":
    main()
