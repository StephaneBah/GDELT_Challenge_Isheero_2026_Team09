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

ABSTRACT_KEYWORDS = {
    "risque", "risques", "sécurité", "securite", "instabilité", "instabilite",
    "crise", "crises", "indicateur", "indicateurs", "analyse", "tendance",
    "tendances", "performance", "bilan", "résultat", "resultat", "impact",
    "signal", "signaux",
}

SECTOR_FLAG_MAP = {
    "economie": "is_economic",
    "diplomatie": "is_diplomatic",
    "cooperation": "is_cooperation",
    "conflits": "is_conflict",
    "gouvernance": "is_governance",
}

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


def _normalize_keywords(keywords: list[str] | None) -> list[str]:
    if not keywords:
        return []
    out = []
    for kw in keywords:
        if not kw:
            continue
        kw_clean = str(kw).strip().lower()
        if kw_clean:
            out.append(kw_clean)
    # Preserve order while removing duplicates
    seen = set()
    unique = []
    for kw in out:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique


def _split_keywords(keywords: list[str]) -> tuple[list[str], list[str]]:
    kw_lower = _normalize_keywords(keywords)
    concrete_kw = [k for k in kw_lower if k not in ABSTRACT_KEYWORDS]
    abstract_kw = [k for k in kw_lower if k in ABSTRACT_KEYWORDS]
    return concrete_kw, abstract_kw


def infer_sector_from_keywords(keywords: list[str] | None) -> str | None:
    words = set(_normalize_keywords(keywords))
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
        concrete_kw, _ = _split_keywords(keywords)
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


def rank_urls(
    df: pd.DataFrame,
    urls: list[str] | None = None,
    keywords: list[str] | None = None,
    sector_hint: str | None = None,
    n: int = 10,
    extra_keywords: list[str] | None = None,
) -> list[str]:
    """Classe les URLs par pertinence (mots-clés + mentions) sur un slice de données."""
    if "SOURCEURL" not in df.columns:
        return []

    base = df[df["SOURCEURL"].notna()]
    if urls:
        base = base[base["SOURCEURL"].isin(urls)]
    if base.empty:
        return []

    base = base.copy()
    base["score"] = pd.to_numeric(base.get("NumMentions", 0), errors="coerce").fillna(0)

    kw_all: list[str] = []
    if keywords:
        kw_all.extend(keywords)
    if extra_keywords:
        kw_all.extend(extra_keywords)

    concrete_kw, abstract_kw = _split_keywords(kw_all)
    for kw in concrete_kw:
        mask = (
            base["event_root_label"].str.contains(kw, case=False, na=False)
            | base["actor1_country"].str.contains(kw, case=False, na=False)
            | base["actor2_country"].str.contains(kw, case=False, na=False)
            | base["actor1_type"].str.contains(kw, case=False, na=False)
        )
        base.loc[mask, "score"] += 3

    sector = sector_hint or infer_sector_from_keywords(abstract_kw) or infer_sector_from_keywords(concrete_kw)
    if sector:
        flag = SECTOR_FLAG_MAP.get(sector)
        if flag in base.columns:
            base.loc[base[flag], "score"] += 2

    ranked = base.groupby("SOURCEURL")["score"].sum().sort_values(ascending=False)
    return ranked.head(n).index.tolist()


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


def get_anomaly_urls(
    df: pd.DataFrame,
    anomaly_months: list[str],
    n: int = 10,
    keywords: list[str] | None = None,
    sector: str | None = None,
) -> list[str]:
    """URLs ciblées sur les mois anomaliques — pour expliquer les pics/creux."""
    if not anomaly_months:
        ranked = rank_urls(df, keywords=keywords, sector_hint=sector, n=n)
        return ranked or get_top_urls(df, n)
    mask = df["month"].astype(str).apply(
        lambda m: any(m[:7] in a[:7] for a in anomaly_months)
    )
    sub = df[mask]
    if sub.empty:
        ranked = rank_urls(df, keywords=keywords, sector_hint=sector, n=n)
        return ranked or get_top_urls(df, n)
    top_labels = sub["event_root_label"].value_counts().head(5).index.tolist()
    ranked = rank_urls(sub, keywords=keywords, sector_hint=sector, n=n, extra_keywords=top_labels)
    return ranked or get_top_urls(sub, n)


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


DEFAULT_CHARTS = ["tension", "signal", "bubble", "partners"]
ALLOWED_CHARTS = {"tension", "signal", "bubble", "partners", "themes", "actors"}
SECTOR_CHART_DEFAULTS = {
    "economie":    ["signal", "tension", "themes"],
    "diplomatie":  ["partners", "signal", "bubble"],
    "cooperation": ["partners", "bubble", "signal"],
    "conflits":    ["tension", "signal", "bubble"],
    "gouvernance": ["tension", "themes", "signal"],
    "libre":       DEFAULT_CHARTS,
}


