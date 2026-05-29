from pathlib import Path
import os
import pandas as pd
import numpy as np

DATA_PATH = Path(os.getenv("DATA_PATH", "../data/GDELT_events_benin_2025_cleaned.csv"))

# ── Codes CAMEO par secteur ───────────────────────────────────────────────────
# Combinaison EventCode précis + EventRootCode selon la logique du dashboard original

ECONOMIC_CODES = {
    61, 71, 85, 211, 231, 254, 311, 331, 354,
    1011, 1031, 1054, 1211, 1221, 1244, 1312, 1621, 163
}
DIPLO_CODES = {
    22, 32, 42, 43, 46, 50, 54, 57, 102, 105, 108,
    125, 126, 134, 135, 161, 164, 165
}
COOP_ROOTS    = {3, 4, 5, 6, 7}
CONFLICT_ROOTS = {13, 14, 15, 16, 17, 18, 19, 20}

# Gouvernance = tout ce qui n'est pas dans les autres secteurs majeurs
GOVERNANCE_ROOTS = {1, 2, 9, 10, 11, 12}

CAMEO_ROOTS = {
    1: "Déclarations publiques",
    2: "Appels & Demandes",
    3: "Intentions de coopérer",
    4: "Consultations diplomatiques",
    5: "Coopération diplomatique",
    6: "Coopération matérielle",
    7: "Aide fournie",
    8: "Cessions & Accords",
    9: "Enquêtes",
    10: "Exigences",
    11: "Désapprobations",
    12: "Rejets & Refus",
    13: "Menaces",
    14: "Manifestations",
    15: "Démonstrations de force",
    16: "Réductions de relations",
    17: "Coercitions",
    18: "Agressions",
    19: "Combats armés",
    20: "Violences de masse",
}

_df_cache: pd.DataFrame | None = None


