import os
import json
from anthropic import AsyncAnthropic
from gdelt_context import SYSTEM_CONTEXT, SYSTEM_CONTEXT_SHORT

client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global client
    if client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY manquante — vérifie ton fichier .env")
        client = AsyncAnthropic(api_key=key)
    return client


# ── Intent ───────────────────────────────────────────────────────────────────

async def extract_intent(message: str, sector: str, is_followup: bool = False) -> dict:
    """Haiku — extrait mots-clés, reformule l'intention, détecte plage de dates et besoin de viz."""
    c = get_client()

    needs_viz_instruction = """
needs_viz : true si la question demande une NOUVELLE analyse de données (nouveau secteur, nouvelle période,
comparaison, "montre-moi", "analyse", "compare", "évolution de") — false si c'est une question
d'interprétation/explication sur ce qui a déjà été montré ("pourquoi", "explique", "que signifie",
"qui sont", "que faire").""" if is_followup else ""

    needs_viz_field = ',\n  "needs_viz": true' if is_followup else ""

    prompt = f"""Secteur actuel : {sector}
Message : "{message}"

JSON uniquement (pas de markdown) :
{{
  "keywords": ["mot1", "mot2"],
  "intent_fr": "Résumé en une phrase",
  "data_focus": "economie|diplomatie|cooperation|conflits|gouvernance|libre",
  "date_from": "YYYYMMDD ou null",
  "date_to":   "YYYYMMDD ou null"{needs_viz_field}
}}

Règles pour data_focus — sois précis, évite "libre" sauf si la question est vraiment générale :
- "economie" : commerce, sanctions, aide économique, investissement, budget, financement, croissance
- "diplomatie" : visites officielles, négociations, accords, relations bilatérales, ambassades
- "cooperation" : aide fournie, partenariats, accords de développement, organisations internationales
- "conflits" : risque, sécurité, menaces, instabilité, violence, tensions, crises, combats, protestations, indicateurs de risque
- "gouvernance" : élections, institutions, politique intérieure, réformes, administration
- "libre" : uniquement si la question couvre plusieurs secteurs sans dominante claire

date_from/date_to : si l'utilisateur mentionne une période (ex: "mars à juillet 2025" → 20250301 / 20250731). Null sinon.{needs_viz_instruction}"""

    r = await c.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=SYSTEM_CONTEXT_SHORT,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return json.loads(r.content[0].text)
    except Exception:
        return {"keywords": [], "intent_fr": message, "data_focus": sector,
                "date_from": None, "date_to": None}


# ── Report 1 — basé sur les descriptions des charts ─────────────────────────

async def stream_report1(chart_description: str, summary: dict, intent: str, sector: str):
    """
    Sonnet — 2 paragraphes max.
    Raisonne à partir de ce que montrent les charts, pas des stats brutes.
    """
    c = get_client()
    prompt = f"""L'utilisateur explore : **{intent}** ({sector})

Voici ce que montrent les visualisations générées :

{chart_description}

Contexte chiffré :
- {summary.get('total_events')} événements · Ton {summary.get('avg_tone'):+.2f} · Goldstein {summary.get('avg_goldstein'):+.2f}
- Anomalies sur : {summary.get('anomaly_months') or 'aucune'}

Rédige un mini-rapport en **2 paragraphes courts** (6 phrases max au total) :
- §1 : Ce que les visuels révèlent sur la dynamique médiatique
- §2 : L'anomalie ou le signal le plus fort — et ce qu'il signifie concrètement

Sois direct. Pas de titre, pas de liste. Parle comme un analyste qui brief un décideur en 30 secondes."""

    async with c.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM_CONTEXT,
        messages=[{"role": "user", "content": prompt}]
    ) as s:
        async for text in s.text_stream:
            yield text


# ── Report 2 — croisement sources ────────────────────────────────────────────

