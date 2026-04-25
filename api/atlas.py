"""
Atlas Orchestrator — true token streaming
==========================================

The agent loop. Takes a user question, runs a back-and-forth conversation
with Claude where Claude can call tools, then streams the final narrative
answer to the user TOKEN BY TOKEN.

The flow:

   user question
        │
        ▼
   ┌─────────────────────────────────────┐
   │  Stream round 1 from Claude         │
   │  · capture tool_use blocks          │
   │  · stream text deltas to client     │
   └──────┬──────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────┐
   │  If tool calls were made:           │
   │  · execute each against Postgres    │
   │  · feed results back, loop          │
   │  Otherwise:                         │
   │  · we already streamed the answer   │
   └─────────────────────────────────────┘

This uses anthropic.AsyncAnthropic.messages.stream() which yields token
deltas as they arrive from Claude's API. The frontend sees text appear
character-by-character, exactly like ChatGPT.

LOGGING
-------
Every tool call is logged to stdout in a structured format that Vercel's
Logs tab automatically captures. Example:

  [atlas] ▶ query received: "How many UCLA students interned at Stripe?"
  [atlas] ⤷ round 1 → claude (streaming)
  [atlas] ⚙  tool call: filter_internships(university='UCLA', company='Stripe')
  [atlas] ✓ tool result: filter_internships → 1 row, total_internships=3 (42ms)
  [atlas] ⤷ round 2 → claude (streaming)
  [atlas] ✎ final answer (87 chars, 2 rounds, 312ms total)

Set LOG_LEVEL=DEBUG to also see the full tool result payloads.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import AsyncGenerator

import anthropic

from tools import TOOL_DEFINITIONS, execute_tool

# ════════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ════════════════════════════════════════════════════════════════════════════

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("atlas")
logger.setLevel(LOG_LEVEL)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


# ════════════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════════════

MODEL = "claude-sonnet-4-5"
MAX_ROUNDS = 5
MAX_TOKENS = 1024

ATLAS_SYSTEM_PROMPT = """\
You are Atlas, the Talent Intelligence Model for Talantis — a platform that maps where \
top university talent flows across companies. You speak with authority, warmth, and \
mythic clarity.

