import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from data_service import filter_data, summarize, get_top_urls, build_charts
from ai_service import extract_intent, stream_report1, stream_report2, generate_suggestions, stream_followup
from scraper import fetch_articles

app = FastAPI(title="Echo Média API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Modèles ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    message: str
    sector: str = "libre"

class FollowupRequest(BaseModel):
    question: str
    sector: str
    keywords: list[str] = []
    history: list[dict] = []

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """
    Pipeline complet :
    1. Extrait l'intention (Haiku)
    2. Filtre les données pandas
    3. Construit les graphiques Plotly
    4. Retourne le résumé + les charts + les URLs top
    Le streaming des rapports est fait via /report1 et /report2.
    """
    intent_data = await extract_intent(req.message, req.sector)
    keywords = intent_data.get("keywords", [])
    sector   = intent_data.get("data_focus", req.sector)

    df = filter_data(sector, keywords)
    if df.empty:
        raise HTTPException(status_code=404, detail="Aucune donnée pour ces filtres.")

    summary = summarize(df)
    charts  = build_charts(df, summary.get("anomaly_months", []))
    urls    = get_top_urls(df, n=3)

    return {
        "intent":   intent_data,
        "summary":  summary,
        "charts":   charts,
        "top_urls": urls,
    }


@app.post("/report1")
async def report1(req: AnalyzeRequest):
    """Stream le Rapport 1 (tendances + anomalies)."""
    intent_data = await extract_intent(req.message, req.sector)
    keywords = intent_data.get("keywords", [])
    sector   = intent_data.get("data_focus", req.sector)

    df      = filter_data(sector, keywords)
    summary = summarize(df)
    intent  = intent_data.get("intent_fr", req.message)

    async def gen():
        async for chunk in stream_report1(summary, intent, sector):
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/report2")
async def report2(req: AnalyzeRequest):
    """Stream le Rapport 2 (enrichissement par articles sources)."""
    intent_data = await extract_intent(req.message, req.sector)
    keywords = intent_data.get("keywords", [])
    sector   = intent_data.get("data_focus", req.sector)

    df      = filter_data(sector, keywords)
    summary = summarize(df)
    intent  = intent_data.get("intent_fr", req.message)
    urls    = get_top_urls(df, n=3)
    articles = await fetch_articles(urls)

    async def gen():
        async for chunk in stream_report2(summary, articles, intent):
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/suggestions")
async def suggestions(req: AnalyzeRequest):
    """Retourne 3 suggestions de questions de suivi."""
    intent_data = await extract_intent(req.message, req.sector)
    keywords = intent_data.get("keywords", [])
    sector   = intent_data.get("data_focus", req.sector)

    df      = filter_data(sector, keywords)
    summary = summarize(df)
    intent  = intent_data.get("intent_fr", req.message)
    suggs   = await generate_suggestions(summary, intent, [])

    return {"suggestions": suggs}


@app.post("/followup")
async def followup(req: FollowupRequest):
    """Stream une réponse à une question de suivi."""
    df      = filter_data(req.sector, req.keywords)
    summary = summarize(df)

    async def gen():
        async for chunk in stream_followup(req.question, summary, req.history):
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ── Frontend statique ─────────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
