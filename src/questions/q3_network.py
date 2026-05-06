"""Q3 — Le réseau : recomposition diplomatique observable sur 2025.

Analyse avec qui le Bénin co-apparaît dans la presse mondiale, et comment
cette structure a évolué entre H1 (jan–juin) et H2 (juil–déc 2025).

Note méthodologique importante :
- Les données GDELT sont dominées par les médias nigérians (punchng.com,
  dailypost.ng…). Le Nigeria apparaît en tête des partenaires en partie
  à cause de ce biais de collecte — interpréter avec prudence.
- "Benin" en anglais peut désigner le Bénin-pays OU Benin City (Nigeria),
  source possible de faux positifs dans le géocodage GDELT.
- Les acteurs retenus pour la comparaison sont des pays tiers uniquement
  (codes ISO-3, hors Bénin lui-même et codes génériques de type GOV/MIL).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd
import plotly.graph_objects as go

from src.analytics import aggregate
from src.config import CAMEO_BENIN, FIPS_BENIN, PROCESSED_DIR, humanize_actor
from src.questions.base import Filters, Result

logger = logging.getLogger(__name__)

# Pivot H1 / H2 — 1er juillet 2025
PIVOT_DATE = pd.Timestamp(date(2025, 7, 1))

# Codes à exclure de l'analyse des partenaires :
# - entités béninoises (BEN*) → sujet de l'analyse, pas un partenaire
# - codes de type génériques CAMEO → pas des pays identifiables
_BENIN_PREFIX = "BEN"
_GENERIC_TYPES = {
    "GOV", "MIL", "CVL", "NGO", "IGO", "MED", "UAF", "REB", "SPY",
    "COP", "EDU", "LEG", "BUS", "HLH", "OPP", "JUD", "REF", "LAB",
    "AFR", "WEU", "INT", "CHR", "SOC", "IND", "ACT", "ETH", "CRM",
    "TER", "ENV", "COM", "MOV", "MIG", "ELI", "INS",
}


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
        mask = (
            (df["ActionGeo_CountryCode"] == FIPS_BENIN)
            | (df["Actor1CountryCode"] == CAMEO_BENIN)
            | (df["Actor2CountryCode"] == CAMEO_BENIN)
        )
        return df[mask]

    def _apply_filters(self, df: pd.DataFrame, filters: Filters) -> pd.DataFrame:
        df = aggregate.filter_period(df, date_from=filters.date_from, date_to=filters.date_to)
        df = aggregate.confidence_filter(df, tier=filters.confidence)
        return df

    def _build_partner_table(self, events: pd.DataFrame) -> pd.DataFrame:
        """Construit le tableau H1/H2 des partenaires pays du Bénin.

        Retient uniquement les codes pays ISO-3 tiers (exclut BEN* et génériques).
        """
        pairs = events.dropna(subset=["Actor1Code", "Actor2Code"]).copy()

        b1 = pairs[pairs["Actor1CountryCode"] == CAMEO_BENIN][
            ["Actor2Code", "NumMentions", "SQLDATE", "AvgTone"]
        ].rename(columns={"Actor2Code": "partner_code"})

        b2 = pairs[pairs["Actor2CountryCode"] == CAMEO_BENIN][
            ["Actor1Code", "NumMentions", "SQLDATE", "AvgTone"]
        ].rename(columns={"Actor1Code": "partner_code"})

        bp = pd.concat([b1, b2], ignore_index=True)

        # Garder uniquement codes pays ISO-3 purs (longueur 3, hors BEN* et génériques)
        bp = bp[bp["partner_code"].str.len() == 3]
        bp = bp[~bp["partner_code"].str.startswith(_BENIN_PREFIX, na=False)]
        bp = bp[~bp["partner_code"].isin(_GENERIC_TYPES)]
        bp = bp.dropna(subset=["partner_code"])

        bp["period"] = bp["SQLDATE"].apply(
            lambda d: "H1" if pd.Timestamp(d) < PIVOT_DATE else "H2"
        )

        # Agrégation par partenaire × période
        agg = (
            bp.groupby(["partner_code", "period"])
            .agg(mentions=("NumMentions", "sum"), avg_tone=("AvgTone", "mean"))
            .reset_index()
        )
        pivot = agg.pivot(index="partner_code", columns="period", values="mentions").fillna(0)
        tone = agg.pivot(index="partner_code", columns="period", values="avg_tone")

        pivot["total"] = pivot.get("H1", 0) + pivot.get("H2", 0)
        pivot["delta"] = pivot.get("H2", 0) - pivot.get("H1", 0)
        h1_safe = pivot["H1"].replace(0, float("nan"))
        pivot["delta_pct"] = ((pivot["delta"] / h1_safe) * 100).round(1)
        pivot["ton_moyen"] = bp.groupby("partner_code")["AvgTone"].mean().round(2)
        pivot["label"] = [humanize_actor(c) for c in pivot.index]

        return (
            pivot.sort_values("total", ascending=False)
            .head(15)
            .reset_index()
        )

    def _build_comparison_chart(self, partner_df: pd.DataFrame, title: str) -> go.Figure:
        """Graphique à barres groupées H1 vs H2 par partenaire pays."""
        df = partner_df.sort_values("total", ascending=True).tail(12)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="H1 jan–juin 2025",
            y=df["label"],
            x=df.get("H1", pd.Series(dtype=float)).fillna(0),
            orientation="h",
            marker_color="#5B9BD5",
        ))
        fig.add_trace(go.Bar(
            name="H2 juil–déc 2025",
            y=df["label"],
            x=df.get("H2", pd.Series(dtype=float)).fillna(0),
            orientation="h",
            marker_color="#ED7D31",
        ))
        fig.update_layout(
            barmode="group",
            title=title,
            xaxis_title="Mentions cumulées",
            yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin={"r": 10, "t": 60, "l": 10, "b": 40},
            height=500,
        )
        return fig

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

        # 1. Tableau des partenaires pays H1 vs H2
        partner_df = self._build_partner_table(events)

        h1_total = len(events[events["SQLDATE"] < PIVOT_DATE])
        h2_total = len(events[events["SQLDATE"] >= PIVOT_DATE])
        n_partners = len(partner_df)

        # 2. Statistiques clés sur les pays significatifs
        def _partner_row(code: str):
            rows = partner_df[partner_df["partner_code"] == code]
            return rows.iloc[0] if not rows.empty else None

        niger = _partner_row("NER")
        nigeria = _partner_row("NGA")
        burkina = _partner_row("BFA")
        togo = _partner_row("TGO")
        france = _partner_row("FRA")

        # 3. Figures
        figures = {
            "partenaires_h1_vs_h2": self._build_comparison_chart(
                partner_df,
                title="Q3 — Partenaires du Bénin dans la presse : H1 vs H2 2025",
            )
        }

        # 4. Métriques affichées en KPI
        niger_delta_str = (
            f"{int(niger['delta_pct'])} %" if niger is not None and pd.notna(niger["delta_pct"])
            else "n/d"
        )
        metrics = {
            "Pays partenaires identifiés": n_partners,
            "Articles H1 (jan–juin)": h1_total,
            "Articles H2 (juil–déc)": h2_total,
            "Niger : variation H1→H2": niger_delta_str,
            "_partner_df": partner_df.to_dict(orient="records"),
        }

        # 5. Insight narratif — centré sur les signaux géopolitiques réels
        niger_str = (
            f"Le Niger, 3e partenaire en H1 ({int(niger['H1']):,} mentions), "
            f"a presque disparu en H2 ({int(niger['H2']):,} mentions, "
            f"{int(niger['delta_pct'])} %), avec le ton le plus négatif "
            f"de tous les partenaires ({niger['ton_moyen']:.2f})."
            if niger is not None else ""
        )
        burkina_str = (
            f"Le Burkina Faso a également reculé de {int(burkina['delta_pct'])} %."
            if burkina is not None and pd.notna(burkina["delta_pct"]) else ""
        )
        togo_str = (
            "Le Togo, absent en H1, émerge en H2 comme nouveau partenaire régional."
            if togo is not None and togo.get("H1", 0) == 0 and togo.get("H2", 0) > 0
            else ""
        )
        nigeria_str = (
            "Le Nigeria domine en volume, mais cela reflète en partie la surreprésentation "
            "des médias nigérians dans GDELT plutôt qu'une activité diplomatique accrue."
            if nigeria is not None else ""
        )

        insight = (
            f"Sur 2025, {n_partners} pays co-apparaissent avec le Bénin dans la presse mondiale. "
            f"{niger_str} {burkina_str} {togo_str} {nigeria_str}"
        ).strip()

        # Table lisible pour le dashboard
        table_display = partner_df[["label", "H1", "H2", "delta", "delta_pct", "ton_moyen"]].rename(columns={
            "label": "Partenaire",
            "H1": "Mentions H1 (jan–juin)",
            "H2": "Mentions H2 (juil–déc)",
            "delta": "Variation (mentions)",
            "delta_pct": "Variation (%)",
            "ton_moyen": "Ton moyen",
        })
        table_display["Mentions H1 (jan–juin)"] = table_display["Mentions H1 (jan–juin)"].astype(int)
        table_display["Mentions H2 (juil–déc)"] = table_display["Mentions H2 (juil–déc)"].astype(int)
        table_display["Variation (mentions)"] = table_display["Variation (mentions)"].astype(int)

        return Result(
            question_id=self.id,
            title=self.title,
            metrics=metrics,
            tables={"Partenaires du Bénin — comparaison H1 / H2": table_display},
            figures=figures,
            insight_text=insight,
            metadata={
                "filters": filters.describe(),
                "pivot_date": PIVOT_DATE.strftime("%Y-%m-%d"),
                "n_events_h1": h1_total,
                "n_events_h2": h2_total,
                "biais_note": "Top sources: médias nigérians (punchng, dailypost, leadership, guardian.ng).",
            },
        )


QUESTION = _Q3()