def select_charts(
    df: pd.DataFrame,
    sector: str,
    requested: list[str] | None = None,
    min_charts: int = 3,
) -> list[str]:
    """Sélectionne des charts adaptés au secteur et aux données filtrées."""
    if df.empty:
        return []

    req = [c for c in (requested or []) if c in ALLOWED_CHARTS]
    defaults = SECTOR_CHART_DEFAULTS.get(sector.lower(), DEFAULT_CHARTS)
    order = req if req else list(defaults)

    month_count = df["month"].nunique() if "month" in df.columns else 0
    if "event_date" in df.columns and df["event_date"].notna().any():
        span_days = (df["event_date"].max() - df["event_date"].min()).days
    else:
        span_days = 0

    available = set()
    if month_count >= 1:
        available.add("tension")
    if month_count >= 2 and span_days >= 30:
        available.add("signal")

    if "event_root_label" in df.columns and df["event_root_label"].nunique() >= 2:
        available.update({"bubble", "themes"})

    if "actor1_country" in df.columns:
        partners = df[~df["actor1_country"].str.lower().isin(["bénin", "benin", "inconnu", ""])]
        if not partners.empty:
            available.add("partners")

    if "actor1_type" in df.columns:
        actors = df[df["actor1_type"].str.lower().ne("inconnu")]
        if not actors.empty:
            available.add("actors")

    selected = [c for c in order if c in available]
    if len(selected) < min_charts:
        fallback = list(defaults) + ["themes", "actors", "partners", "bubble", "tension", "signal"]
        for c in fallback:
            if c in available and c not in selected:
                selected.append(c)
            if len(selected) >= min_charts:
                break

    return selected

