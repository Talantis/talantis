import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from atlas import stream_atlas_answer
from database import get_intern_data, get_universities

app = FastAPI(title="Talantis API")

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
# Frontend data endpoints — used by the Recharts bar chart
# ────────────────────────────────────────────────────────────────────────────

@app.get("/api/universities")
def universities():
    return get_universities()


@app.get("/api/companies")
def companies(university: str | None = Query(default=None)):
    return get_intern_data(university)


# ────────────────────────────────────────────────────────────────────────────
# Atlas — the Talent Intelligence Model
# Uses the new tool-use orchestrator (atlas.py + tools.py)
# ────────────────────────────────────────────────────────────────────────────

@app.post("/api/insights")
async def insights(body: InsightRequest):
    """
    The Atlas streaming endpoint. Frontend consumes this via EventSource:

      const es = new EventSource('/api/insights', { method: 'POST', body: ... });
      es.onmessage = (e) => { append(JSON.parse(e.data).text); };

    Each event is one of:
      { "text": "..." }    narrative chunk
      { "tool": "name" }   tool-call notification (for UX/loading state)
      [DONE]               end of stream
    """
    # Augment the user's question with optional university context
    question = body.query
    if body.university:
        question = f"(Context: the user is currently filtered to {body.university}.) {question}"

    return StreamingResponse(
        stream_atlas_answer(question),
        media_type="text/event-stream",
    )
