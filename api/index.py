"""
Vercel entrypoint for the Talantis FastAPI backend.

Vercel's rewrite in vercel.json sends every /api/* path here. FastAPI's
internal router then dispatches to the correct endpoint based on the
original path.
"""
import os
import sys

# Make sibling modules importable when running on Vercel
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from atlas import stream_atlas_answer
from database import get_intern_data, get_universities

app = FastAPI(title="Talantis API")

# Open CORS — same-origin in production but useful for local dev / uAgent calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class InsightRequest(BaseModel):
    query: str
    university: str | None = None  # optional context — Atlas can use or ignore


# ────────────────────────────────────────────────────────────────────────────
# Health check — useful for verifying the function is alive on Vercel
# Hit https://<your-domain>/api/health to confirm the deploy works at all
# ────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "talantis-api",
        "env_check": {
            "SUPABASE_URL":      bool(os.environ.get("SUPABASE_URL")),
            "SUPABASE_KEY":      bool(os.environ.get("SUPABASE_KEY")),
            "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        },
    }


# ────────────────────────────────────────────────────────────────────────────
# Frontend data endpoints — used by the bar chart and university dropdown
# ────────────────────────────────────────────────────────────────────────────

@app.get("/api/universities")
def universities():
    return get_universities()


@app.get("/api/companies")
def companies(university: str | None = Query(default=None)):
    return get_intern_data(university)


# ────────────────────────────────────────────────────────────────────────────
# Atlas — the streaming insights endpoint
# Frontend POSTs JSON: {"query": "...", "university": "..."}
# Server returns Server-Sent Events:
#   data: {"text": "..."}    one token of narrative text
#   data: {"tool": "name"}   tool-call notification
#   data: [DONE]              end of stream
# ────────────────────────────────────────────────────────────────────────────

@app.post("/api/insights")
async def insights(body: InsightRequest):
    question = body.query
    if body.university:
        question = (
            f"(Context: the user is currently filtered to {body.university}.) "
            f"{question}"
        )

    # Anti-buffering headers tell intermediate proxies (CDN, browser) to flush
    # SSE chunks as they arrive instead of buffering the whole response.
    headers = {
        "Cache-Control":     "no-cache, no-transform",
        "Connection":        "keep-alive",
        "X-Accel-Buffering": "no",  # disables NGINX/Vercel proxy buffering
    }

    return StreamingResponse(
        stream_atlas_answer(question),
        media_type="text/event-stream",
        headers=headers,
    )
