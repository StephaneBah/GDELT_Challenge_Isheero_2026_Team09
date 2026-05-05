"""Q3 — Le réseau : recomposition diplomatique observable.

Compose `analytics.{aggregate, network_ops}` et `viz.network` pour :
- construire le graphe d'acteurs apparaissant aux côtés du Bénin,
- comparer la structure pré et post juillet 2023 (rupture CEDEAO/AES),
- détecter les communautés (Louvain) et identifier les recompositions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd

from src.analytics import aggregate, network_ops
from src.config import FIPS_BENIN, PROCESSED_DIR
from src.questions.base import Filters, Result
from src.viz import network as viz_network

logger = logging.getLogger(__name__)

# Date pivot — coup d'État au Niger, accélérateur de la rupture CEDEAO/AES
PIVOT_DATE = pd.Timestamp(date(2023, 7, 26))


@dataclass
class _Q3:
    id: str = "Q3"
    title: str = "Le réseau — recomposition diplomatique observable"

    def _load_events(self) -> pd.DataFrame:
        path = PROCESSED_DIR / "events_enriched.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} introuvable. Lancer `make extract && make process`."
            )
        return pd.read_parquet(path)

    def _filter_to_benin_actors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Garde uniquement les events où le Bénin est acteur, géographiquement ou nominalement."""
        from src.config import CAMEO_BENIN

        mask = (
            (df["ActionGeo_CountryCode"] == FIPS_BENIN)
            | (df["Actor1CountryCode"] == CAMEO_BENIN)
            | (df["Actor2CountryCode"] == CAMEO_BENIN)
        )
        return df[mask]

    def _apply_filters(self, df: pd.DataFrame, filters: Filters) -> pd.DataFrame:
        df = aggregate.filter_period(df, date_from=filters.date_from, date_to=filters.date_to)
        df = aggregate.confidence_filter(df, tier=filters.confidence)
        # Q3 ne filtre pas sur les pays ni sur les domaines : on veut tout le contexte d'acteurs
        return df

    def run(self, filters: Filters) -> Result:
        events_all = self._apply_filters(self._load_events(), filters)
        events = self._filter_to_benin_actors(events_all)
        if events.empty:
            return Result(
                question_id=self.id,
                title=self.title,
                metrics={"n_events": 0},
                insight_text="Aucun event impliquant le Bénin ne correspond aux filtres.",
                metadata={"filters": filters.describe()},
            )

        # 1. Graphe global (toute la période)
        g_global = network_ops.build_actor_graph(events)
        partition_global = network_ops.detect_communities(g_global) if g_global.number_of_nodes() else {}

        # 2. Comparaison pré / post juillet 2023
        pre = events[events["SQLDATE"] < PIVOT_DATE]
        post = events[events["SQLDATE"] >= PIVOT_DATE]
        g_pre = network_ops.build_actor_graph(pre) if not pre.empty else None
        g_post = network_ops.build_actor_graph(post) if not post.empty else None

        # Variation de degré pour chaque acteur
        if g_pre is not None and g_post is not None:
            variation = network_ops.degree_variation(g_pre, g_post)
        else:
            variation = pd.DataFrame(columns=["node", "degree_pre", "degree_post", "delta", "delta_pct"])

        # 3. Top co-occurrences brutes
        co = aggregate.co_occurrence(
            events,
            col_a="Actor1Code",
            col_b="Actor2Code",
            weight_col="NumMentions",
        ).head(20)

        # 4. Figures
        figures = {}
        if g_global.number_of_nodes() > 0:
            # Limiter à top-30 pour la lisibilité
            top_nodes = sorted(
                g_global.nodes,
                key=lambda n: sum(d.get("weight", 0) for _, _, d in g_global.edges(n, data=True)),
                reverse=True,
            )[:30]
            g_top = g_global.subgraph(top_nodes).copy()
            sub_partition = {n: partition_global.get(n, 0) for n in top_nodes}
            figures["network_global"] = viz_network.force_layout_graph(
                g_top,
                partition=sub_partition,
                title="Q3 — Réseau d'acteurs Bénin (top 30, communautés Louvain)",
            )

        # 5. Métriques
        winners = variation.head(5)[["node", "delta", "delta_pct"]] if not variation.empty else pd.DataFrame()
        losers = (
            variation.sort_values("delta").head(5)[["node", "delta", "delta_pct"]]
            if not variation.empty
            else pd.DataFrame()
        )

        metrics = {
            "n_events_benin_centred": len(events),
            "n_actors": g_global.number_of_nodes(),
            "n_edges": g_global.number_of_edges(),
            "n_communities": len(set(partition_global.values())) if partition_global else 0,
            "top_co_occurrences": co.head(5).to_dict(orient="records"),
            "winners_post_2023": winners.to_dict(orient="records"),
            "losers_post_2023": losers.to_dict(orient="records"),
        }

        # 6. Insight narratif
        winner_label = winners.iloc[0]["node"] if not winners.empty else "n/a"
        loser_label = losers.iloc[0]["node"] if not losers.empty else "n/a"
        insight = (
            f"Le réseau diplomatique observable du Bénin compte {metrics['n_actors']} "
            f"acteurs distincts répartis en {metrics['n_communities']} communautés. "
            f"Plus grand gagnant post-juillet 2023 : {winner_label}. "
            f"Plus grand perdant : {loser_label}. La table `degree_variation` "
            "détaille la recomposition complète."
        )

        return Result(
            question_id=self.id,
            title=self.title,
            metrics=metrics,
            tables={
                "co_occurrences": co,
                "degree_variation": variation,
            },
            figures=figures,
            insight_text=insight,
            metadata={
                "filters": filters.describe(),
                "pivot_date": PIVOT_DATE.strftime("%Y-%m-%d"),
                "n_events_pre": len(pre),
                "n_events_post": len(post),
            },
        )


QUESTION = _Q3()