def get_df() -> pd.DataFrame:
    global _df_cache
    if _df_cache is not None:
        return _df_cache

    path = Path(__file__).parent.parent / DATA_PATH
    df = pd.read_csv(path, low_memory=False)

    for col in ["AvgTone", "GoldsteinScale", "NumMentions", "NumSources", "NumArticles",
                "ActionGeo_Lat", "ActionGeo_Long"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "SQLDATE" in df.columns:
        df["event_date"] = pd.to_datetime(df["SQLDATE"].astype(str), errors="coerce")
    elif "MonthYear" in df.columns:
        df["event_date"] = pd.to_datetime(df["MonthYear"].astype(str), format="%Y%m", errors="coerce")
    df["month"] = df["event_date"].dt.to_period("M").dt.to_timestamp()

    df["root_int"]       = pd.to_numeric(df.get("EventRootCode", pd.Series(dtype=float)), errors="coerce").fillna(-1).astype(int)
    df["event_code_int"] = pd.to_numeric(df.get("EventCode",     pd.Series(dtype=float)), errors="coerce").fillna(-1).astype(int)

    df["event_root_label"] = df["root_int"].map(CAMEO_ROOTS).fillna("Inconnu")

    a1l = df.get("Actor1CountryLabel", pd.Series(dtype=str))
    a1c = df.get("Actor1CountryCode",  pd.Series(dtype=str))
    df["actor1_country"] = a1l.fillna(a1c).fillna("Inconnu").replace("", "Inconnu")

    a2l = df.get("Actor2CountryLabel", pd.Series(dtype=str))
    df["actor2_country"] = a2l.fillna("Inconnu").replace("", "Inconnu")

    df["actor1_type"] = df.get("Actor1Type1Label", pd.Series(dtype=str)).fillna("Inconnu")
    df["actor2_type"] = df.get("Actor2Type1Label", pd.Series(dtype=str)).fillna("Inconnu")

    # Drapeaux secteur — combos EventCode + RootCode
    df["is_economic"]    = df["event_code_int"].isin(ECONOMIC_CODES)
    df["is_diplomatic"]  = df["event_code_int"].isin(DIPLO_CODES) | df["root_int"].isin({4, 5})
    df["is_cooperation"] = df["root_int"].isin(COOP_ROOTS)
    df["is_conflict"]    = df["root_int"].isin(CONFLICT_ROOTS)
    df["is_governance"]  = df["root_int"].isin(GOVERNANCE_ROOTS)

    # Indice de tension composite (0-100)
    gold_norm = df["GoldsteinScale"].clip(-10, 10) / 10
    tone_norm = df["AvgTone"].clip(-20, 20) / 20
    df["tension_idx"] = ((-gold_norm * 0.6 + -tone_norm * 0.4 + 1) / 2 * 100).clip(0, 100).round(1)

    _df_cache = df.copy()
    return _df_cache


SECTOR_FILTERS = {
    "economie":    lambda df: df[df["is_economic"]],
    "diplomatie":  lambda df: df[df["is_diplomatic"]],
    "cooperation": lambda df: df[df["is_cooperation"]],
    "conflits":    lambda df: df[df["is_conflict"]],
    "gouvernance": lambda df: df[df["is_governance"]],
    "libre":       lambda df: df,
}

# Mots-clés → secteur : fallback Python si Haiku retourne "libre"
_KW_SECTOR: list[tuple[set[str], str]] = [
    ({"risque", "risques", "sécurité", "menace", "menaces", "instabilité", "violence",
      "conflit", "conflits", "combat", "combats", "crise", "crises", "tension",
      "tensions", "agression", "protestation", "manifestation"}, "conflits"),
    ({"partenaire", "partenaires", "allié", "alliés", "ambassadeur", "négociation",
      "négociations", "bilatéral", "bilatéraux", "visite", "visites", "accord",
      "accords", "traité", "traités", "relation", "relations", "diplomatique"}, "diplomatie"),
    ({"aide", "financement", "développement", "coopération", "partenariat",
      "organisation", "international", "multilatéral", "don", "subvention",
      "onu", "cedeao", "ua", "banque mondiale", "fmi"}, "cooperation"),
    ({"économie", "économique", "commerce", "commercial", "investissement",
      "budget", "fiscal", "croissance", "pib", "exportation", "importation",
      "sanction", "sanctions", "dette", "financement"}, "economie"),
    ({"élection", "élections", "gouvernement", "institution", "réforme",
      "politique", "parlement", "constitution", "administration",
      "président", "ministre"}, "gouvernance"),
]

def infer_sector_from_text(message: str) -> str | None:
    """Détecte un secteur à partir des mots du message — fallback si Haiku dit 'libre'."""
    words = set(message.lower().split())
    scores: dict[str, int] = {}
    for kw_set, sector in _KW_SECTOR:
        hit = len(words & kw_set)
        if hit:
            scores[sector] = scores.get(sector, 0) + hit
    if scores:
        return max(scores, key=lambda s: scores[s])
    return None


def filter_data(
    sector: str,
    keywords: list[str],
    date_from: str | None = None,
    date_to: str | None = None,
) -> pd.DataFrame:
    df = get_df()
    sector_key = sector.lower().strip()

    if sector_key in SECTOR_FILTERS:
        df = SECTOR_FILTERS[sector_key](df)

    # Filtre temporel (YYYYMMDD strings venant de l'intent)
    if date_from:
        try:
            df = df[df["event_date"] >= pd.to_datetime(date_from, format="%Y%m%d", errors="coerce")]
        except Exception:
            pass
    if date_to:
        try:
            df = df[df["event_date"] <= pd.to_datetime(date_to, format="%Y%m%d", errors="coerce")]
        except Exception:
            pass

    if keywords:
        kw_lower = [k.lower() for k in keywords]
        # Mots abstraits qui ne matchent pas des noms de pays/codes — on les ignore
        ABSTRACT = {"risque", "risques", "sécurité", "instabilité", "crise", "crises",
                    "indicateur", "indicateurs", "analyse", "tendance", "tendances",
                    "performance", "bilan", "résultat", "impact", "signal", "signaux"}
        concrete_kw = [k for k in kw_lower if k not in ABSTRACT]
        if concrete_kw:
            mask = pd.Series(False, index=df.index)
            for kw in concrete_kw:
                mask |= df["event_root_label"].str.lower().str.contains(kw, na=False)
                mask |= df["actor1_country"].str.lower().str.contains(kw, na=False)
                mask |= df["actor2_country"].str.lower().str.contains(kw, na=False)
                mask |= df["actor1_type"].str.lower().str.contains(kw, na=False)
            if mask.any():
                df = df[mask]
        # Si tous les keywords sont abstraits → le filtre sectoriel suffit, pas de réduction

    return df.copy()


def summarize(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"error": "Aucune donnée pour ces filtres"}

    monthly = (
        df.groupby("month")
        .agg(count=("GLOBALEVENTID", "count"),
             avg_tone=("AvgTone", "mean"),
             avg_gold=("GoldsteinScale", "mean"),
             avg_tension=("tension_idx", "mean"))
        .reset_index()
    )
    monthly["month"] = monthly["month"].astype(str)

    # Anomalies : mois avec volume ou tension hors ±1.5σ
    anomalies = []
    if len(monthly) >= 3:
        vm, vs = monthly["count"].mean(), monthly["count"].std()
        tm, ts = monthly["avg_tension"].mean(), monthly["avg_tension"].std()
        anomalies = monthly[
            (monthly["count"] > vm + 1.5 * vs) |
            (monthly["count"] < vm - 1.5 * vs) |
            (monthly["avg_tension"] > tm + 1.5 * ts)
        ]["month"].tolist()

    top_themes = df["event_root_label"].value_counts().head(8).to_dict()
    top_actors = (
        df[~df["actor1_country"].str.lower().isin(["bénin", "benin", "inconnu", ""])]
        ["actor1_country"].value_counts().head(8).to_dict()
    )

    return {
        "total_events":    int(len(df)),
        "date_range":      {"min": str(df["event_date"].min())[:10], "max": str(df["event_date"].max())[:10]},
        "avg_tone":        round(float(df["AvgTone"].mean()), 2),
        "avg_goldstein":   round(float(df["GoldsteinScale"].mean()), 2),
        "avg_tension":     round(float(df["tension_idx"].mean()), 1),
        "coop_pct":        round(float(df["is_cooperation"].mean()) * 100, 1),
        "conflict_pct":    round(float(df["is_conflict"].mean()) * 100, 1),
        "economic_pct":    round(float(df["is_economic"].mean()) * 100, 1),
        "top_themes":      top_themes,
        "top_actors":      top_actors,
        "anomaly_months":  anomalies,
        "monthly_evolution": monthly.to_dict("records"),
    }


def get_top_urls(df: pd.DataFrame, n: int = 10) -> list[str]:
    if "SOURCEURL" not in df.columns:
        return []
    return (
        df[df["SOURCEURL"].notna()]
        .sort_values("NumMentions", ascending=False)
        .drop_duplicates("SOURCEURL")["SOURCEURL"]
        .head(n)
        .tolist()
    )


def get_anomaly_urls(df: pd.DataFrame, anomaly_months: list[str], n: int = 10) -> list[str]:
    """URLs ciblées sur les mois anomaliques — pour expliquer les pics/creux."""
    if not anomaly_months:
        return get_top_urls(df, n)
    mask = df["month"].astype(str).apply(
        lambda m: any(m[:7] in a[:7] for a in anomaly_months)
    )
    sub = df[mask]
    if sub.empty:
        return get_top_urls(df, n)
    return get_top_urls(sub, n)


def describe_anomaly_period(df: pd.DataFrame, anomaly_months: list[str]) -> str:
    """
    Détail structuré des événements pendant les mois anomaliques.
    Donne au LLM les éléments concrets pour expliquer le pourquoi.
    """
    if not anomaly_months:
        return ""
    mask = df["month"].astype(str).apply(
        lambda m: any(m[:7] in a[:7] for a in anomaly_months)
    )
    sub = df[mask]
    if sub.empty:
        return ""

    lines = [f"DÉTAIL PÉRIODE ANOMALIQUE ({', '.join(anomaly_months)}) — {len(sub)} événements\n"]

    # Types d'événements dominants
    top_codes = sub["event_root_label"].value_counts().head(6).to_dict()
    lines.append("Types d'événements : " + ", ".join(f'"{k}" ({v})' for k, v in top_codes.items()))

    # Acteurs principaux (hors Bénin)
    foreign = sub[~sub["actor1_country"].str.lower().isin(["bénin", "benin", "inconnu", ""])]
    top_actors = foreign["actor1_country"].value_counts().head(5).to_dict()
    if top_actors:
        lines.append("Acteurs étrangers impliqués : " + ", ".join(f"{k} ({v})" for k, v in top_actors.items()))

    # Stats période vs reste
    rest = df[~mask]
    tone_anom  = sub["AvgTone"].mean()
    tone_rest  = rest["AvgTone"].mean() if not rest.empty else 0
    gold_anom  = sub["GoldsteinScale"].mean()
    gold_rest  = rest["GoldsteinScale"].mean() if not rest.empty else 0

    lines.append(
        f"Ton période : {tone_anom:+.2f} vs reste de l'année : {tone_rest:+.2f} "
        f"(écart {tone_anom - tone_rest:+.2f})"
    )
    lines.append(
        f"Goldstein période : {gold_anom:+.2f} vs reste : {gold_rest:+.2f}"
    )

    # Codes CAMEO les plus conflictuels présents
    conflict_present = sub[sub["root_int"].isin(CONFLICT_ROOTS)]["event_root_label"].value_counts().head(3)
    if not conflict_present.empty:
        lines.append("Signaux conflictuels détectés : " + ", ".join(
            f'"{k}" ({v})' for k, v in conflict_present.items()
        ))

    return "\n".join(lines)


def build_charts(df: pd.DataFrame, anomaly_months: list[str]) -> dict:
    import plotly.graph_objects as go

    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Space Grotesk, sans-serif", color="#9a9090", size=11),
        margin=dict(l=8, r=8, t=32, b=8),
        xaxis=dict(showgrid=False, zeroline=False, color="#5e5e70", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, color="#5e5e70"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        hovermode="x unified",
    )

    monthly = (
        df.groupby("month")
        .agg(count=("GLOBALEVENTID", "count"), avg_tone=("AvgTone", "mean"),
             avg_gold=("GoldsteinScale", "mean"), avg_tension=("tension_idx", "mean"))
        .reset_index().sort_values("month")
    )
    monthly["ms"] = monthly["month"].dt.strftime("%b %Y")

    # ── 1. Indice de tension — barres colorées, anomalies rouge ──────────────
    colors = [
        "#d45050" if any(str(row["month"])[:7] in a for a in anomaly_months) else "#1a9da6"
        for _, row in monthly.iterrows()
    ]
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=monthly["ms"], y=monthly["avg_tension"].round(1),
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>Tension : %{y:.0f}/100<extra></extra>",
    ))
    mean_t = monthly["avg_tension"].mean()
    fig1.add_hline(y=mean_t, line_dash="dot", line_color="rgba(255,255,255,0.2)",
                   annotation_text=f"moy. {mean_t:.0f}", annotation_font_color="#5e5e70",
                   annotation_position="right")
    fig1.update_layout(title="Indice de tension médiatique", showlegend=False,
                       yaxis_range=[0, 100], **base)

    # ── 2. Bubble Perception × Stabilité ─────────────────────────────────────
    # Chaque bulle = une catégorie CAMEO. Taille = volume. Couleur = Goldstein.
    cs = (
        df.groupby("event_root_label")
        .agg(volume=("GLOBALEVENTID", "count"), tone=("AvgTone", "mean"),
             stability=("GoldsteinScale", "mean"))
        .reset_index().query("volume >= 30").sort_values("volume", ascending=False).head(12)
    )
    fig2 = go.Figure()
    fig2.add_vrect(x0=-20, x1=0, fillcolor="rgba(212,80,80,0.03)", line_width=0)
    fig2.add_vrect(x0=0, x1=20,  fillcolor="rgba(41,185,125,0.03)", line_width=0)
    fig2.add_hline(y=0, line_color="rgba(255,255,255,0.1)", line_dash="dot")
    fig2.add_vline(x=0, line_color="rgba(255,255,255,0.1)", line_dash="dot")
    fig2.add_trace(go.Scatter(
        x=cs["tone"].round(2), y=cs["stability"].round(2),
        mode="markers+text",
        text=cs["event_root_label"],
        textposition="top center",
        textfont=dict(size=8, color="#9a9090"),
        marker=dict(
            size=(cs["volume"] / cs["volume"].max() * 50 + 10),
            color=cs["stability"],
            colorscale=[[0,"#d45050"],[0.5,"#c8862a"],[1,"#29b97d"]],
            cmin=-5, cmax=5,
            opacity=0.8,
            line=dict(width=1, color="rgba(255,255,255,0.1)"),
        ),
        hovertemplate="<b>%{text}</b><br>Ton : %{x}<br>Stabilité : %{y}<br>Volume : %{customdata}<extra></extra>",
        customdata=cs["volume"],
    ))
    fig2.update_layout(title="Catégories — Perception vs Stabilité", showlegend=False,
                       xaxis_title="Ton médiatique →", yaxis_title="Stabilité →", **base)

    # ── 3. Signal — volume barres + courbes ton & stabilité ──────────────────
    tone_std = monthly["avg_tone"].std()
    fig3 = go.Figure()
    # Bande de confiance
    fig3.add_trace(go.Scatter(
        x=list(monthly["ms"]) + list(monthly["ms"])[::-1],
        y=list((monthly["avg_tone"] + tone_std).round(2)) + list((monthly["avg_tone"] - tone_std).round(2))[::-1],
        fill="toself", fillcolor="rgba(26,157,166,0.05)", line_width=0,
        showlegend=False, hoverinfo="skip",
    ))
    # Volume en fond
    fig3.add_trace(go.Bar(
        x=monthly["ms"], y=monthly["count"],
        name="Volume", marker_color="rgba(200,134,42,0.2)",
        yaxis="y2", hovertemplate="%{y} événements<extra></extra>",
    ))
    fig3.add_trace(go.Scatter(
        x=monthly["ms"], y=monthly["avg_tone"].round(2),
        name="Ton", line=dict(color="#1a9da6", width=2),
        mode="lines+markers", marker=dict(size=4),
        hovertemplate="Ton : %{y:.2f}<extra></extra>",
    ))
    fig3.add_trace(go.Scatter(
        x=monthly["ms"], y=monthly["avg_gold"].round(2),
        name="Stabilité", line=dict(color="#c8862a", width=2, dash="dash"),
        mode="lines", hovertemplate="Goldstein : %{y:.2f}<extra></extra>",
    ))
    fig3.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.1)")
    fig3.update_layout(
        title="Signal médiatique mensuel",
        yaxis2=dict(overlaying="y", side="right", showgrid=False, color="#5e5e70", zeroline=False),
        barmode="overlay",
        **base,
    )

    return {
        "tension":  fig1.to_json(),
        "bubble":   fig2.to_json(),
        "signal":   fig3.to_json(),
    }
