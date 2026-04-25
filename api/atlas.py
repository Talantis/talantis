"""
Atlas Orchestrator — token streaming, no TaskGroup conflicts
==============================================================

WHY THIS VERSION
----------------
The previous version used `client.messages.stream()` as an `async with`
context manager. On Vercel, that runs an internal `anyio.TaskGroup` to
manage the SSE connection. When wrapped in FastAPI's `StreamingResponse`,
which itself uses a TaskGroup to drive the response generator, the two
TaskGroups conflict. The result is the ExceptionGroup we saw in logs:

    ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
      File "starlette/responses.py", line 252
        async with anyio.create_task_group() as task_group:

This rewrite drops the context-manager API and uses `messages.create(
stream=True)` directly. That returns a plain async iterator over events
— no inner TaskGroup, no conflict with Starlette.

Same external behavior: token-by-token SSE streaming with tool use.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
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
    characters at the start of lines. Short paragraphs separated by a blank line are fine.

You are a guide, not a salesman.\
"""


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
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


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing ANTHROPIC_API_KEY env var. "
            "Set it in Vercel → Project Settings → Environment Variables."
        )
    return anthropic.AsyncAnthropic(api_key=api_key)


def _log_exception(trace_id: str, e: BaseException, prefix: str = "") -> None:
    """
    Log an exception with full traceback. Handles ExceptionGroup specially
    since those wrap their real cause in a sub-exception list.
    """
    logger.error(f"[{trace_id}] ✗ {prefix}{type(e).__name__}: {e}")

    # ExceptionGroup hides the real error in .exceptions
    if hasattr(e, "exceptions"):
        for i, sub in enumerate(e.exceptions):
            logger.error(f"[{trace_id}]   sub-exception {i}: {type(sub).__name__}: {sub}")
            sub_tb = "".join(traceback.format_exception(type(sub), sub, sub.__traceback__))
            logger.error(f"[{trace_id}]   sub-traceback {i}:\n{sub_tb}")

    tb = traceback.format_exc()
    logger.error(f"[{trace_id}] traceback:\n{tb}")


# ════════════════════════════════════════════════════════════════════════════
# MAIN STREAMING GENERATOR
# Uses messages.create(stream=True) — a flat async iterator, no TaskGroup.
# Wrapped in try/except so any exception is surfaced cleanly.
# ════════════════════════════════════════════════════════════════════════════

async def stream_atlas_answer(user_question: str) -> AsyncGenerator[str, None]:
    """
    Run the Atlas tool-use loop with token-by-token SSE streaming.

    Yields:
        {"text": "..."}    text token
        {"tool": "name"}   tool call notification
        {"error": "msg"}   recoverable error — frontend should display
        [DONE]             end of stream
    """
    trace_id = _short_id()
    t_start = time.time()

    q_preview = user_question if len(user_question) <= 120 else user_question[:117] + "..."
    logger.info(f"[{trace_id}] ▶ query received: {q_preview!r}")

    try:
        async for sse in _run_agent_loop(trace_id, t_start, user_question):
            yield sse

    except BaseException as e:
        _log_exception(trace_id, e, prefix="FATAL: ")

        # Extract a useful message — pick the deepest sub-exception if it's
        # an ExceptionGroup, since that's the real error.
        msg = f"{type(e).__name__}: {e}"
        if hasattr(e, "exceptions") and e.exceptions:
            inner = e.exceptions[0]
            msg = f"{type(inner).__name__}: {inner}"

        yield _sse({"error": msg[:300]})
        yield "data: [DONE]\n\n"


