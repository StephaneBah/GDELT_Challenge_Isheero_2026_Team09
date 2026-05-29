"""
Transforme les données de chaque chart en prose structurée pour le LLM.
Décrit uniquement les charts effectivement construits.
"""
import statistics


def describe_charts(charts: dict, summary: dict) -> str:
    """Retourne une description textuelle des charts effectivement présents."""
    parts = []
    monthly = summary.get("monthly_evolution", [])
    months_lbl = [m["month"][:7] for m in monthly]

    # ── tension ───────────────────────────────────────────────────────────────
    if "tension" in charts and monthly:
        vals = [m["avg_tension"] for m in monthly if m.get("avg_tension") is not None]
        if vals:
            mean_t = statistics.mean(vals)
            anomalies = summary.get("anomaly_months", [])
            peaks = [
                f"{months_lbl[i]} → {vals[i]:.0f}/100"
                for i in range(len(vals))
                if any(months_lbl[i] in a for a in anomalies)
            ]
            trend = "hausse" if vals[-1] > vals[0] else "baisse" if vals[-1] < vals[0] else "stable"
            desc = f"TENSION MENSUELLE — moyenne {mean_t:.0f}/100, tendance {trend}."
            desc += f" Pics anomaliques : {', '.join(peaks)}." if peaks else " Aucune anomalie significative."
            parts.append(desc)

    # ── bubble ────────────────────────────────────────────────────────────────
    if "bubble" in charts:
        top_themes = summary.get("top_themes", {})
        avg_tone = summary.get("avg_tone", 0)
        avg_gold = summary.get("avg_goldstein", 0)
        if top_themes:
            top3 = list(top_themes.items())[:3]
            top3_str = ", ".join(f'"{k}" ({v} evt)' for k, v in top3)
            quadrant = (
                "favorable et stable"    if avg_tone > 0 and avg_gold > 1 else
                "défavorable mais stable" if avg_tone < 0 and avg_gold > 1 else
                "favorable mais instable" if avg_tone > 0 and avg_gold < 0 else
                "défavorable et instable"
            )
            parts.append(
                f"PERCEPTION × STABILITÉ — quadrant '{quadrant}' "
                f"(ton {avg_tone:+.2f}, Goldstein {avg_gold:+.2f}). "
                f"Thèmes dominants : {top3_str}."
            )

    # ── signal ────────────────────────────────────────────────────────────────
    if "signal" in charts and monthly:
        vol_vals  = [m["count"]    for m in monthly if m.get("count")]
        tone_vals = [m["avg_tone"] for m in monthly if m.get("avg_tone") is not None]
        if vol_vals and tone_vals:
            max_v = vol_vals.index(max(vol_vals))
            min_t = tone_vals.index(min(tone_vals))
            parts.append(
                f"SIGNAL MÉDIATIQUE — Volume max : {months_lbl[max_v]} ({max(vol_vals)} evt). "
                f"Ton le plus négatif : {months_lbl[min_t]} ({min(tone_vals):+.2f}). "
                f"Coopération {summary.get('coop_pct', 0)}% vs Conflits {summary.get('conflict_pct', 0)}%."
            )

    # ── partners ──────────────────────────────────────────────────────────────
    if "partners" in charts:
        top_actors = summary.get("top_actors", {})
        if top_actors:
            top5 = list(top_actors.items())[:5]
            top5_str = ", ".join(f"{k} ({v} evt)" for k, v in top5)
            parts.append(f"PARTENAIRES PRINCIPAUX — {top5_str}.")

    # ── themes ────────────────────────────────────────────────────────────────
    if "themes" in charts:
        top_themes = summary.get("top_themes", {})
        if top_themes:
            top5 = list(top_themes.items())[:5]
            top5_str = ", ".join(f'"{k}" ({v})' for k, v in top5)
            parts.append(f"THÈMES DOMINANTS — {top5_str}.")

    # ── actors ────────────────────────────────────────────────────────────────
    if "actors" in charts:
        parts.append(
            f"TYPES D'ACTEURS — coopération {summary.get('coop_pct',0)}%, "
            f"conflits {summary.get('conflict_pct',0)}%, "
            f"économique {summary.get('economic_pct',0)}%."
        )

    return "\n".join(parts) if parts else "Données insuffisantes pour description."
