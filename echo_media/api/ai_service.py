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


async def extract_intent(message: str, sector: str) -> dict:
    """Haiku — rapide, extrait mots-clés et reformule l'intention."""
    c = get_client()
    prompt = f"""Secteur sélectionné : {sector}
Message utilisateur : "{message}"

Analyse et réponds UNIQUEMENT en JSON valide (pas de markdown, pas d'explication) :
{{
  "keywords": ["mot-clé1", "mot-clé2"],
  "intent_fr": "Résumé en une phrase de ce que cherche l'utilisateur",
  "data_focus": "economie|diplomatie|cooperation|conflits|gouvernance|libre"
}}

Les keywords doivent être des termes présents dans les données GDELT (pays, types d'acteurs, types d'événements CAMEO).
Si l'utilisateur ne précise pas de sous-angle, retourne data_focus = secteur fourni."""

    r = await c.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=SYSTEM_CONTEXT_SHORT,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return json.loads(r.content[0].text)
    except Exception:
        return {"keywords": [], "intent_fr": message, "data_focus": sector}


async def stream_report1(summary: dict, intent: str, sector: str):
    """Sonnet — Rapport 1 : tendances, anomalies, interprétation."""
    c = get_client()
    prompt = f"""L'utilisateur explore : **{intent}** (secteur : {sector})

Voici le résumé statistique des données GDELT filtrées :

```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

Rédige un rapport analytique en français (300-400 mots), structuré ainsi :

## Tendances clés
[2-3 observations précises avec chiffres : volume, évolution du ton, stabilité]

## Thèmes dominants
[Ce que révèlent les top thèmes sur la posture internationale autour du Bénin]

## Anomalies détectées
[Analyse des mois signalés dans anomaly_months. Si vide, précise qu'aucune rupture n'est détectée.]

## Lecture stratégique
[Ce que ces signaux médiatiques signifient concrètement pour le secteur analysé — sois direct et utile]

Appuie-toi sur les chiffres. Ne répète pas les données brutes, interprète-les."""

    async with c.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=700,
        system=SYSTEM_CONTEXT,
        messages=[{"role": "user", "content": prompt}]
    ) as s:
        async for text in s.text_stream:
            yield text


async def stream_report2(summary: dict, articles: list[dict], intent: str):
    """Sonnet — Rapport 2 : enrichissement par articles sources."""
    c = get_client()

    articles_text = "\n\n---\n\n".join(
        f"**Source {i+1}** : {a['title']}\nURL : {a['url']}\n{a['excerpt']}"
        for i, a in enumerate(articles)
        if a.get("excerpt") and not a["excerpt"].startswith("[Inaccessible")
    ) or "Aucun article accessible pour enrichissement."

    prompt = f"""L'utilisateur explore : **{intent}**

Résumé GDELT (contexte chiffré) :
- {summary.get('total_events')} événements · Ton moyen : {summary.get('avg_tone')} · Stabilité : {summary.get('avg_goldstein')}
- Top thèmes : {list(summary.get('top_themes', {}).keys())[:5]}
- Anomalies détectées sur : {summary.get('anomaly_months', [])}

Articles sources récupérés :
{articles_text}

Rédige un rapport de croisement (250-350 mots) :

## Ce que disent les médias
[Croise les événements GDELT avec le contenu réel des articles — qu'est-ce qui est couvert, comment ?]

## Explication des irrégularités
[Si des anomalies ont été détectées, les articles sources donnent-ils un contexte ? Qu'est-ce qui s'est passé ?]

## Angle éditorial
[Qui couvre le Bénin ? Quelle est la tonalité dominante des sources ? Y a-t-il un biais géographique ou thématique ?]

Sois direct. Si les articles ne permettent pas de répondre, dis-le clairement."""

    async with c.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=SYSTEM_CONTEXT,
        messages=[{"role": "user", "content": prompt}]
    ) as s:
        async for text in s.text_stream:
            yield text


async def generate_suggestions(summary: dict, intent: str, history: list[dict]) -> list[str]:
    """Haiku — 3 questions de suivi pertinentes."""
    c = get_client()
    top_themes = list(summary.get("top_themes", {}).keys())[:4]
    top_actors = list(summary.get("top_actors", {}).keys())[:3]
    hist = " | ".join(h["content"][:60] for h in history[-3:] if h.get("content"))

    prompt = f"""Contexte : {intent}
Top thèmes dans les données : {top_themes}
Top acteurs : {top_actors}
Historique récent : {hist or "premier échange"}

Génère exactement 3 questions courtes (max 10 mots chacune) pour approfondir l'analyse.
Questions variées : une sur un acteur, une sur une période, une sur un thème.
Réponds UNIQUEMENT avec un JSON array : ["question1", "question2", "question3"]"""

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
            "Quels pays interagissent le plus avec le Bénin ?",
            "Comment évolue la tension au second semestre ?",
            "Quel secteur concentre le plus d'anomalies ?",
        ]


async def stream_followup(question: str, summary: dict, history: list[dict]):
    """Sonnet — réponse conversationnelle à une question de suivi."""
    c = get_client()
    history_msgs = [{"role": h["role"], "content": h["content"][:400]} for h in history[-6:]]
    history_msgs.append({
        "role": "user",
        "content": f"""{question}

Données disponibles (résumé) :
```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```
Réponds en 150-250 mots, analytiquement, avec des chiffres précis."""
    })

    async with c.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=450,
        system=SYSTEM_CONTEXT,
        messages=history_msgs
    ) as s:
        async for text in s.text_stream:
            yield text
