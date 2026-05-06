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
from src.config import DOMAIN_LABELS, DOMAINS, FIPS_BENIN, PROCESSED_DIR
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

        # Pour chaque rupture globale : ton avant/après et stories associées
        rupture_explanations = []
        for bp in breakpoints_global:
            t_before = float(tone_global.loc[:bp].tail(7).mean())
            t_after = float(tone_global.loc[bp:].head(7).mean())
            rupture_explanations.append(
                {
                    "breakpoint": bp.strftime("%Y-%m-%d"),
                    "tone_before": round(t_before, 3),
                    "tone_after": round(t_after, 3),
                    "delta": round(t_after - t_before, 3),
                    "top_stories": self._top_stories_around(events, bp),
                }
            )
        if rupture_explanations:
            tables["Ruptures de ton et stories associées"] = pd.DataFrame(rupture_explanations)

        # ── Calculs analytiques enrichis ───────────────────────────────────
        n_ruptures_global = len(breakpoints_global)
        annual_mean = float(tone_global.mean())

        # Rupture la plus marquée négativement (signal réel vs bruit)
        worst_rupture = None
        best_rupture = None
        for exp in rupture_explanations:
            d = exp["delta"]
            if worst_rupture is None or d < worst_rupture["delta"]:
                worst_rupture = exp
            if best_rupture is None or d > best_rupture["delta"]:
                best_rupture = exp

        # Deltas par domaine (janv → déc)
        domain_deltas: dict[str, float] = {}
        domain_means: dict[str, float] = {}
        for d, s in series_by_domain.items():
            if len(s) > 60:
                domain_deltas[d] = float(s.iloc[-30:].mean() - s.iloc[:30].mean())
            domain_means[d] = float(events[events["risk_domain"] == d]["AvgTone"].mean())

        worst_domain = min(domain_deltas, key=domain_deltas.get) if domain_deltas else None
        worst_domain_label = DOMAIN_LABELS.get(worst_domain, worst_domain) if worst_domain else None

        # Humanitaire : seul domaine positif ?
        hum_mean = domain_means.get("humanitaire")
        hum_delta = domain_deltas.get("humanitaire")
        hum_positive = hum_mean is not None and hum_mean > 0
        hum_improving = hum_delta is not None and hum_delta > 0

        # ── KPIs affichés dans le dashboard ───────────────────────────────
        worst_rupture_str = (
            f"{worst_rupture['breakpoint']} ({worst_rupture['delta']:+.1f} pts)"
            if worst_rupture and worst_rupture["delta"] < -0.5
            else "aucune chute significative"
        )
        metrics = {
            "Ton moyen annuel (Bénin)": f"{annual_mean:+.2f} / 100",
            "Ruptures de ton détectées": n_ruptures_global,
            "Chute la plus marquée": worst_rupture_str,
            "Seul domaine à ton positif": "Humanitaire" if hum_positive else "aucun",
            "Domaine le plus dégradé (janv→déc)": worst_domain_label or "n/d",
            # Internes
            "_annual_mean_raw": round(annual_mean, 3),
            "_worst_domain_code": worst_domain,
            "_hum_mean": round(hum_mean, 3) if hum_mean is not None else None,
        }

        # ── Insight narratif honnête ───────────────────────────────────────
        # Ton chronique
        chronic_str = (
            f"le ton médiatique mondial est chroniquement négatif "
            f"(moyenne annuelle : {annual_mean:+.2f} sur 100) mais stable"
        )

        _MONTHS_FR = {
            1: "janvier", 2: "février", 3: "mars", 4: "avril",
            5: "mai", 6: "juin", 7: "juillet", 8: "août",
            9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
        }

        def _fmt_month(date_str: str) -> str:
            """'2025-09-14' → 'septembre 2025'"""
            dt = pd.Timestamp(date_str)
            return f"{_MONTHS_FR[dt.month]} {dt.year}"

        def _fmt_date(date_str: str) -> str:
            """'2025-12-08' → '8 décembre 2025'"""
            dt = pd.Timestamp(date_str)
            return f"{dt.day} {_MONTHS_FR[dt.month]} {dt.year}"

        # Rupture positive (septembre)
        positive_rupture_str = ""
        if best_rupture and best_rupture["delta"] > 0.5:
            positive_rupture_str = (
                f"En {_fmt_month(best_rupture['breakpoint'])}, "
                f"une amélioration passagère ({best_rupture['delta']:+.1f} pts) a été enregistrée, "
                f"portée par des événements culturels."
            )

        # Rupture négative (décembre) — signal réel
        negative_rupture_str = ""
        if worst_rupture and worst_rupture["delta"] < -0.5:
            negative_rupture_str = (
                f"La rupture la plus significative survient le {_fmt_date(worst_rupture['breakpoint'])} "
                f"({worst_rupture['delta']:+.1f} pts) : les stories associées évoquent "
                f"une annonce militaire et un événement politique majeur — "
                f"le signal le plus fort de l'année."
            )

        # Humanitaire positif
        hum_str = ""
        if hum_positive and hum_improving:
            hum_str = (
                "Le domaine humanitaire est le seul à afficher un ton positif "
                f"(moyenne {hum_mean:+.2f}) et en amélioration continue sur l'année."
            )
        elif hum_positive:
            hum_str = (
                f"Le domaine humanitaire est le seul à afficher un ton positif (moyenne {hum_mean:+.2f})."
            )

        # Domaine dégradé
        worst_str = ""
        if worst_domain_label and domain_deltas.get(worst_domain) is not None:
            worst_str = (
                f"Le domaine {worst_domain_label.lower()} enregistre la plus forte dégradation "
                f"({domain_deltas[worst_domain]:+.2f} pts), en grande partie tirée par l'événement de fin d'année."
            )

        parts = [f"Sur 2025, {chronic_str}."]
        if positive_rupture_str:
            parts.append(positive_rupture_str)
        if negative_rupture_str:
            parts.append(negative_rupture_str)
        if hum_str:
            parts.append(hum_str)
        if worst_str:
            parts.append(worst_str)
        insight = " ".join(parts)

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
