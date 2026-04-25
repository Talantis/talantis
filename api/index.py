"""
Vercel entrypoint for the Talantis FastAPI backend.

Vercel's rewrite in vercel.json sends every /api/* path here. FastAPI's
internal router then dispatches to the correct endpoint based on the
original path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from atlas import stream_atlas_answer
from database import get_intern_data, get_universities

app = FastAPI(title="Talantis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ════════════════════════════════════════════════════════════════════════════

class ChatTurn(BaseModel):
    """One message in the conversation. role is 'user' or 'assistant'."""
    role: str
    content: str


class InsightRequest(BaseModel):
    """
    Atlas insights request.

    The frontend now sends the full conversation history on every turn —
    Atlas itself is stateless. This keeps the architecture serverless-friendly
    (no per-session storage) and lets the frontend persist transcripts in
    localStorage if it wants to.

    Fields:
      query      — the new user message (the latest turn)
      history    — prior conversation turns, oldest-first; empty for the first
                   message. Only role + content text is needed; tool-use
                   bookkeeping doesn't carry across turns.
      university — optional UI filter context, prepended to the new query
    """
    query: str
    history: list[ChatTurn] = Field(default_factory=list)
    university: str | None = None


# ────────────────────────────────────────────────────────────────────────────
# Health check
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
# Frontend data endpoints
# ────────────────────────────────────────────────────────────────────────────

@app.get("/api/universities")
def universities():
    return get_universities()


@app.get("/api/companies")
def companies(university: str | None = Query(default=None)):
    return get_intern_data(university)


# ────────────────────────────────────────────────────────────────────────────
# Atlas — streaming insights endpoint with conversation history
# ────────────────────────────────────────────────────────────────────────────

@app.post("/api/insights")
async def insights(body: InsightRequest):
    # Atlas reasons from the conversation itself, not from the bar chart's
    # university dropdown. The dropdown is a separate UI filter for the
    # chart — feeding it into Atlas would constrain the agent unnecessarily
    # ("filtered to UCLA" overriding a user's "what about Berkeley?" follow-up).
    latest = body.query

    # Convert ChatTurn → plain dict for the orchestrator
    history = [{"role": t.role, "content": t.content} for t in body.history]

    headers = {
        "Cache-Control":     "no-cache, no-transform",
        "Connection":        "keep-alive",
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(
        stream_atlas_answer(latest, history=history),
        media_type="text/event-stream",
        headers=headers,
    )