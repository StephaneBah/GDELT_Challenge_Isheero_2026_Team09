"""Q1 — Le terrain : risque sécuritaire départemental au Bénin.

Compose les primitives de `analytics.aggregate` et `viz.{maps,timeseries}` pour :
- cartographier le risque sécuritaire par département béninois,
- comparer l'intensité Bénin / Burkina / Niger,
- mesurer la sous-couverture médiatique relative.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from src.analytics import aggregate
from src.config import (
    FIPS_BENIN,
    FIPS_BURKINA,
    FIPS_NIGER,
    PROCESSED_DIR,
)
from src.questions.base import Filters, Result
from src.viz import maps, timeseries

logger = logging.getLogger(__name__)

_COUNTRY_LABELS = {FIPS_BENIN: "Bénin", FIPS_BURKINA: "Burkina Faso", FIPS_NIGER: "Niger"}


@dataclass
class _Q1:
    id: str = "Q1"
    title: str = "Le terrain — risque sécuritaire départemental"

    def _load_events(self) -> pd.DataFrame:
        path = PROCESSED_DIR / "events_enriched.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} introuvable. Lancer `make extract && make process`."
            )
        return pd.read_parquet(path)

    def _apply_filters(self, df: pd.DataFrame, filters: Filters) -> pd.DataFrame:
        df = aggregate.filter_period(df, date_from=filters.date_from, date_to=filters.date_to)
        df = aggregate.confidence_filter(df, tier=filters.confidence)
        if filters.countries:
            df = df[df["ActionGeo_CountryCode"].isin(filters.countries)]
        # Q1 est intrinsèquement sécuritaire, sauf si l'utilisateur force d'autres domaines
        domains = filters.risk_domains or ("securitaire",)
        df = aggregate.domain_filter(df, domains)
        return df

    def run(self, filters: Filters) -> Result:
        events = self._apply_filters(self._load_events(), filters)
        if events.empty:
            return Result(
                question_id=self.id,
                title=self.title,
                metrics={"n_events": 0},
                insight_text="Aucun event ne correspond aux filtres appliqués.",
                metadata={"filters": filters.describe()},
            )

        # 1. Distribution départementale (Bénin uniquement)
        benin = events[events["ActionGeo_CountryCode"] == FIPS_BENIN]
        by_dept = aggregate.by_admin1(benin, value_col="n_events")
        by_dept = by_dept.sort_values("n_events", ascending=False)

        # 2. Comparaison régionale BC / UV / NG
        by_country = aggregate.by_country(events, value_col="n_events")
        by_country["country_label"] = by_country["ActionGeo_CountryCode"].map(_COUNTRY_LABELS)

        # 3. Mentions par event — proxy de sous-couverture médiatique
        mentions_by_country = events.groupby("ActionGeo_CountryCode").agg(
            n_events=("GLOBALEVENTID", "count"),
            total_mentions=("NumMentions", "sum"),
        )
        mentions_by_country["mentions_per_event"] = (
            mentions_by_country["total_mentions"] / mentions_by_country["n_events"]
        )

        # 4. Série temporelle hebdomadaire par pays
        ts_by_country = {}
        for code, label in _COUNTRY_LABELS.items():
            sub = events[events["ActionGeo_CountryCode"] == code]
            if not sub.empty:
                ts_by_country[label] = aggregate.time_series(sub, freq="W")

        # 5. Figures
        figures = {
            "choropleth_benin": maps.choropleth_benin(
                by_dept,
                value_col="n_events",
                title="Q1 — Risque sécuritaire par département (Bénin)",
            ),
            "country_comparison": timeseries.multi_line(
                ts_by_country,
                title="Q1 — Stories sécuritaires hebdomadaires (BC / UV / NG)",
                yaxis_title="Stories / semaine",
            ),
        }

        # 6. Métriques scalaires affichables en KPI
        n_benin = int(by_country.loc[
            by_country["ActionGeo_CountryCode"] == FIPS_BENIN, "n_events"
        ].sum())
        n_burkina = int(by_country.loc[
            by_country["ActionGeo_CountryCode"] == FIPS_BURKINA, "n_events"
        ].sum())
        n_niger = int(by_country.loc[
            by_country["ActionGeo_CountryCode"] == FIPS_NIGER, "n_events"
        ].sum())
        ratio_burkina = (n_benin / n_burkina) if n_burkina else None

        top_depts = by_dept.head(2)
        top_dept_1 = top_depts.iloc[0]["dept_normalized"] if not top_depts.empty else None
        top_dept_2 = top_depts.iloc[1]["dept_normalized"] if len(top_depts) > 1 else None

        # Sous-couverture : mentions/event Bénin vs Burkina
        mpe_benin = mentions_by_country.loc[FIPS_BENIN, "mentions_per_event"] if FIPS_BENIN in mentions_by_country.index else 0
        mpe_burkina = mentions_by_country.loc[FIPS_BURKINA, "mentions_per_event"] if FIPS_BURKINA in mentions_by_country.index else 0
        coverage_ratio = (mpe_benin / mpe_burkina) if mpe_burkina else None

        metrics = {
            "n_events_benin": n_benin,
            "n_events_burkina": n_burkina,
            "n_events_niger": n_niger,
            "ratio_benin_vs_burkina_pct": round(ratio_burkina * 100, 1) if ratio_burkina else None,
            "top_dept_1": top_dept_1,
            "top_dept_2": top_dept_2,
            "mentions_per_event_benin": round(mpe_benin, 2),
            "mentions_per_event_burkina": round(mpe_burkina, 2),
            "coverage_ratio_benin_vs_burkina": round(coverage_ratio, 2) if coverage_ratio else None,
        }

        # 7. Insight narratif (template, à raffiner au pitch)
        insight = (
            f"Sur la période, le Bénin a enregistré {n_benin} events sécuritaires, "
            f"soit {metrics['ratio_benin_vs_burkina_pct']}% de l'intensité observée au "
            f"Burkina Faso. Top départements concernés : {top_dept_1} et {top_dept_2}. "
            f"Sous-couverture médiatique mesurée : un event béninois génère "
            f"{metrics['coverage_ratio_benin_vs_burkina']}× moins de mentions qu'un "
            f"event burkinabè comparable."
        )

        return Result(
            question_id=self.id,
            title=self.title,
            metrics=metrics,
            tables={
                "by_dept": by_dept.reset_index(drop=True),
                "by_country": by_country.reset_index(drop=True),
                "mentions_by_country": mentions_by_country.reset_index(),
            },
            figures=figures,
            insight_text=insight,
            metadata={"filters": filters.describe(), "n_events_total": len(events)},
        )


QUESTION = _Q1()
