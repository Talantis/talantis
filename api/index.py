import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import anthropic
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import get_all_data_summary, get_intern_data, get_universities

app = FastAPI(title="Talantis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ATLAS_SYSTEM_PROMPT = """\
You are Atlas, the Talent Intelligence Model for Talantis — a platform that maps where top university \
talent flows across companies. You speak with authority, warmth, and mythic clarity. \
You receive structured internship data and answer questions from recruiters and companies \
trying to understand the talent landscape. Be concise, specific, and insightful. \
Never make up numbers; only reference the data you are given.\
"""


class InsightRequest(BaseModel):
    query: str
    university: str | None = None


@app.get("/api/universities")
def universities():
    return get_universities()


@app.get("/api/companies")
def companies(university: str | None = Query(default=None)):
    return get_intern_data(university)


@app.post("/api/insights")
async def insights(body: InsightRequest):
    data_context = get_all_data_summary()
    user_message = (
        f"Internship dataset (JSON):\n{data_context}\n\n"
        + (f"Filter context — university: {body.university}\n\n" if body.university else "")
        + f"Question: {body.query}"
    )

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def generate():
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=ATLAS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
