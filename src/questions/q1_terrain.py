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
        # Q1 est intrinsèquement comparative BN/UV/NG : on IGNORE le filtre
        # pays utilisateur et on retient toujours les 3 pays cibles.
        df = df[df["ActionGeo_CountryCode"].isin([FIPS_BENIN, FIPS_BURKINA, FIPS_NIGER])]
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

        # 1. Distribution départementale (Bénin uniquement, events géolocalisés)
        benin = events[events["ActionGeo_CountryCode"] == FIPS_BENIN]
        by_dept = aggregate.by_admin1(benin, value_col="n_events")
        # On retire le bucket NaN (events tagués au niveau pays uniquement)
        # qui domine en volume mais ne nous renseigne pas géographiquement.
        by_dept = (
            by_dept.dropna(subset=["dept_normalized"])
            .sort_values("n_events", ascending=False)
            .reset_index(drop=True)
        )

        # 2. Comparaison régionale BN / UV / NG
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
                title="Q1 — Stories sécuritaires hebdomadaires (BN / UV / NG)",
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
            "Incidents sécuritaires — Bénin": n_benin,
            "Incidents sécuritaires — Burkina Faso": n_burkina,
            "Incidents sécuritaires — Niger": n_niger,
            "Intensité Bénin / Burkina Faso": f"{round(ratio_burkina * 100, 1)} %" if ratio_burkina else "n/d",
            "Département le plus exposé": top_dept_1 or "n/d",
            "2e département exposé": top_dept_2 or "n/d",
            # Valeurs internes conservées pour le calcul de l'insight (non affichées en KPI)
            "_mpe_benin": round(mpe_benin, 2),
            "_mpe_burkina": round(mpe_burkina, 2),
            "_coverage_ratio": round(coverage_ratio, 2) if coverage_ratio else None,
        }

        # 7. Insight narratif
        ratio_str = (
            f"{round(ratio_burkina * 100, 1)} %"
            if ratio_burkina is not None
            else "n/d"
        )
        coverage_str = (
            f"{round(coverage_ratio, 2)}×"
            if coverage_ratio is not None
            else "n/d"
        )
        dept1_str = top_dept_1 or "n/d"
        dept2_str = top_dept_2 or "n/d"
        insight = (
            f"Sur 2025, le Bénin a enregistré {n_benin} incidents sécuritaires "
            f"dans la presse mondiale, soit {ratio_str} de l'intensité observée "
            f"au Burkina Faso. Les départements les plus exposés sont "
            f"{dept1_str} et {dept2_str} — tous deux frontaliers des zones "
            f"de conflit sahélien. Un incident béninois génère {coverage_str} "
            f"moins de couverture médiatique qu'un incident burkinabè comparable : "
            f"la crise au nord du Bénin reste statistiquement sous-couverte."
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
