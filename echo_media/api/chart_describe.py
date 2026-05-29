"""
Transforme les données de chaque chart en prose structurée pour le LLM.
Le LLM raisonne sur des chiffres exacts — pas sur une image, pas sur du JSON brut.
"""
import json
import statistics


def describe_charts(charts: dict, summary: dict) -> str:
    """Retourne une description textuelle concise de ce que montrent les 3 charts."""
    parts = []

    # ── 1. Tension mensuelle ──────────────────────────────────────────────────
    monthly = summary.get("monthly_evolution", [])
    if monthly:
        vals = [m["avg_tension"] for m in monthly if m.get("avg_tension") is not None]
        months_lbl = [m["month"][:7] for m in monthly]
        if vals:
            mean_t = statistics.mean(vals)
            anomalies = summary.get("anomaly_months", [])
            peaks = [
                f"{months_lbl[i]} → {vals[i]:.0f}/100"
                for i, v in enumerate(vals)
                if any(months_lbl[i] in a for a in anomalies)
            ]
            trend = "hausse" if vals[-1] > vals[0] else "baisse" if vals[-1] < vals[0] else "stable"

            desc = f"TENSION MENSUELLE — moyenne {mean_t:.0f}/100, tendance {trend}."
            if peaks:
                desc += f" Pics anomaliques : {', '.join(peaks)}."
            else:
                desc += " Aucune anomalie significative détectée."
            parts.append(desc)

    # ── 2. Bubble Perception × Stabilité ─────────────────────────────────────
    top_themes = summary.get("top_themes", {})
    avg_tone = summary.get("avg_tone", 0)
    avg_gold = summary.get("avg_goldstein", 0)
    if top_themes:
        top3 = list(top_themes.items())[:3]
        top3_str = ", ".join(f'"{k}" ({v} evt)' for k, v in top3)
        quadrant = (
            "favorable et stable" if avg_tone > 0 and avg_gold > 1 else
            "défavorable mais stable" if avg_tone < 0 and avg_gold > 1 else
            "favorable mais instable" if avg_tone > 0 and avg_gold < 0 else
            "défavorable et instable"
        )
        parts.append(
            f"PERCEPTION × STABILITÉ — Le Bénin se positionne dans le quadrant '{quadrant}' "
            f"(ton {avg_tone:+.2f}, Goldstein {avg_gold:+.2f}). "
            f"Thèmes dominant la couverture : {top3_str}."
        )

    # ── 3. Signal médiatique ──────────────────────────────────────────────────
    if monthly:
        vol_vals = [m["count"] for m in monthly if m.get("count")]
        tone_vals = [m["avg_tone"] for m in monthly if m.get("avg_tone") is not None]
        if vol_vals and tone_vals:
            max_vol_idx = vol_vals.index(max(vol_vals))
            min_tone_idx = tone_vals.index(min(tone_vals))
            parts.append(
                f"SIGNAL MÉDIATIQUE — Volume max : {months_lbl[max_vol_idx]} ({max(vol_vals)} evt). "
                f"Ton le plus négatif : {months_lbl[min_tone_idx]} ({min(tone_vals):+.2f}). "
                f"Coopération {summary.get('coop_pct', 0)}% vs Conflits {summary.get('conflict_pct', 0)}%."
            )

    return "\n".join(parts) if parts else "Données visuelles insuffisantes pour description."
