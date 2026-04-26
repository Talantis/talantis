"""
Atlas uAgent — Render deployment variant
==========================================

Same Chat Protocol implementation as the local version, but configured for
running headless on Render (or any cloud Python host) with a public URL.

Differences from the local version:
  - No mailbox=True (mailbox needs a browser handshake to set up; we can't
    do that on a remote server)
  - Uses an explicit `endpoint=[<public URL>]` so other agents can reach us
  - Binds to PORT from the environment (Render sets this), defaults to 8001
  - Reads the public URL from PUBLIC_URL env var (Render auto-provides
    RENDER_EXTERNAL_URL, we read either)

Architecture
------------
This uAgent is a thin bridge. Real work happens at the Vercel-hosted FastAPI
backend (talantis.vercel.app/api/insights) which already implements:
  - Multi-turn conversation with Claude
  - Three Postgres-backed tools (filter_internships, compare_companies,
    find_similar_schools)
  - Streaming SSE responses

The uAgent's job:
  1. Receive a ChatMessage (from ASI:One or any other agent)
  2. Forward the user's text to the Talantis backend
  3. Read the SSE stream until [DONE]
  4. Send the assembled answer back as a ChatMessage

Per-sender history is kept in agent storage so multi-turn works across
ASI:One sessions.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from uuid import uuid4

import httpx
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

# ════════════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════════════

# The Talantis backend (already deployed on Vercel)
TALANTIS_API_URL = os.environ.get(
    "TALANTIS_API_URL",
    "https://talantis.vercel.app/api/insights",
)

# uAgent identity. Stable across deploys — DO NOT change after registering
# on Agentverse, or you'll get a new agent address and lose your listing.
SEED_PHRASE = os.environ.get(
    "AGENT_SEED_PHRASE",
    "talantis-atlas-default-seed-replace-me-with-a-long-random-string",
)

# Render sets PORT automatically. Locally we default to 8001.
PORT = int(os.environ.get("PORT", "8001"))

# Public URL where this agent is reachable. Render exposes this as
# RENDER_EXTERNAL_URL automatically, but we also accept PUBLIC_URL as
# a manual override for other hosts.
PUBLIC_URL = (
    os.environ.get("PUBLIC_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or f"http://localhost:{PORT}"
)

# Build the agent's submit endpoint. Other agents (and ASI:One) will POST
# Chat Protocol envelopes here.
ENDPOINT = f"{PUBLIC_URL.rstrip('/')}/submit"

MAX_HISTORY_TURNS = 20
HTTP_TIMEOUT_SECONDS = 60


# ════════════════════════════════════════════════════════════════════════════
# AGENT SETUP
# ════════════════════════════════════════════════════════════════════════════

agent = Agent(
    name="Atlas",
    seed=SEED_PHRASE,
    port=PORT,
    endpoint=[ENDPOINT],
    publish_agent_details=True,
    readme_path="README.md",
)

protocol = Protocol(spec=chat_protocol_spec)


# ════════════════════════════════════════════════════════════════════════════
# CONVERSATION HISTORY (per-sender)
# ════════════════════════════════════════════════════════════════════════════

def history_key(sender: str) -> str:
    return f"history:{sender}"


def load_history(ctx: Context, sender: str) -> list[dict]:
    raw = ctx.storage.get(history_key(sender))
    if not raw:
        return []
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def save_history(ctx: Context, sender: str, history: list[dict]) -> None:
    trimmed = history[-MAX_HISTORY_TURNS:]
    ctx.storage.set(history_key(sender), json.dumps(trimmed))


# ════════════════════════════════════════════════════════════════════════════
# CALL THE TALANTIS BACKEND
# ════════════════════════════════════════════════════════════════════════════

async def ask_atlas_via_api(user_question: str, history: list[dict]) -> str:
    """POST to the streaming endpoint, accumulate text deltas, return final answer."""
    payload = {"query": user_question, "history": history}

    accumulated = ""
    error_msg: str | None = None

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        async with client.stream(
            "POST",
            TALANTIS_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as response:
            response.raise_for_status()
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                events = buffer.split("\n\n")
                buffer = events.pop() if events else ""
                for event in events:
                    data_line = next(
                        (l for l in event.split("\n") if l.startswith("data: ")),
                        None,
                    )
                    if not data_line:
                        continue
                    payload_str = data_line[6:].strip()
                    if payload_str == "[DONE]":
                        continue
                    try:
                        parsed = json.loads(payload_str)
                    except json.JSONDecodeError:
                        continue
                    if "text" in parsed:
                        accumulated += parsed["text"]
                    elif "error" in parsed:
                        error_msg = parsed["error"]

    if error_msg and not accumulated:
        return f"I hit an error reaching the data: {error_msg}"
    return accumulated.strip() or "I have no answer to give. Try asking again."


# ════════════════════════════════════════════════════════════════════════════
# CHAT PROTOCOL HANDLERS
# ════════════════════════════════════════════════════════════════════════════

@protocol.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    # Acknowledge receipt (Chat Protocol requirement)
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.utcnow(),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    # Extract user text
    user_text = ""
    for item in msg.content:
        if isinstance(item, TextContent):
            user_text += item.text
    user_text = user_text.strip()
    if not user_text:
        await send_text(ctx, sender, "I didn't catch a question. What would you like to know?")
        return

    ctx.logger.info(f"[atlas] user={sender[:16]}... q={user_text[:80]!r}")
    history = load_history(ctx, sender)

    try:
        answer = await ask_atlas_via_api(user_text, history)
    except httpx.HTTPStatusError as e:
        ctx.logger.error(f"[atlas] backend HTTP error: {e.response.status_code}")
        await send_text(
            ctx, sender,
            f"I couldn't reach my data right now (HTTP {e.response.status_code}). "
            "The shore is dark — try again in a moment."
        )
        return
    except httpx.HTTPError as e:
        ctx.logger.error(f"[atlas] backend network error: {e}")
        await send_text(
            ctx, sender,
            "I couldn't reach my data right now. The shore is dark — try again in a moment."
        )
        return
    except Exception as e:
        ctx.logger.exception(f"[atlas] unexpected error: {e}")
        await send_text(
            ctx, sender,
            f"Something unexpected happened: {type(e).__name__}. Try rephrasing the question?"
        )
        return

    ctx.logger.info(f"[atlas] answer ({len(answer)} chars) → {sender[:16]}...")

    new_history = history + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": answer},
    ]
    save_history(ctx, sender, new_history)

    await send_text(ctx, sender, answer)


@protocol.on_message(ChatAcknowledgement)
async def handle_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.debug(f"[atlas] ack from {sender[:16]}... for {msg.acknowledged_msg_id}")


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

async def send_text(ctx: Context, recipient: str, text: str) -> None:
    await ctx.send(
        recipient,
        ChatMessage(
            timestamp=datetime.utcnow(),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=text)],
        ),
    )


@agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info("=" * 60)
    ctx.logger.info(f"  Atlas uAgent online")
    ctx.logger.info(f"  Address:    {agent.address}")
    ctx.logger.info(f"  Endpoint:   {ENDPOINT}")
    ctx.logger.info(f"  Backend:    {TALANTIS_API_URL}")
    ctx.logger.info("=" * 60)


agent.include(protocol, publish_manifest=True)


if __name__ == "__main__":
    agent.run()