async def _run_agent_loop(
    trace_id: str, t_start: float, user_question: str
) -> AsyncGenerator[str, None]:
    """The actual loop, separated so the wrapper above can catch errors."""
    client = _get_anthropic_client()
    messages: list[dict] = [{"role": "user", "content": user_question}]
    total_tool_calls = 0

    for round_num in range(1, MAX_ROUNDS + 1):
        logger.info(f"[{trace_id}] ⤷ round {round_num} → claude (streaming)")
        t_round = time.time()

        # ── Open a streaming connection ────────────────────────────────────
        # Use stream=True directly. This returns an async iterator over raw
        # events — no internal TaskGroup, no conflict with Starlette.
        stream = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=ATLAS_SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
            stream=True,
        )

        # We need to reconstruct the assistant message from the events so we
        # can append it to history for the next round. Track text and tool
        # blocks as they stream in.
        text_buffer = ""
        # content_blocks[index] = {"type": "text", "text": "..."}
        #                       or {"type": "tool_use", "id": ..., "name": ..., "input_json": "..."}
        content_blocks: dict[int, dict] = {}

        async for event in stream:
            etype = event.type

            if etype == "content_block_start":
                idx = event.index
                block = event.content_block
                if block.type == "text":
                    content_blocks[idx] = {"type": "text", "text": ""}
                elif block.type == "tool_use":
                    content_blocks[idx] = {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input_json": "",
                    }

            elif etype == "content_block_delta":
                idx = event.index
                delta = event.delta
                if delta.type == "text_delta":
                    yield _sse({"text": delta.text})
                    text_buffer += delta.text
                    if idx in content_blocks:
                        content_blocks[idx]["text"] += delta.text
                elif delta.type == "input_json_delta":
                    if idx in content_blocks:
                        content_blocks[idx]["input_json"] += delta.partial_json

            elif etype == "message_delta":
                # carries stop_reason, usage — nothing to forward to client
                pass

            elif etype == "message_stop":
                pass

        round_ms = int((time.time() - t_round) * 1000)

        # ── Reconstruct assistant content for history ──────────────────────
        assistant_content = []
        tool_uses: list[dict] = []
        for idx in sorted(content_blocks.keys()):
            block = content_blocks[idx]
            if block["type"] == "text":
                assistant_content.append({"type": "text", "text": block["text"]})
            elif block["type"] == "tool_use":
                # Parse the accumulated JSON. Empty string means {} arguments.
                try:
                    tool_input = json.loads(block["input_json"]) if block["input_json"] else {}
                except json.JSONDecodeError as e:
                    logger.error(
                        f"[{trace_id}] bad tool input JSON for {block['name']}: "
                        f"{block['input_json']!r} ({e})"
                    )
                    tool_input = {}
                assistant_content.append({
                    "type": "tool_use",
                    "id": block["id"],
                    "name": block["name"],
                    "input": tool_input,
                })
                tool_uses.append({
                    "id": block["id"],
                    "name": block["name"],
                    "input": tool_input,
                })

        messages.append({"role": "assistant", "content": assistant_content})

        if not tool_uses:
            # ── No tool calls: final answer was already streamed ───────────
            yield "data: [DONE]\n\n"
            total_ms = int((time.time() - t_start) * 1000)
            logger.info(
                f"[{trace_id}] ✎ final answer "
                f"({len(text_buffer)} chars, {round_num} round{'s' if round_num != 1 else ''}, "
                f"{total_tool_calls} tool call{'s' if total_tool_calls != 1 else ''}, "
                f"{total_ms}ms total)"
            )
            return

        # ── Execute the tools Claude requested ─────────────────────────────
        tool_results = []
        for tool_use in tool_uses:
            total_tool_calls += 1
            logger.info(
                f"[{trace_id}] ⚙  tool call: "
                f"{tool_use['name']}({_format_args(tool_use['input'])})"
            )
            yield _sse({"tool": tool_use["name"]})

            t_tool = time.time()
            result = execute_tool(tool_use["name"], tool_use["input"])
            tool_ms = int((time.time() - t_tool) * 1000)

            summary = _summarize_result(tool_use["name"], result)
            logger.info(
                f"[{trace_id}] ✓ tool result: {tool_use['name']} → {summary} ({tool_ms}ms)"
            )
            if logger.isEnabledFor(logging.DEBUG):
                payload = json.dumps(result, default=str)
                if len(payload) > 1000:
                    payload = payload[:1000] + "...(truncated)"
                logger.debug(f"[{trace_id}]   payload: {payload}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use["id"],
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

    # ── Hit the round cap ─────────────────────────────────────────────────
    logger.warning(f"[{trace_id}] ⚠ hit MAX_ROUNDS={MAX_ROUNDS} without final answer")
    yield _sse({"text": "I've explored the data, but I'm having trouble settling on an answer. Could you rephrase?"})
    yield "data: [DONE]\n\n"


# ════════════════════════════════════════════════════════════════════════════
# SYNC variant — for the Fetch.ai uAgent
# ════════════════════════════════════════════════════════════════════════════

def get_atlas_answer(user_question: str) -> str:
    """Sync version — used by the Fetch.ai uAgent (no streaming needed)."""
    trace_id = _short_id()
    t_start = time.time()

    q_preview = user_question if len(user_question) <= 120 else user_question[:117] + "..."
    logger.info(f"[{trace_id}] ▶ (sync) query received: {q_preview!r}")

    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Missing ANTHROPIC_API_KEY env var.")

        client = anthropic.Anthropic(api_key=api_key)
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

        logger.warning(f"[{trace_id}] ⚠ (sync) hit MAX_ROUNDS={MAX_ROUNDS}")
        return "I've explored the data, but couldn't settle on an answer. Could you rephrase?"

    except BaseException as e:
        _log_exception(trace_id, e, prefix="(sync) FATAL: ")
        return f"Atlas hit an error: {type(e).__name__}: {str(e)[:200]}"