def build_charts(df: pd.DataFrame, anomaly_months: list[str],
                 requested: list[str] | None = None) -> dict:
    """Construit uniquement les charts demandés (liste validée)."""
    to_build = set(requested) if requested else set(DEFAULT_CHARTS)
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

    charts = {}

    # ── tension ───────────────────────────────────────────────────────────────
    if "tension" in to_build:
        colors = [
            "#d45050" if any(str(row["month"])[:7] in a for a in anomaly_months) else "#1a9da6"
            for _, row in monthly.iterrows()
        ]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly["ms"], y=monthly["avg_tension"].round(1),
            marker_color=colors,
            hovertemplate="<b>%{x}</b><br>Tension : %{y:.0f}/100<extra></extra>",
        ))
        mean_t = monthly["avg_tension"].mean()
        fig.add_hline(y=mean_t, line_dash="dot", line_color="rgba(255,255,255,0.2)",
                      annotation_text=f"moy. {mean_t:.0f}", annotation_font_color="#5e5e70",
                      annotation_position="right")
        fig.update_layout(title="Indice de tension médiatique", showlegend=False,
                          yaxis_range=[0, 100], **base)
        charts["tension"] = fig.to_json()

    # ── bubble ────────────────────────────────────────────────────────────────
    if "bubble" in to_build:
        cs = (
            df.groupby("event_root_label")
            .agg(volume=("GLOBALEVENTID", "count"), tone=("AvgTone", "mean"),
                 stability=("GoldsteinScale", "mean"))
            .reset_index().query("volume >= 10").sort_values("volume", ascending=False).head(12)
        )
        fig = go.Figure()
        fig.add_vrect(x0=-20, x1=0, fillcolor="rgba(212,80,80,0.03)", line_width=0)
        fig.add_vrect(x0=0,  x1=20, fillcolor="rgba(41,185,125,0.03)", line_width=0)
        fig.add_hline(y=0, line_color="rgba(255,255,255,0.1)", line_dash="dot")
        fig.add_vline(x=0, line_color="rgba(255,255,255,0.1)", line_dash="dot")
        fig.add_trace(go.Scatter(
            x=cs["tone"].round(2), y=cs["stability"].round(2),
            mode="markers+text", text=cs["event_root_label"],
            textposition="top center", textfont=dict(size=8, color="#9a9090"),
            marker=dict(
                size=(cs["volume"] / cs["volume"].max() * 50 + 10),
                color=cs["stability"],
                colorscale=[[0,"#d45050"],[0.5,"#c8862a"],[1,"#29b97d"]],
                cmin=-5, cmax=5, opacity=0.8,
                line=dict(width=1, color="rgba(255,255,255,0.1)"),
            ),
            hovertemplate="<b>%{text}</b><br>Ton : %{x}<br>Stabilité : %{y}<br>Volume : %{customdata}<extra></extra>",
            customdata=cs["volume"],
        ))
        fig.update_layout(title="Catégories — Perception vs Stabilité", showlegend=False,
                          xaxis_title="Ton médiatique →", yaxis_title="Stabilité →", **base)
        charts["bubble"] = fig.to_json()

    # ── signal ────────────────────────────────────────────────────────────────
    if "signal" in to_build:
        tone_std = monthly["avg_tone"].std()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(monthly["ms"]) + list(monthly["ms"])[::-1],
            y=list((monthly["avg_tone"] + tone_std).round(2)) + list((monthly["avg_tone"] - tone_std).round(2))[::-1],
            fill="toself", fillcolor="rgba(26,157,166,0.05)", line_width=0,
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Bar(
            x=monthly["ms"], y=monthly["count"],
            name="Volume", marker_color="rgba(200,134,42,0.2)",
            yaxis="y2", hovertemplate="%{y} événements<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=monthly["ms"], y=monthly["avg_tone"].round(2),
            name="Ton", line=dict(color="#1a9da6", width=2),
            mode="lines+markers", marker=dict(size=4),
            hovertemplate="Ton : %{y:.2f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=monthly["ms"], y=monthly["avg_gold"].round(2),
            name="Stabilité", line=dict(color="#c8862a", width=2, dash="dash"),
            mode="lines", hovertemplate="Goldstein : %{y:.2f}<extra></extra>",
        ))
        fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.1)")
        fig.update_layout(
            title="Signal médiatique mensuel",
            yaxis2=dict(overlaying="y", side="right", showgrid=False, color="#5e5e70", zeroline=False),
            barmode="overlay", **base,
        )
        charts["signal"] = fig.to_json()

    # ── partners ──────────────────────────────────────────────────────────────
    if "partners" in to_build:
        p = (
            df[~df["actor1_country"].str.lower().isin(["bénin", "benin", "inconnu", ""])]
            ["actor1_country"].value_counts().head(12).reset_index()
        )
        p.columns = ["country", "count"]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=p["count"], y=p["country"], orientation="h",
            marker=dict(color=p["count"],
                        colorscale=[[0,"#1a3a3d"],[0.5,"#1a9da6"],[1,"#29b97d"]],
                        showscale=False),
            hovertemplate="<b>%{y}</b> — %{x} événements<extra></extra>",
        ))
        fig.update_layout(
            title="Principaux pays partenaires", showlegend=False,
            yaxis=dict(autorange="reversed", showgrid=False, zeroline=False,
                       color="#9a9090", tickfont=dict(size=10)),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                       zeroline=False, color="#5e5e70"),
            **{k: v for k, v in base.items() if k not in ("xaxis","yaxis","hovermode")},
            hovermode="y unified",
        )
        charts["partners"] = fig.to_json()

    # ── themes ────────────────────────────────────────────────────────────────
    if "themes" in to_build:
        th = df["event_root_label"].value_counts().head(10).reset_index()
        th.columns = ["theme", "count"]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=th["count"], y=th["theme"], orientation="h",
            marker=dict(color=th["count"],
                        colorscale=[[0,"#1a3a3d"],[0.5,"#c8862a"],[1,"#f0a500"]],
                        showscale=False),
            hovertemplate="<b>%{y}</b> — %{x} événements<extra></extra>",
        ))
        fig.update_layout(
            title="Thèmes dominants", showlegend=False,
            yaxis=dict(autorange="reversed", showgrid=False, zeroline=False,
                       color="#9a9090", tickfont=dict(size=10)),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                       zeroline=False, color="#5e5e70"),
            **{k: v for k, v in base.items() if k not in ("xaxis","yaxis","hovermode")},
            hovermode="y unified",
        )
        charts["themes"] = fig.to_json()

    # ── actors ────────────────────────────────────────────────────────────────
    if "actors" in to_build:
        ac = df["actor1_type"].value_counts().head(10).reset_index()
        ac.columns = ["actor", "count"]
        ac = ac[ac["actor"] != "Inconnu"]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ac["count"], y=ac["actor"], orientation="h",
            marker=dict(color=ac["count"],
                        colorscale=[[0,"#1a3a3d"],[0.5,"#7b5ea7"],[1,"#a78bfa"]],
                        showscale=False),
            hovertemplate="<b>%{y}</b> — %{x} événements<extra></extra>",
        ))
        fig.update_layout(
            title="Types d'acteurs impliqués", showlegend=False,
            yaxis=dict(autorange="reversed", showgrid=False, zeroline=False,
                       color="#9a9090", tickfont=dict(size=10)),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                       zeroline=False, color="#5e5e70"),
            **{k: v for k, v in base.items() if k not in ("xaxis","yaxis","hovermode")},
            hovermode="y unified",
        )
        charts["actors"] = fig.to_json()

    return charts
