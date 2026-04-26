"""
Vercel entrypoint for the Talantis FastAPI backend.

Vercel's rewrite in vercel.json sends every /api/* path here. FastAPI's
internal router then dispatches to the correct endpoint based on the
original path.
"""
import hashlib
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from atlas import stream_atlas_answer
from database import (
    get_intern_data,
    get_universities,
    insert_internship,
    slug_for_company,
    slug_for_university,
    upload_offer_letter,
)

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
def companies(
    university: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=2021, le=2025),
):
    return get_intern_data(university, year)


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


# ────────────────────────────────────────────────────────────────────────────
# Submission — user-contributed internship records
# ────────────────────────────────────────────────────────────────────────────

ALLOWED_EXTS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_BYTES = 10 * 1024 * 1024


@app.post("/api/submit")
async def submit_internship(
    email:      str = Form(...),
    university: str = Form(...),
    company:    str = Form(...),
    roleTitle:  str = Form(...),
    category:   str = Form(...),
    year:       str = Form(...),
    season:     str = Form(...),
    offer_letter: UploadFile | None = File(default=None),
):
    import traceback
    step = "init"
    try:
        step = "lookup_university"
        uni_slug = slug_for_university(university)
        if not uni_slug:
            raise HTTPException(400, f"Unknown university: {university}")

        step = "lookup_company"
        co_slug = slug_for_company(company)
        if not co_slug:
            raise HTTPException(400, f"Unknown company: {company}")

        step = "parse_year"
        year_int = int(year)

        step = "read_file"
        proof_url: str | None = None
        if offer_letter and offer_letter.filename:
            ext = os.path.splitext(offer_letter.filename)[1].lower()
            if ext not in ALLOWED_EXTS:
                raise HTTPException(400, "File must be PDF, JPG, or PNG")
            contents = await offer_letter.read()
            if len(contents) > MAX_FILE_BYTES:
                raise HTTPException(400, "File exceeds 10MB limit")
            step = "upload_file"
            path = f"{uuid.uuid4().hex}{ext}"
            proof_url = upload_offer_letter(
                path, contents, offer_letter.content_type or "application/octet-stream"
            )

        step = "build_row"
        key = f"submission-{email}-{co_slug}-{uni_slug}-{year_int}-{season}".encode()
        student_hash = hashlib.sha256(key).hexdigest()[:16]

        # source must satisfy the internships.source check constraint
        # ('real' | 'synthetic'). User submissions are real (not seeded).
        # proof_url is not persisted to the row — the schema has no such
        # column. The file is still uploaded to Supabase Storage and the
        # URL is returned to the client.
        row = {
            "student_hash":    student_hash,
            "company_slug":    co_slug,
            "university_slug": uni_slug,
            "role_title":      roleTitle,
            "role_category":   category,
            "year":            year_int,
            "season":          season,
            "source":          "real",
        }

        step = "insert"
        insert_internship(row)
        return {"ok": True, "proof_url": proof_url}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            500,
            detail=f"step={step} type={type(e).__name__} msg={e} trace={traceback.format_exc()[-500:]}",
        )