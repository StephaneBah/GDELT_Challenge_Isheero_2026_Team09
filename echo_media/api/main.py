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

from data_service import filter_data, summarize, get_top_urls, get_anomaly_urls, describe_anomaly_period, build_charts, infer_sector_from_text
from scraper import fetch_articles
from chart_describe import describe_charts
import cache as _cache

# Détection mode démo (pas de clé ou solde épuisé)
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEMO_MODE = not API_KEY or API_KEY.startswith("sk-ant-REMPLACE")

if not DEMO_MODE:
    from ai_service import extract_intent, stream_report1, stream_report2, generate_suggestions, stream_followup
else:
    print("Mode demo active — API Anthropic non disponible")

app = FastAPI(title="Echo Media API")

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

class Report1Request(BaseModel):
    message: str
    sector: str = "libre"
    chart_description: str = ""
    summary: dict = {}
    intent: str = ""

class Report2Request(BaseModel):
    message: str
    sector: str = "libre"
    chart_description: str = ""
    summary: dict = {}
    intent: str = ""
    top_urls: list[str] = []
    anomaly_detail: str = ""

class SuggestionsRequest(BaseModel):
    message: str
    sector: str = "libre"
    report1_text: str = ""
    intent: str = ""
    top_themes: list = []
    top_actors: list = []

class FollowupRequest(BaseModel):
    question: str
    sector: str
    keywords: list[str] = []
    history: list[dict] = []
    chart_description: str = ""
    summary: dict = {}

# ── Helpers ───────────────────────────────────────────────────────────────────

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

class RouteRequest(BaseModel):
    question: str
    sector: str = "libre"

@app.post("/route")
async def route(req: RouteRequest):
    """Haiku — décide si la question nécessite une nouvelle analyse (viz) ou une réponse conversationnelle."""
    if DEMO_MODE:
        return {"needs_viz": False, "intent": {"intent_fr": req.question, "data_focus": req.sector,
                "keywords": [], "date_from": None, "date_to": None, "needs_viz": False}}
    intent_data = await extract_intent(req.question, req.sector, is_followup=True)
    return {"needs_viz": intent_data.get("needs_viz", False), "intent": intent_data}


@app.get("/health")
def health():
    return {"status": "ok", "demo_mode": DEMO_MODE, "cache": _cache.stats()}

@app.post("/cache/clear")
def cache_clear():
    _cache._store.clear()
    return {"cleared": True}


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    if DEMO_MODE:
        from demo_data import DEMO_SUMMARY, DEMO_INTENT
        try:
            df = filter_data(req.sector, [])
            summary = summarize(df)
            charts = build_charts(df, summary.get("anomaly_months", []))
            chart_description = describe_charts(charts, summary)
            urls = get_top_urls(df, n=3)
        except Exception:
            summary = DEMO_SUMMARY
            charts = {}
            chart_description = ""
            urls = []
        return {
            "intent": DEMO_INTENT,
            "summary": summary,
            "charts": charts,
            "chart_description": chart_description,
            "top_urls": urls,
        }

    # Cache hit ?
    cached = _cache.get(req.message, req.sector)
    if cached:
        return cached

    intent_data = await extract_intent(req.message, req.sector)
    keywords  = intent_data.get("keywords", [])
    ai_sector = intent_data.get("data_focus", req.sector)

    if req.sector != "libre":
        # Secteur explicitement choisi par l'utilisateur — priorité absolue
        sector = req.sector
    elif ai_sector and ai_sector != "libre":
        # Haiku a détecté un secteur
        sector = ai_sector
    else:
        # Haiku dit "libre" — fallback détection Python par mots-clés
        sector = infer_sector_from_text(req.message) or "libre"

    print(f"[analyze] req.sector={req.sector!r} ai={ai_sector!r} py_infer={infer_sector_from_text(req.message)!r} → final={sector!r} kw={keywords}")
    date_from = intent_data.get("date_from")
    date_to   = intent_data.get("date_to")

    df = filter_data(sector, keywords, date_from=date_from, date_to=date_to)
    if df.empty:
        raise HTTPException(status_code=404, detail="Aucune donnée pour ces filtres.")

    summary           = summarize(df)
    anomaly_months    = summary.get("anomaly_months", [])
    charts            = build_charts(df, anomaly_months)
    chart_description = describe_charts(charts, summary)
    urls              = get_anomaly_urls(df, anomaly_months, n=10)
    anomaly_detail    = describe_anomaly_period(df, anomaly_months)

    result = {
        "intent": intent_data,
        "summary": summary,
        "charts": charts,
        "chart_description": chart_description,
        "top_urls": urls,
        "anomaly_detail": anomaly_detail,
    }
    _cache.set(req.message, req.sector, result)
    return result


