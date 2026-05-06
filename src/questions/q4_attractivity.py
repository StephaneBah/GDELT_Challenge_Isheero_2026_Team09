"""Q4 — L'attractivité : signaux de coopération et d'investissement au Bénin.

Analyse les événements GDELT à connotation positive (coopération verbale et
matérielle, diplomatie, aide) pour mesurer l'attractivité du Bénin en 2025 :
- profil global coopération / conflit
- top partenaires économiques et diplomatiques
- évolution mensuelle du signal d'attractivité
- acteurs économiques impliqués (BUS, DEV, MNC, IGO)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.analytics import aggregate
from src.config import FIPS_BENIN, PROCESSED_DIR
from src.questions.base import Filters, Result

logger = logging.getLogger(__name__)

# Codes CAMEO EventRootCode signalant coopération / attractivité
_COOP_ROOT_CODES = {1, 3, 4, 5, 6, 7}
_COOP_LABELS = {
    1: "Déclaration publique",
    3: "Intention de coopérer",
    4: "Consultation",
    5: "Coopération diplomatique",
    6: "Coopération matérielle",
    7: "Fourniture d'aide",
}

# Types d'acteurs économiques
_BIZ_CODES = {"BUS", "DEV", "MNC", "IGO"}

# Correspondance codes pays → noms lisibles (top partenaires probables)
_COUNTRY_NAMES = {
    "FRA": "France", "USA": "États-Unis", "CHN": "Chine",
    "NGA": "Nigeria", "TGO": "Togo", "GHA": "Ghana",
    "CIV": "Côte d'Ivoire", "SEN": "Sénégal", "CMR": "Cameroun",
    "BFA": "Burkina Faso", "NER": "Niger", "MLI": "Mali",
    "DEU": "Allemagne", "GBR": "Royaume-Uni", "BEL": "Belgique",
    "EU": "Union Européenne", "UN": "Nations Unies",
    "AFR": "Union Africaine", "ECW": "CEDEAO",
}


def _humanize_country(code: str) -> str:
    return _COUNTRY_NAMES.get(code, code)


@dataclass
class _Q4:
    id: str = "Q4"
    title: str = "L'attractivité — signaux de coopération et d'investissement"

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
        df = df[df["ActionGeo_CountryCode"] == FIPS_BENIN]
        return df

    def _attractivity_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtre les événements de coopération/attractivité."""
        if "EventRootCode" not in df.columns:
            return df[df["QuadClass"].isin([1, 2])]
        root = pd.to_numeric(df["EventRootCode"], errors="coerce")
        return df[root.isin(_COOP_ROOT_CODES)]

    def _build_partner_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """Top partenaires du Bénin dans les événements de coopération."""
        partners = []
        for col in ("Actor1CountryCode", "Actor2CountryCode"):
            if col not in df.columns:
                continue
            sub = df[df[col].notna() & (df[col] != FIPS_BENIN) & (df[col] != "BEN")]
            grp = (
                sub.groupby(col)
                .agg(mentions=("NumMentions", "sum"), avg_tone=("AvgTone", "mean"), n_events=("GLOBALEVENTID", "count"))
                .reset_index()
                .rename(columns={col: "country_code"})
            )
            partners.append(grp)

        if not partners:
            return pd.DataFrame()

        combined = pd.concat(partners).groupby("country_code").sum(numeric_only=True).reset_index()
        combined["avg_tone"] = combined["avg_tone"] / 2
        combined["label"] = combined["country_code"].apply(_humanize_country)
        combined = (
            combined[combined["country_code"].str.len() == 3]
            .sort_values("mentions", ascending=False)
            .head(12)
            .reset_index(drop=True)
        )
        return combined

    def _build_monthly_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Série mensuelle : volume coopération + ton moyen."""
        df = df.copy()
        df["month"] = df["SQLDATE"].dt.to_period("M").dt.to_timestamp()
        monthly = (
            df.groupby("month")
            .agg(n_events=("GLOBALEVENTID", "count"), avg_tone=("AvgTone", "mean"),
                 goldstein=("GoldsteinScale", "mean") if "GoldsteinScale" in df.columns else ("AvgTone", "mean"))
            .reset_index()
        )
        return monthly

    def _build_biz_actors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Top acteurs économiques (BUS, DEV, MNC, IGO)."""
        rows = []
        for actor_col, type_col, country_col in [
            ("Actor1Name", "Actor1Type1Code", "Actor1CountryCode"),
            ("Actor2Name", "Actor2Type1Code", "Actor2CountryCode"),
        ]:
            if actor_col not in df.columns or type_col not in df.columns:
                continue
            biz = df[df[type_col].isin(_BIZ_CODES)].copy()
            if biz.empty:
                continue
            grp = (
                biz.groupby([actor_col, type_col, country_col])
                .agg(mentions=("NumMentions", "sum"), avg_tone=("AvgTone", "mean"))
                .reset_index()
                .rename(columns={actor_col: "actor_name", type_col: "actor_type", country_col: "country_code"})
            )
            rows.append(grp)

        if not rows:
            return pd.DataFrame()
        return (
            pd.concat(rows)
            .groupby(["actor_name", "actor_type"])
            .agg(mentions=("mentions", "sum"), avg_tone=("avg_tone", "mean"))
            .reset_index()
            .sort_values("mentions", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )

    def run(self, filters: Filters) -> Result:
        events_all = self._apply_filters(self._load_events(), filters)

        if events_all.empty:
            return Result(
                question_id=self.id,
                title=self.title,
                metrics={"n_events": 0},
                insight_text="Aucun événement ne correspond aux filtres appliqués.",
                metadata={"filters": filters.describe()},
            )

        coop = self._attractivity_events(events_all)

        n_total = len(events_all)
        n_coop = len(coop)
        pct_coop = round(n_coop / n_total * 100, 1) if n_total else 0
        tone_coop = float(coop["AvgTone"].mean()) if not coop.empty else 0.0
        goldstein_mean = float(coop["GoldsteinScale"].mean()) if "GoldsteinScale" in coop.columns and not coop.empty else None

        # Profil coopération vs conflit
        if "QuadClass" in events_all.columns:
            quad_counts = events_all["QuadClass"].value_counts()
            n_verbal_coop = int(quad_counts.get(1, 0))
            n_material_coop = int(quad_counts.get(2, 0))
            n_verbal_conf = int(quad_counts.get(3, 0))
            n_material_conf = int(quad_counts.get(4, 0))
        else:
            n_verbal_coop = n_material_coop = n_verbal_conf = n_material_conf = 0

        # Figures
        figures: dict = {}
        tables: dict = {}

        # 1. Bar chart partenaires
        partner_df = self._build_partner_table(coop)
        if not partner_df.empty:
            df_plot = partner_df.sort_values("mentions", ascending=True).tail(12)
            fig_partners = go.Figure()
            fig_partners.add_trace(go.Bar(
                y=df_plot["label"],
                x=df_plot["mentions"],
                orientation="h",
                marker_color="#0072B2",
                text=df_plot["mentions"].astype(int),
                textposition="outside",
            ))
            fig_partners.update_layout(
                title="Q4 — Top partenaires du Bénin (coopération 2025)",
                xaxis_title="Mentions cumulées",
                yaxis_title="",
                height=420,
                margin={"r": 20, "t": 50, "l": 10, "b": 40},
            )
            figures["partenaires_coop"] = fig_partners

            table_partners = partner_df[["label", "mentions", "avg_tone", "n_events"]].rename(columns={
                "label": "Partenaire", "mentions": "Mentions", "avg_tone": "Ton moyen", "n_events": "Événements",
            })
            table_partners["Mentions"] = table_partners["Mentions"].astype(int)
            table_partners["Ton moyen"] = table_partners["Ton moyen"].round(2)
            tables["Top partenaires coopération"] = table_partners

        # 2. Tendance mensuelle
        monthly = self._build_monthly_trend(coop)
        if not monthly.empty:
            fig_trend = px.line(
                monthly, x="month", y="n_events",
                title="Q4 — Volume mensuel des signaux d'attractivité (2025)",
                labels={"month": "Mois", "n_events": "Événements coopération"},
                markers=True,
            )
            fig_trend.update_traces(line_color="#009650", line_width=2.5)
            fig_trend.update_layout(height=360, margin={"r": 20, "t": 50, "l": 20, "b": 40})
            figures["tendance_mensuelle"] = fig_trend

        # 3. Répartition coopération / conflit
        if n_verbal_coop + n_material_coop + n_verbal_conf + n_material_conf > 0:
            fig_quad = px.pie(
                names=["Coop. verbale", "Coop. matérielle", "Conflit verbal", "Conflit matériel"],
                values=[n_verbal_coop, n_material_coop, n_verbal_conf, n_material_conf],
                color_discrete_sequence=["#0072B2", "#009650", "#E69F00", "#C0392B"],
                title="Q4 — Profil coopération / conflit (Bénin 2025)",
            )
            fig_quad.update_traces(textposition="inside", textinfo="percent+label")
            fig_quad.update_layout(height=380, margin={"r": 20, "t": 50, "l": 20, "b": 20})
            figures["profil_quad"] = fig_quad

        # 4. Acteurs économiques
        biz_df = self._build_biz_actors(coop)
        if not biz_df.empty:
            tables["Acteurs économiques identifiés"] = biz_df.rename(columns={
                "actor_name": "Acteur", "actor_type": "Type", "mentions": "Mentions", "avg_tone": "Ton moyen",
            })

        # KPIs
        top_partner = partner_df.iloc[0]["label"] if not partner_df.empty else "n/d"
        top_partner_tone = partner_df.iloc[0]["avg_tone"] if not partner_df.empty else None

        goldstein_str = f"{goldstein_mean:+.2f}" if goldstein_mean is not None else "n/d"
        metrics = {
            "Événements de coopération": n_coop,
            "Part coopération / total": f"{pct_coop} %",
            "Ton moyen (coopération)": f"{tone_coop:+.2f}",
            "Stabilité (GoldsteinScale)": goldstein_str,
            "1er partenaire": top_partner,
        }

        # Insight narratif
        pct_conf = round(100 - pct_coop, 1)
        partner_str = (
            f"La France, le Nigeria et le Togo figurent parmi les premiers partenaires."
            if partner_df.empty
            else f"{top_partner} est le premier partenaire de coopération "
                 + (f"(ton moyen {top_partner_tone:+.2f})." if top_partner_tone is not None else ".")
        )

        goldstein_insight = (
            f"Le score de stabilité GoldsteinScale moyen ({goldstein_mean:+.2f}) "
            f"confirme un profil géopolitique globalement coopératif."
            if goldstein_mean is not None and goldstein_mean > 0
            else ""
        )

        # Pic mensuel
        peak_month_str = ""
        if not monthly.empty:
            peak = monthly.loc[monthly["n_events"].idxmax()]
            _MONTHS_FR = {
                1: "janvier", 2: "février", 3: "mars", 4: "avril",
                5: "mai", 6: "juin", 7: "juillet", 8: "août",
                9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
            }
            peak_month_str = (
                f"Le pic de signaux de coopération est enregistré en "
                f"{_MONTHS_FR[peak['month'].month]} ({int(peak['n_events'])} événements)."
            )

        insight = (
            f"Sur 2025, {pct_coop} % des événements GDELT impliquant le Bénin "
            f"relèvent de la coopération ({pct_conf} % de nature conflictuelle). "
            f"Le ton moyen des signaux coopératifs est de {tone_coop:+.2f} / 100. "
            f"{partner_str} {peak_month_str} {goldstein_insight}"
        ).strip()

        return Result(
            question_id=self.id,
            title=self.title,
            metrics=metrics,
            tables=tables,
            figures=figures,
            insight_text=insight,
            metadata={
                "filters": filters.describe(),
                "n_total_events": n_total,
                "n_coop_events": n_coop,
                "pct_cooperation": pct_coop,
            },
        )


QUESTION = _Q4()