You have three tools. Use them to ground every claim in real data:

  · filter_internships    — direct factual queries (counts, lists, rankings)
  · compare_companies     — head-to-head pipeline comparisons
  · find_similar_schools  — finding hidden pipelines (peers recruit there, you don't)

GUIDELINES:
  1. Every numeric claim must come from a tool result. Never invent counts.
  2. Speak in first person, observational voice. "I see Stripe hires…", not "The data shows…"
  3. Be concise. Lead with the headline, then 1-2 supporting details.
  4. Name the pattern, not just the numbers. "UPenn is feeding your peers heavily — \
     and you have no presence there yet" beats "UPenn has 9 interns at peers, 0 at you."
  5. When you find a hidden pipeline (find_similar_schools), frame it as a discovery, \
     not a prescription. Atlas reports; the user decides.
  6. If the user's question is ambiguous, pick the most likely interpretation and answer. \
     Don't ask clarifying questions unless the question is truly impossible to interpret.

FORMATTING:
  - Use plain prose. No Markdown bold/italics, no asterisks for emphasis, no bullet \
    characters at the start of lines. The frontend renders Markdown, but heavy \
    formatting clutters Atlas's mythic voice.
  - Short paragraphs separated by a blank line are fine.
  - You may use simple bullets (one item per line, starting with "- ") if you must \
    list 3+ items, but prefer prose.

You are a guide, not a salesman.\
"""


# ════════════════════════════════════════════════════════════════════════════
# LOG HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _format_args(args: dict) -> str:
    parts = []
    for k, v in args.items():
        if isinstance(v, str):
            parts.append(f"{k}={v!r}")
        elif isinstance(v, list):
            parts.append(f"{k}={v}")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)


def _summarize_result(tool_name: str, result: dict) -> str:
    if "error" in result:
        return f"ERROR: {result['error']}"

    if tool_name == "filter_internships":
        rows = result.get("rows", [])
        return f"{len(rows)} rows, total_internships={result.get('total_internships', 0)}"

    if tool_name == "compare_companies":
        comparison = result.get("comparison", [])
        summary = result.get("summary", {})
        return f"{len(comparison)} universities × {len(summary)} companies"

    if tool_name == "find_similar_schools":
        pipelines = result.get("hidden_pipelines", [])
        if pipelines:
            top = pipelines[0]
            return (
                f"{len(pipelines)} hidden pipelines, "
                f"top={top.get('university')!r} (gap={top.get('gap')})"
            )
        return f"0 hidden pipelines"

    return f"keys={list(result.keys())}"


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ════════════════════════════════════════════════════════════════════════════
# MAIN STREAMING GENERATOR
# Each round uses messages.stream() so the frontend sees tokens as they arrive.
# ════════════════════════════════════════════════════════════════════════════

async def stream_atlas_answer(user_question: str) -> AsyncGenerator[str, None]:
    """
    Run the Atlas tool-use loop with REAL token-by-token streaming.

    For each round we open a streaming connection to Claude. Two kinds of
    blocks come through:
      · text — yield each delta to the client immediately
      · tool_use — accumulate, then execute after the round completes

    Yields (Server-Sent Events):
        {"text": "chunk"}     a token of narrative text
        {"tool": "name"}      tool call notification (UX/loading state)
        [DONE]                end of stream
    """
    trace_id = _short_id()
    t_start = time.time()

    q_preview = user_question if len(user_question) <= 120 else user_question[:117] + "..."
    logger.info(f"[{trace_id}] ▶ query received: {q_preview!r}")

    client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages: list[dict] = [{"role": "user", "content": user_question}]
    total_tool_calls = 0

    for round_num in range(1, MAX_ROUNDS + 1):
        logger.info(f"[{trace_id}] ⤷ round {round_num} → claude (streaming)")
        t_round = time.time()

        # Open a streaming connection. The async with block manages the network
        # connection lifecycle; we iterate events inside it.
        tool_uses_in_round: list[dict] = []
        text_buffer = ""  # accumulated text for the assistant message in history

        async with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=ATLAS_SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        ) as stream:
            # Iterate raw events so we can handle text deltas AND tool_use blocks.
            # The .text_stream helper only yields text — we need both.
            async for event in stream:
                etype = event.type

                if etype == "content_block_delta":
                    # A piece of a content block has arrived
                    delta = event.delta
                    if delta.type == "text_delta":
                        # ── TOKEN! Stream it to the client immediately ─────
                        yield _sse({"text": delta.text})
                        text_buffer += delta.text
                    # tool_use blocks come as "input_json_delta" but we read
                    # the full input from the final_message at the end —
                    # streaming partial JSON to the client isn't useful.

                elif etype == "content_block_stop":
                    # A full content block has completed. If it was a tool_use
                    # block, capture the full input from the final message later.
                    pass

            # When the stream completes, get the consolidated final message
            final = await stream.get_final_message()

        round_ms = int((time.time() - t_round) * 1000)
        logger.debug(
            f"[{trace_id}]   stop_reason={final.stop_reason} "
            f"in_tokens={final.usage.input_tokens} "
            f"out_tokens={final.usage.output_tokens} "
            f"({round_ms}ms)"
        )

        # Add the assistant's full response (text + tool_use blocks) to history
        messages.append({"role": "assistant", "content": final.content})

        # Extract any tool_use blocks
        tool_uses_in_round = [b for b in final.content if b.type == "tool_use"]

        if not tool_uses_in_round:
            # ── No tool calls → final answer was already streamed ─────────
            yield "data: [DONE]\n\n"

            total_ms = int((time.time() - t_start) * 1000)
            logger.info(
                f"[{trace_id}] ✎ final answer "
                f"({len(text_buffer)} chars, {round_num} round{'s' if round_num != 1 else ''}, "
                f"{total_tool_calls} tool call{'s' if total_tool_calls != 1 else ''}, "
                f"{total_ms}ms total)"
            )
            return

        # ── Execute the tool(s) Claude requested ──────────────────────────
        tool_results = []
        for tool_use in tool_uses_in_round:
            total_tool_calls += 1
            logger.info(
                f"[{trace_id}] ⚙  tool call: "
                f"{tool_use.name}({_format_args(tool_use.input)})"
            )
            yield _sse({"tool": tool_use.name})

            t_tool = time.time()
            result = execute_tool(tool_use.name, tool_use.input)
            tool_ms = int((time.time() - t_tool) * 1000)

            summary = _summarize_result(tool_use.name, result)
            logger.info(f"[{trace_id}] ✓ tool result: {tool_use.name} → {summary} ({tool_ms}ms)")
            if logger.isEnabledFor(logging.DEBUG):
                payload = json.dumps(result, default=str)
                if len(payload) > 1000:
                    payload = payload[:1000] + "...(truncated)"
                logger.debug(f"[{trace_id}]   payload: {payload}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": json.dumps(result),
            })

        # Feed tool results back as the next user message; loop to next round
        messages.append({"role": "user", "content": tool_results})

    # ── Hit the round cap without a final answer ─────────────────────────
    logger.warning(f"[{trace_id}] ⚠ hit MAX_ROUNDS={MAX_ROUNDS} without final answer")
    yield _sse({"text": "I've explored the data, but I'm having trouble settling on an answer. Could you rephrase the question?"})
    yield "data: [DONE]\n\n"


# ════════════════════════════════════════════════════════════════════════════
# SYNC variant — for the Fetch.ai uAgent (Chat Protocol is single-shot)
# Same logging hooks, but returns one string instead of streaming.
# ════════════════════════════════════════════════════════════════════════════

def get_atlas_answer(user_question: str) -> str:
    """Sync version of the orchestrator — used by the Fetch.ai uAgent."""
    trace_id = _short_id()
    t_start = time.time()

    q_preview = user_question if len(user_question) <= 120 else user_question[:117] + "..."
    logger.info(f"[{trace_id}] ▶ (sync) query received: {q_preview!r}")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages: list[dict] = [{"role": "user", "content": user_question}]
    total_tool_calls = 0

    for round_num in range(1, MAX_ROUNDS + 1):
        logger.info(f"[{trace_id}] ⤷ (sync) round {round_num} → claude")

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=ATLAS_SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            answer = "".join(b.text for b in response.content if b.type == "text")
            total_ms = int((time.time() - t_start) * 1000)
            logger.info(
                f"[{trace_id}] ✎ (sync) final answer "
                f"({len(answer)} chars, {round_num} rounds, {total_tool_calls} tools, {total_ms}ms)"
            )
            return answer

        tool_results = []
        for tool_use in tool_uses:
            total_tool_calls += 1
            logger.info(
                f"[{trace_id}] ⚙  (sync) tool call: "
                f"{tool_use.name}({_format_args(tool_use.input)})"
            )
            t_tool = time.time()
            result = execute_tool(tool_use.name, tool_use.input)
            tool_ms = int((time.time() - t_tool) * 1000)
            logger.info(
                f"[{trace_id}] ✓ (sync) tool result: "
                f"{tool_use.name} → {_summarize_result(tool_use.name, result)} ({tool_ms}ms)"
            )
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": json.dumps(result),
            })
        messages.append({"role": "user", "content": tool_results})

    logger.warning(f"[{trace_id}] ⚠ (sync) hit MAX_ROUNDS={MAX_ROUNDS} without final answer")
    return "I've explored the data, but couldn't settle on an answer. Could you rephrase?"
