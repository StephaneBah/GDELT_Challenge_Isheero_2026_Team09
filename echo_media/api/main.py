import json
import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from data_service import filter_data, summarize, get_top_urls, build_charts
from scraper import fetch_articles

# Détection mode démo (pas de clé ou solde épuisé)
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEMO_MODE = not API_KEY or API_KEY.startswith("sk-ant-REMPLACE")

if not DEMO_MODE:
    from ai_service import extract_intent, stream_report1, stream_report2, generate_suggestions, stream_followup
else:
    print("⚡ Mode démo activé — API Anthropic non disponible")

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

# ── Helpers démo ─────────────────────────────────────────────────────────────

def _sse(text: str) -> str:
    return f"data: {json.dumps({'text': text})}\n\n"

async def _stream_text(text: str, chunk_size: int = 6):
    """Simule un streaming token par token pour la démo."""
    words = text.split(" ")
    buf = ""
    for i, word in enumerate(words):
        buf += word + " "
        if len(buf) >= chunk_size or i == len(words) - 1:
            yield _sse(buf)
            buf = ""
            await asyncio.sleep(0.02)
    yield "data: [DONE]\n\n"

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "demo_mode": DEMO_MODE}


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    if DEMO_MODE:
        from demo_data import DEMO_SUMMARY, DEMO_INTENT
        # Génère quand même de vrais charts depuis les données
        try:
            df = filter_data(req.sector, [])
            summary = summarize(df)
            charts = build_charts(df, summary.get("anomaly_months", []))
            urls = get_top_urls(df, n=3)
        except Exception:
            summary = DEMO_SUMMARY
            charts = {}
            urls = []
        return {"intent": DEMO_INTENT, "summary": summary, "charts": charts, "top_urls": urls}

    intent_data = await extract_intent(req.message, req.sector)
    keywords = intent_data.get("keywords", [])
    sector   = intent_data.get("data_focus", req.sector)

    df = filter_data(sector, keywords)
    if df.empty:
        raise HTTPException(status_code=404, detail="Aucune donnée pour ces filtres.")

    summary = summarize(df)
    charts  = build_charts(df, summary.get("anomaly_months", []))
    urls    = get_top_urls(df, n=3)

    return {"intent": intent_data, "summary": summary, "charts": charts, "top_urls": urls}


@app.post("/report1")
async def report1(req: AnalyzeRequest):
    if DEMO_MODE:
        from demo_data import DEMO_REPORT1
        return StreamingResponse(_stream_text(DEMO_REPORT1), media_type="text/event-stream")

    intent_data = await extract_intent(req.message, req.sector)
    keywords = intent_data.get("keywords", [])
    sector   = intent_data.get("data_focus", req.sector)
    df       = filter_data(sector, keywords)
    summary  = summarize(df)
    intent   = intent_data.get("intent_fr", req.message)

    async def gen():
        async for chunk in stream_report1(summary, intent, sector):
            yield _sse(chunk)
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/report2")
async def report2(req: AnalyzeRequest):
    if DEMO_MODE:
        from demo_data import DEMO_REPORT2
        return StreamingResponse(_stream_text(DEMO_REPORT2), media_type="text/event-stream")

    intent_data = await extract_intent(req.message, req.sector)
    keywords = intent_data.get("keywords", [])
    sector   = intent_data.get("data_focus", req.sector)
    df       = filter_data(sector, keywords)
    summary  = summarize(df)
    intent   = intent_data.get("intent_fr", req.message)
    urls     = get_top_urls(df, n=3)
    articles = await fetch_articles(urls)

    async def gen():
        async for chunk in stream_report2(summary, articles, intent):
            yield _sse(chunk)
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/suggestions")
async def suggestions(req: AnalyzeRequest):
    if DEMO_MODE:
        from demo_data import DEMO_SUGGESTIONS
        return {"suggestions": DEMO_SUGGESTIONS}

    intent_data = await extract_intent(req.message, req.sector)
    keywords = intent_data.get("keywords", [])
    sector   = intent_data.get("data_focus", req.sector)
    df       = filter_data(sector, keywords)
    summary  = summarize(df)
    intent   = intent_data.get("intent_fr", req.message)
    suggs    = await generate_suggestions(summary, intent, [])
    return {"suggestions": suggs}


@app.post("/followup")
async def followup(req: FollowupRequest):
    if DEMO_MODE:
        from demo_data import DEMO_FOLLOWUP
        return StreamingResponse(_stream_text(DEMO_FOLLOWUP), media_type="text/event-stream")

    df      = filter_data(req.sector, req.keywords)
    summary = summarize(df)

    async def gen():
        async for chunk in stream_followup(req.question, summary, req.history):
            yield _sse(chunk)
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ── Frontend statique ─────────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
