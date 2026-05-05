"""Q2 — Le ton : évolution médiatique mondiale par domaine de risque.

Compose `analytics.{aggregate, change_points}` et `viz.timeseries` pour :
- tracer le ton lissé du Bénin par domaine de risque,
- détecter les points de bascule (PELT),
- attribuer chaque rupture aux stories dominantes des 7 jours précédents.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from src.analytics import aggregate, change_points
from src.config import DOMAINS, FIPS_BENIN, PROCESSED_DIR
from src.questions.base import Filters, Result
from src.viz import timeseries

logger = logging.getLogger(__name__)


@dataclass
class _Q2:
    id: str = "Q2"
    title: str = "Le ton — évolution par domaine de risque"

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
        countries = filters.countries or (FIPS_BENIN,)
        df = df[df["ActionGeo_CountryCode"].isin(countries)]
        if filters.risk_domains:
            df = aggregate.domain_filter(df, filters.risk_domains)
        return df

    def _top_stories_around(
        self, df: pd.DataFrame, breakpoint: pd.Timestamp, days_before: int = 7, n: int = 3
    ) -> list[dict]:
        """Retourne les top stories des `days_before` jours précédant la rupture."""
        window_start = breakpoint - pd.Timedelta(days=days_before)
        window = df[(df["SQLDATE"] >= window_start) & (df["SQLDATE"] < breakpoint)]
        if window.empty:
            return []
        top = (
            window.sort_values("NumMentions", ascending=False)
            .head(n)[["SQLDATE", "Actor1Name", "Actor2Name", "NumMentions", "AvgTone", "SOURCEURL"]]
        )
        return top.to_dict(orient="records")

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

        figures: dict = {}
        tables: dict = {}
        domains_to_plot = filters.risk_domains or tuple(d for d in DOMAINS if d != "informationnel")

        # Série de ton globale (tous domaines confondus)
        tone_global = change_points.smooth_tone(events, window="7D")
        breakpoints_global = change_points.detect_breakpoints(tone_global, penalty=8.0)
        figures["tone_global"] = timeseries.line_with_breakpoints(
            tone_global,
            breakpoints=breakpoints_global,
            title="Q2 — Ton lissé du Bénin (tous domaines)",
            yaxis_title="AvgTone (lissé 7j, pondéré NumMentions)",
        )

        # Une série par domaine
        series_by_domain: dict[str, pd.Series] = {}
        breakpoints_by_domain: dict[str, list] = {}
        for domain in domains_to_plot:
            sub = events[events["risk_domain"] == domain]
            if len(sub) < 14:
                continue
            ts = change_points.smooth_tone(sub, window="7D")
            series_by_domain[domain] = ts
            breakpoints_by_domain[domain] = change_points.detect_breakpoints(ts, penalty=10.0)

        if series_by_domain:
            figures["tone_by_domain"] = timeseries.multi_line(
                series_by_domain,
                title="Q2 — Ton lissé par domaine de risque",
                yaxis_title="AvgTone (lissé 7j)",
            )

        # Pour chaque rupture globale, identifier les top stories antérieures
        rupture_explanations = []
        for bp in breakpoints_global:
            rupture_explanations.append(
                {
                    "breakpoint": bp.strftime("%Y-%m-%d"),
                    "tone_before": float(tone_global.loc[:bp].tail(7).mean()),
                    "tone_after": float(tone_global.loc[bp:].head(7).mean()),
                    "top_stories": self._top_stories_around(events, bp),
                }
            )
        if rupture_explanations:
            tables["ruptures"] = pd.DataFrame(rupture_explanations)

        # Métriques
        n_ruptures_global = len(breakpoints_global)
        delta_total = (
            float(tone_global.iloc[-30:].mean() - tone_global.iloc[:30].mean())
            if len(tone_global) > 60
            else None
        )
        worst_domain = None
        if series_by_domain:
            domain_deltas = {
                d: float(s.iloc[-30:].mean() - s.iloc[:30].mean())
                for d, s in series_by_domain.items()
                if len(s) > 60
            }
            if domain_deltas:
                worst_domain = min(domain_deltas, key=domain_deltas.get)

        metrics = {
            "n_events": len(events),
            "n_ruptures_global": n_ruptures_global,
            "delta_tone_global": round(delta_total, 2) if delta_total is not None else None,
            "n_breakpoints_by_domain": {
                d: len(bps) for d, bps in breakpoints_by_domain.items()
            },
            "worst_domain": worst_domain,
        }

        # Insight narratif
        delta_str = (
            f"{metrics['delta_tone_global']:+.2f} points"
            if metrics["delta_tone_global"] is not None
            else "n/a"
        )
        insight = (
            f"Le ton mondial sur le Bénin connaît {n_ruptures_global} ruptures "
            f"sur la période, avec une dérive globale de {delta_str}. "
            f"Domaine le plus dégradé : {worst_domain or 'n/a'}. "
            "Les ruptures sont attribuables à des stories identifiables dans "
            "la table `ruptures`."
        )

        return Result(
            question_id=self.id,
            title=self.title,
            metrics=metrics,
            tables=tables,
            figures=figures,
            insight_text=insight,
            metadata={
                "filters": filters.describe(),
                "domains_analysed": list(series_by_domain.keys()),
            },
        )


QUESTION = _Q2()