async def stream_report2(summary: dict, articles: list[dict], intent: str,
                         chart_description: str, anomaly_detail: str = ""):
    """Sonnet — 2 paragraphes, croisement articles + explication causale des anomalies."""
    c = get_client()

    accessible = [
        a for a in articles
        if a.get("excerpt") and not a["excerpt"].startswith("[Inaccessible")
    ]
    inaccessible_count = len(articles) - len(accessible)

    articles_text = "\n\n".join(
        f"[{a['title']}]\nSource : {a.get('url','?')}\n{a['excerpt']}"
        for a in accessible
    ) or "Aucun article accessible."

    scraping_note = (
        f"\n⚠ {inaccessible_count} article(s) inaccessibles sur {len(articles)} tentés."
        if inaccessible_count > 0 else ""
    )

    anomaly_block = f"\nDétail période anomalique :\n{anomaly_detail}" if anomaly_detail else ""

    prompt = f"""L'utilisateur explore : **{intent}**

Signal GDELT global :
{chart_description}
{anomaly_block}

Articles sources (ciblés sur la période anomalique si applicable) :{scraping_note}
{articles_text}

Rédige 3 paragraphes courts (8 phrases max au total) :
- §1 : Ce que les articles révèlent sur le POURQUOI des anomalies — événement précis, acteur déclencheur, contexte. Si les articles n'expliquent pas l'anomalie, dis-le franchement.
- §2 : Angle éditorial — qui couvre, depuis où, quels biais. Signale si la couverture est insuffisante pour conclure.
- §3 : Implication concrète pour un décideur + 1 signal à surveiller dans les semaines suivantes. Formule comme un brief de 30 secondes.

Précis, chiffré, sans titre. Si les données ne permettent pas de conclure sur le pourquoi, dis-le explicitement."""

    async with c.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=420,
        system=SYSTEM_CONTEXT,
        messages=[{"role": "user", "content": prompt}]
    ) as s:
        async for text in s.text_stream:
            yield text


# ── Suggestions — basées sur le rapport + intérêt perçu ─────────────────────

async def generate_suggestions(report1_text: str, intent: str, top_themes: list, top_actors: list) -> list[str]:
    """
    Haiku — 3 questions de suivi issues du rapport lui-même.
    Pas des questions génériques — tirées directement de ce qui a été trouvé.
    """
    c = get_client()
    prompt = f"""Intention initiale : {intent}
Thèmes dominants : {top_themes[:4]}
Acteurs clés : {top_actors[:3]}

Rapport produit :
{report1_text[:600]}

Génère 3 questions de suivi PRÉCISES (max 10 mots chacune) que l'utilisateur voudrait naturellement poser après avoir lu ce rapport. Elles doivent être ancrées dans ce qui a été trouvé, pas génériques.

JSON uniquement : ["question1", "question2", "question3"]"""

    r = await c.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        system=SYSTEM_CONTEXT_SHORT,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return json.loads(r.content[0].text)
    except Exception:
        return [
            f"Pourquoi ce pic en {intent[:20]} ?",
            "Quels acteurs dominent cette période ?",
            "Comment évolue le ton sur le reste de l'année ?",
        ]


# ── Follow-up conversationnel ────────────────────────────────────────────────

async def stream_followup(question: str, summary: dict, chart_description: str, history: list[dict]):
    """Sonnet — réponse courte, ancrée dans les données + ce que montrent les charts."""
    c = get_client()

    history_msgs = [{"role": h["role"], "content": h["content"][:350]} for h in history[-6:]]
    history_msgs.append({
        "role": "user",
        "content": f"""{question}

Données disponibles :
{chart_description}

Résumé : {summary.get('total_events')} evt · Ton {summary.get('avg_tone'):+.2f} · Top thèmes : {list(summary.get('top_themes', {}).keys())[:4]}

Réponds en 3-4 phrases max. Précis, chiffré, utile."""
    })

    async with c.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=250,
        system=SYSTEM_CONTEXT,
        messages=history_msgs
    ) as s:
        async for text in s.text_stream:
            yield text
