"""Bénin Insights — dashboard Streamlit.

Architecture en 3 onglets (cf. doctrine) :
1. Tableau de bord — résultats des questions Q1, Q2, Q3 (vue exécutive)
2. Explorer — exploration libre des stories (filtres complets, table)
3. Méthodologie — doctrine, manifest, limites

Le dashboard consomme directement les modules `src.questions.*` via le
manifest `questions.yaml`. Aucun calcul de viz n'est réalisé ici : tout
vient des `Result` produits par les orchestrateurs de questions.

Lancement local : streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from datetime import date as dtdate
from pathlib import Path

# Permettre l'import depuis src/ quand Streamlit lance ce fichier
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import yaml

from src.config import DOMAINS, PROCESSED_DIR, PROJECT_ROOT
from src.questions.base import Filters, Result

st.set_page_config(
    page_title="Bénin Insights",
    page_icon="🗺️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Chargement des données et du manifest
# ---------------------------------------------------------------------------

def _parquet_mtime() -> float:
    """Renvoie le mtime du parquet enrichi — sert de clé de cache."""
    p = PROCESSED_DIR / "events_enriched.parquet"
    return p.stat().st_mtime if p.exists() else 0.0


@st.cache_data(show_spinner="Chargement des données...")
def load_events_and_stories(mtime: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge events enrichis et stories. Stoppe l'app avec message si absent.

    Le paramètre `mtime` (float, hashable) est inclus dans la clé de cache
    Streamlit : quand le parquet est régénéré, mtime change et le cache est
    automatiquement invalidé.
    """
    events_path = PROCESSED_DIR / "events_enriched.parquet"
    stories_path = PROCESSED_DIR / "stories.parquet"
    if not events_path.exists() or not stories_path.exists():
        st.error(
            "**Données manquantes.** Lancer le pipeline avant d'utiliser le dashboard :\n\n"
            "```bash\n"
            "make extract     # snapshot 12 mois (BigQuery)\n"
            "make process     # nettoyage + enrichissement + stories\n"
            "```"
        )
        st.stop()
    events = pd.read_parquet(events_path)
    stories = pd.read_parquet(stories_path)
    return events, stories


@st.cache_data(show_spinner=False)
def _run_question_cached(
    module_name: str,
    mtime: float,
    filters_key: str,
    filters: Filters,
) -> Result:
    """Wrapper mis en cache autour de QUESTION.run().

    `mtime` invalide le cache quand le parquet est régénéré.
    `filters_key` invalide le cache quand les filtres changent.
    """
    import importlib

    module = importlib.import_module(module_name)
    return module.QUESTION.run(filters)


@st.cache_data
def load_manifest() -> dict:
    """Charge le manifest YAML des questions."""
    path = PROJECT_ROOT / "questions.yaml"
    if not path.exists():
        return {"questions": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"questions": []}


# ---------------------------------------------------------------------------
# Sidebar : filtres globaux
# ---------------------------------------------------------------------------