@app.post("/report1")
async def report1(req: Report1Request):
    if DEMO_MODE:
        from demo_data import DEMO_REPORT1
        return StreamingResponse(_stream_text(DEMO_REPORT1), media_type="text/event-stream")

    # chart_description et summary fournis directement par le frontend
    # (déjà calculés dans /analyze)
    chart_description = req.chart_description
    summary           = req.summary
    intent            = req.intent or req.message
    sector            = req.sector

    # Fallback si le frontend n'a pas transmis les données
    if not chart_description or not summary:
        intent_data       = await extract_intent(req.message, req.sector)
        keywords          = intent_data.get("keywords", [])
        sector            = req.sector if req.sector != "libre" else (intent_data.get("data_focus") or infer_sector_from_text(req.message) or "libre")
        date_from         = intent_data.get("date_from")
        date_to           = intent_data.get("date_to")
        df                = filter_data(sector, keywords, date_from=date_from, date_to=date_to)
        summary           = summarize(df)
        charts            = build_charts(df, summary.get("anomaly_months", []))
        chart_description = describe_charts(charts, summary)
        intent            = intent_data.get("intent_fr", req.message)

    async def gen():
        async for chunk in stream_report1(chart_description, summary, intent, sector):
            yield _sse(chunk)
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/report2")
async def report2(req: Report2Request):
    if DEMO_MODE:
        from demo_data import DEMO_REPORT2
        return StreamingResponse(_stream_text(DEMO_REPORT2), media_type="text/event-stream")

    chart_description = req.chart_description
    summary           = req.summary
    intent            = req.intent or req.message
    top_urls          = req.top_urls
    anomaly_detail    = req.anomaly_detail

    if not chart_description or not summary:
        intent_data       = await extract_intent(req.message, req.sector)
        keywords          = intent_data.get("keywords", [])
        sector            = req.sector if req.sector != "libre" else (intent_data.get("data_focus") or infer_sector_from_text(req.message) or "libre")
        date_from         = intent_data.get("date_from")
        date_to           = intent_data.get("date_to")
        df                = filter_data(sector, keywords, date_from=date_from, date_to=date_to)
        summary           = summarize(df)
        anomaly_months    = summary.get("anomaly_months", [])
        charts            = build_charts(df, anomaly_months)
        chart_description = describe_charts(charts, summary)
        intent            = intent_data.get("intent_fr", req.message)
        top_urls          = get_anomaly_urls(df, anomaly_months, n=10)
        anomaly_detail    = describe_anomaly_period(df, anomaly_months)

    articles = await fetch_articles(top_urls)

    async def gen():
        async for chunk in stream_report2(summary, articles, intent, chart_description, anomaly_detail):
            yield _sse(chunk)
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/suggestions")
async def suggestions(req: SuggestionsRequest):
    if DEMO_MODE:
        from demo_data import DEMO_SUGGESTIONS
        return {"suggestions": DEMO_SUGGESTIONS}

    report1_text = req.report1_text
    intent       = req.intent or req.message
    top_themes   = req.top_themes
    top_actors   = req.top_actors

    if not top_themes:
        intent_data = await extract_intent(req.message, req.sector)
        keywords    = intent_data.get("keywords", [])
        sector      = intent_data.get("data_focus", req.sector)
        date_from   = intent_data.get("date_from")
        date_to     = intent_data.get("date_to")
        df          = filter_data(sector, keywords, date_from=date_from, date_to=date_to)
        summary     = summarize(df)
        intent      = intent_data.get("intent_fr", req.message)
        top_themes  = list(summary.get("top_themes", {}).keys())
        top_actors  = list(summary.get("top_actors", {}).keys())

    suggs = await generate_suggestions(report1_text, intent, top_themes, top_actors)
    return {"suggestions": suggs}


@app.post("/followup")
async def followup(req: FollowupRequest):
    if DEMO_MODE:
        from demo_data import DEMO_FOLLOWUP
        return StreamingResponse(_stream_text(DEMO_FOLLOWUP), media_type="text/event-stream")

    chart_description = req.chart_description
    summary           = req.summary

    if not chart_description or not summary:
        df                = filter_data(req.sector, req.keywords)
        summary           = summarize(df)
        charts            = build_charts(df, summary.get("anomaly_months", []))
        chart_description = describe_charts(charts, summary)

    async def gen():
        async for chunk in stream_followup(req.question, summary, chart_description, req.history):
            yield _sse(chunk)
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ── Frontend statique ─────────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