def sidebar_filters(events: pd.DataFrame) -> Filters:
    """Construit un objet `Filters` à partir des choix utilisateur."""
    st.sidebar.title("Filtres")
    st.sidebar.caption("Bénin · Burkina Faso · Niger — 2025")

    if st.sidebar.button("Actualiser les données", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")

    confidence = st.sidebar.radio(
        "Niveau de confiance",
        options=["all", "strict", "large"],
        index=0,
        help=(
            "**Strict** : events avec ≥3 sources et géolocalisation renseignée.\n\n"
            "**Large** : events avec au moins 1 source.\n\n"
            "**All** : aucun filtre de qualité (volume maximal)."
        ),
    )

    domains = st.sidebar.multiselect(
        "Domaines de risque",
        options=list(DOMAINS),
        default=[],
        help=(
            "Filtre par domaine thématique CAMEO.\n\n"
            "Vide = tous les domaines.\n\n"
            "**Q1 analyse toujours le domaine sécuritaire**, "
            "indépendamment de ce filtre."
        ),
    )

    date_min = events["SQLDATE"].min().date()
    date_max = events["SQLDATE"].max().date()
    date_range = st.sidebar.date_input(
        "Période",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        d_from, d_to = date_range
    else:
        d_from, d_to = date_min, date_max

    return Filters(
        date_from=d_from,
        date_to=d_to,
        countries=("BN",),  # Q1 étend à BN/UV/NG en interne ; Q2/Q3 restent centrés Bénin
        risk_domains=tuple(domains),
        confidence=confidence,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Onglet 1 — Tableau de bord (résultats des questions)
# ---------------------------------------------------------------------------

def render_question_section(question_meta: dict, filters: Filters, mtime: float) -> None:
    """Importe et exécute une question puis affiche son `Result`."""
    qid = question_meta.get("id", "?")
    title = question_meta.get("public_title") or question_meta.get("title", qid)
    module_name = question_meta.get("module", f"src.questions.{qid.lower()}")

    st.markdown(f"### {qid} — {title}")
    st.caption(question_meta.get("summary", ""))

    try:
        with st.spinner(f"Calcul de {qid}..."):
            result = _run_question_cached(
                module_name=module_name,
                mtime=mtime,
                filters_key=filters.describe(),
                filters=filters,
            )
    except ImportError as e:
        st.warning(f"Module `{module_name}` introuvable : {e}")
        return
    except AttributeError as e:
        st.warning(f"Le module `{module_name}` n'expose pas de variable `QUESTION` : {e}")
        return
    except FileNotFoundError as e:
        st.error(str(e))
        return
    except Exception as e:  # noqa: BLE001
        st.error(f"Erreur lors de l'exécution de {qid} : {e}")
        return

    # Métriques en KPIs (clés préfixées "_" = usage interne, exclues de l'affichage)
    if result.metrics:
        scalar_metrics = {
            k: v for k, v in result.metrics.items()
            if isinstance(v, (int, float, str))
            and not isinstance(v, bool)
            and not k.startswith("_")
        }
        if scalar_metrics:
            cols = st.columns(min(len(scalar_metrics), 5))
            for col, (k, v) in zip(cols, list(scalar_metrics.items())[:5]):
                col.metric(k, v)

    # Insight narratif
    if result.insight_text:
        st.info(result.insight_text)

    # Figures
    for fig_name, fig in result.figures.items():
        st.plotly_chart(fig, use_container_width=True)

    # Tables (en expander pour ne pas surcharger)
    if result.tables:
        with st.expander(f"Tables détaillées ({len(result.tables)})"):
            for table_name, df in result.tables.items():
                st.markdown(f"**{table_name}** — {len(df)} lignes")
                st.dataframe(df.head(50), use_container_width=True)

    st.divider()


def tab_dashboard(manifest: dict, filters: Filters, mtime: float) -> None:
    """Onglet 1 — itère sur les questions du manifest et rend chacune."""
    st.subheader("Vue exécutive — résultats des questions de recherche")
    st.caption(f"Filtres actifs : {filters.describe()}")

    questions = manifest.get("questions", [])
    if not questions:
        st.info("Aucune question dans le manifest. Compléter `questions.yaml`.")
        return

    qids = [q.get("id", "?") for q in questions]
    selected = st.radio(
        "Question à afficher",
        options=qids + ["Toutes"],
        horizontal=True,
        index=len(qids),  # par défaut : Toutes
    )

    for q in questions:
        if selected != "Toutes" and q.get("id") != selected:
            continue
        render_question_section(q, filters, mtime)


# ---------------------------------------------------------------------------
# Onglet 2 — Explorer
# ---------------------------------------------------------------------------

def tab_explorer(events: pd.DataFrame, stories: pd.DataFrame, filters: Filters) -> None:
    st.subheader("Exploration libre")
    st.caption(f"Filtres actifs : {filters.describe()}")

    # Application manuelle des filtres (sans passer par les questions)
    df = events
    if filters.confidence != "all":
        df = df[df["confidence_tier"] == filters.confidence]
    if filters.countries:
        df = df[df["ActionGeo_CountryCode"].isin(filters.countries)]
    if filters.risk_domains:
        df = df[df["risk_domain"].isin(filters.risk_domains)]
    if filters.date_from and filters.date_to:
        df = df[
            (df["SQLDATE"].dt.date >= filters.date_from)
            & (df["SQLDATE"].dt.date <= filters.date_to)
        ]

    col1, col2, col3 = st.columns(3)
    col1.metric("Events filtrés", f"{len(df):,}")
    col2.metric("Stories totales", f"{len(stories):,}")
    col3.metric(
        "Ton moyen",
        f"{df['AvgTone'].mean():.2f}" if len(df) else "—",
    )

    st.markdown("#### Top stories par mentions")
    if not stories.empty:
        st.dataframe(
            stories.sort_values("n_mentions", ascending=False).head(50),
            use_container_width=True,
        )
    else:
        st.info("Aucune story chargée.")

    st.markdown("#### Events filtrés (échantillon 100 lignes)")
    st.dataframe(df.head(100), use_container_width=True)


# ---------------------------------------------------------------------------
# Onglet 3 — Méthodologie
# ---------------------------------------------------------------------------

def tab_methodology(manifest: dict) -> None:
    st.subheader("Méthodologie")

    st.warning(
        "**Note méthodologique importante — biais Benin City**\n\n"
        "GDELT confond fréquemment « Benin » (le pays) avec **Benin City** "
        "(capitale de l'Edo State, Nigeria). Ce biais introduit un volume important "
        "d'articles nigérians sans rapport avec le Bénin.\n\n"
        "**Notre solution :** un pipeline de nettoyage en deux filtres "
        "(voir `notebooks/GDELT_Benin_Nettoyage.ipynb`) réduit le dataset de "
        "**34 106 à 22 026 événements** avec un bruit résiduel estimé à **< 0,3 %**. "
        "Ce nettoyage est entièrement reproductible et documenté pas à pas.\n\n"
        "La couverture reflète un regard majoritairement extérieur sur le Bénin, "
        "dominé par les médias africains régionaux.",
        icon="⚠️",
    )

    st.markdown(
        """
        ### Source de données
        - **GDELT v2** (BigQuery) — fenêtre **année calendaire 2025**, 3 pays (Bénin, Burkina Faso, Niger).
        - Filtre `_PARTITIONTIME` strict pour préserver le quota mensuel BigQuery.

        ### Doctrine d'analyse — 4 principes
        1. **Story-as-unit** — clusters d'articles, pas events bruts.
        2. **Confidence as slider** — strict (≥3 sources + géoloc) vs large.
        3. **Domains, not codes** — agrégation CAMEO en 5-7 domaines de risque lisibles.
        4. **Admin1-first** — maille départementale (12 départements béninois).

        ### Validations croisées
        - **ACLED** sur les events sécuritaires au nord du Bénin.
        - **GDELT Cloud** (free tier) — Conflict Events à méthodologie ACLED + entity profiles.

        ### Limites GDELT documentées
        | Limite | Traitement |
        |---|---|
        | **Confusion Benin / Benin City Nigeria** | Pipeline de nettoyage 2 filtres — 34 106 → 22 026 events, bruit < 0,3 % |
        | Géocodage infranational imprécis (Hammond & Weidmann 2014) | Audit sur échantillon, fallback ADM1 |
        | Sur-comptage d'events | Pondération `NumMentions`, clustering stories |
        | Biais anglophone du crawl | Mention explicite, validation croisée multilingue |
        | `AvgTone` grossier (dictionnaire GCAM) | Validation xlm-roberta sur sous-échantillon |
        | Codes acteurs bruyants | Filtre `Actor1Type1Code` ∈ {GOV, MIL, IGO, NGO} |

        ### Architecture du code
        Quatre couches en cascade : `pipeline` → `analytics` / `ml` / `viz` → `questions` → consommateurs.
        Les détails sont dans [`docs/04_architecture.md`](https://github.com/StephaneBah/GDELT_Challenge_Isheero_2026_Team09).
        """
    )

    st.markdown("### Manifest des questions")
    questions = manifest.get("questions", [])
    if questions:
        meta_df = pd.DataFrame(
            [
                {
                    "ID": q.get("id"),
                    "Titre public": q.get("public_title") or q.get("title"),
                    "Owner": q.get("owner"),
                    "Status": q.get("status"),
                    "Module": q.get("module"),
                }
                for q in questions
            ]
        )
        st.dataframe(meta_df, use_container_width=True)
    else:
        st.info("Manifest vide.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("Bénin Insights")
    st.caption(
        "Analyse des signaux médiatiques mondiaux GDELT sur le Bénin (2025) — "
        "Sécurité · Ton · Réseau · Attractivité — Équipe Team09 · "
        "Hackathon iSHEERO × DataCamp 2026"
    )

    mtime = _parquet_mtime()
    events, stories = load_events_and_stories(mtime)
    manifest = load_manifest()
    filters = sidebar_filters(events)

    tab1, tab2, tab3 = st.tabs(["Tableau de bord", "Explorer", "Méthodologie"])

    with tab1:
        tab_dashboard(manifest, filters, mtime)
    with tab2:
        tab_explorer(events, stories, filters)
    with tab3:
        tab_methodology(manifest)


if __name__ == "__main__":
    main()
