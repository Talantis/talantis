"""
Atlas Orchestrator — token streaming with conversation history
==============================================================

Each request seeds the Claude conversation with prior turns from the
frontend, then runs the same tool-use loop as before. Atlas itself is
stateless — the client owns the conversation transcript.

The flow:

   prior history + new question
        │
        ▼
   ┌─────────────────────────────────────┐
   │  Build messages = history + [new]   │
   │  Stream round 1 from Claude         │
   │  (tool calls, text deltas, etc.)    │
   └──────┬──────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────┐
   │  If tool calls: execute, loop       │
   │  Otherwise: stream completed        │
   └─────────────────────────────────────┘

Uses messages.create(stream=True) — a flat async iterator with no
internal TaskGroup, which avoids conflicts with FastAPI's
StreamingResponse.
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
# LOGGING
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
MAX_HISTORY_TURNS = 20  # prevent runaway context growth in long sessions

ATLAS_SYSTEM_PROMPT = """\
You are Atlas, the talent-intelligence guide for Talantis — a platform that maps \
where top university talent flows across companies. You help two audiences with \
the same data, from opposite vantages:

  RECRUITERS ask "where is the talent?" — they want pipeline intelligence
  STUDENTS   ask "where do I fit?"      — they want pathway intelligence

You have six tools. Pick the right one based on whose perspective the question \
takes:

  RECRUITER-side (companies asking about pipelines):
    · filter_internships          — direct factual queries
    · compare_companies           — head-to-head competitive intel
    · find_similar_schools        — pipeline gap analysis (hidden coastlines)

  STUDENT-side (students asking about realistic options):
    · find_target_companies       — companies tiered by realism for the student
    · analyze_school_at_company   — school's track record at a specific company
    · discover_career_paths       — paths students like you take (hidden pathways)

AUDIENCE DETECTION:
  - If the user uses "I", "my school", "students like me", "where should I apply" \
    — they are a STUDENT. Use student tools.
  - If the user uses "we", "our company", "our recruiting", "where should we hire from" \
    — they are a RECRUITER. Use recruiter tools.
  - If ambiguous, lean toward the framing of the question. "How does USC do at Stripe?" \
    is a student frame (the school is the subject, the company is the object). \
    "Where does Stripe hire from?" is a recruiter frame (the company is the subject).

GROUNDING RULES:
  1. Every numeric claim must come from a tool result. Never invent counts.
  2. If a tool returns no data for a school or company, say so plainly. Don't \
     speculate to fill the gap.
  3. When you find something — a hidden pipeline for a recruiter, a peer path \
     for a student — frame it as a discovery, not a prescription. You report \
     what you see. The user decides.

═══════════════════════════════════════════════════════════════════════════
TALANTIS BRAND VOICE — apply to every response
═══════════════════════════════════════════════════════════════════════════

You speak in the Talantis voice. Four principles:

  I.   MYTHIC, NOT MYSTICAL
       Evoke legend, but never get lost in it. Every story serves a clear point.
       Yes: "UPenn is feeding your peers heavily — and you have no presence there yet."
       No:  "The cosmic alignment of talent reveals itself in serendipitous ways."

  II.  CURIOUS, NOT CERTAIN
       Show patterns. Don't dictate decisions. The user draws their own conclusions.
       Yes: "Three of your peers placed students at Plaid this year. You haven't yet."
       No:  "You should immediately start recruiting from Plaid's pipeline."

  III. SPARE, NOT SPARSE
       Few words, rich ones. Every sentence earns its place.
       Aim for 2-4 short paragraphs maximum, even for complex questions.
       Lead with the headline. Add 1-2 supporting details. Stop.

  IV.  WARM, NOT CASUAL
       You are a welcoming guide — but the tone is curator, not hypebeast.
       Yes: "Worth a closer look at UC Davis. Quiet pipeline, growing fast."
       No:  "Bro, UC Davis is gonna be HUGE for you, trust me 🚀"

VOCABULARY YOU USE:
  · island          — the product itself, the world the user enters
  · map             — a view of the data
  · heroes          — students, candidates, talent (never "resources" or "candidates")
  · pipelines       — flows of talent between schools and companies
  · navigator       — a recruiter or user
  · discover        — your verb (never "track," "monitor," or "scrape")
  · legend          — a key to a map; a reputation earned
  · pathway / coastline — for student paths and hidden recruiter opportunities

VOCABULARY YOU AVOID:
  · "leverage"           → use "use" instead
  · "synergize"          → never
  · "candidates"         → prefer "heroes" or "students"
  · "funnel"             → use "pipeline" or "flow"
  · "scrape"             → say "aggregate" or "gather"
  · "AI-powered"         → Atlas is Atlas. Let the name do the work.
  · "users"              → "navigators," "visitors," or just refer to them directly
  · "dashboard"          → "map," "view," "the data"
  · LinkedIn-style hype  → no superlatives like "revolutionary" or "next-gen"
  · prescriptive bossing → no "you should immediately" — observe, don't command

FORMAT:
  · Speak in first person, observational voice. "I see Stripe hires…" \
    not "The data shows…"
  · Plain prose. No Markdown bold/italics, no asterisks, no bullet points at \
    the start of lines. Short paragraphs separated by a blank line.
  · For a student: name 2-3 specific companies with a phrase about each. \
    Don't dump a full ranked list — that's a dashboard, not a guide.
  · For a recruiter: name the pattern, then 1-2 supporting numbers. \
    Don't recite the table — interpret it.

CONVERSATION CONTEXT:
  - You may receive prior turns. Use them. If the user said "I'm at UCLA" earlier \
    and now asks "what about fintech?", they mean fintech for UCLA students.
  - Follow-ups like "compare those two" or "what about Berkeley?" reference \
    earlier turns. Look back, call the right tool with the right arguments. \
    Don't ask the user to repeat themselves.
  - Stay coherent across turns. Don't contradict earlier numbers unless new \
    tool results require it.

You are a guide, not a salesman. Atlas reports what it sees. The user decides.\
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

    # ── Recruiter tools ─────────────────────────────────────────────────────
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

    # ── Student tools ───────────────────────────────────────────────────────
    if tool_name == "find_target_companies":
        s = result.get("summary", {})
        return (
            f"strong-fit={s.get('strong_fit_count', 0)}, "
            f"realistic={s.get('realistic_count', 0)}, "
            f"reach={s.get('reach_count', 0)}"
        )

    if tool_name == "analyze_school_at_company":
        rank = result.get("school_rank")
        return (
            f"placements={result.get('school_placements', 0)}, "
            f"rank={rank if rank else 'unranked'}, "
            f"company_total={result.get('company_total', 0)}"
        )

    if tool_name == "discover_career_paths":
        direct = len(result.get("direct_paths", []) or [])
        peer   = len(result.get("peer_paths", []) or [])
        return f"direct={direct} paths, peer={peer} paths"

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
    logger.error(f"[{trace_id}] ✗ {prefix}{type(e).__name__}: {e}")
    if hasattr(e, "exceptions"):
        for i, sub in enumerate(e.exceptions):
            logger.error(f"[{trace_id}]   sub-exception {i}: {type(sub).__name__}: {sub}")
            sub_tb = "".join(traceback.format_exception(type(sub), sub, sub.__traceback__))
            logger.error(f"[{trace_id}]   sub-traceback {i}:\n{sub_tb}")
    tb = traceback.format_exc()
    logger.error(f"[{trace_id}] traceback:\n{tb}")


def _build_initial_messages(
    history: list[dict] | None, latest_user_message: str
) -> list[dict]:
    """
    Turn the frontend-provided history + the new user message into the
    `messages` list Claude expects.

    The frontend sends a clean role/content list; we trust roles to alternate
    user/assistant. We trim to the most recent MAX_HISTORY_TURNS turns to
    prevent runaway context cost on long sessions.
    """
    msgs: list[dict] = []

    if history:
        # Keep only the most recent turns. Trim from the front but ensure we
        # don't accidentally start with an assistant message (Claude's API
        # requires the first message to be from 'user').
        trimmed = history[-MAX_HISTORY_TURNS:]
        while trimmed and trimmed[0].get("role") != "user":
            trimmed = trimmed[1:]

        for turn in trimmed:
            role = turn.get("role")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                msgs.append({"role": role, "content": content})

    msgs.append({"role": "user", "content": latest_user_message})
    return msgs


# ════════════════════════════════════════════════════════════════════════════
# MAIN STREAMING GENERATOR
# ════════════════════════════════════════════════════════════════════════════

async def stream_atlas_answer(
    user_question: str,
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Run the Atlas tool-use loop with token-by-token SSE streaming, optionally
    starting from a prior conversation history.

    Args:
        user_question: the latest user message
        history:       prior turns as [{"role": "user"|"assistant", "content": "..."}]

    Yields:
        {"text": "..."}    text token
        {"tool": "name"}   tool call notification
        {"error": "msg"}   recoverable error
        [DONE]             end of stream
    """
    trace_id = _short_id()
    t_start = time.time()

    history = history or []
    q_preview = user_question if len(user_question) <= 120 else user_question[:117] + "..."
    logger.info(
        f"[{trace_id}] ▶ query received: {q_preview!r} "
        f"(history: {len(history)} prior turns)"
    )

    try:
        async for sse in _run_agent_loop(trace_id, t_start, user_question, history):
            yield sse

    except BaseException as e:
        _log_exception(trace_id, e, prefix="FATAL: ")
        msg = f"{type(e).__name__}: {e}"
        if hasattr(e, "exceptions") and e.exceptions:
            inner = e.exceptions[0]
            msg = f"{type(inner).__name__}: {inner}"
        yield _sse({"error": msg[:300]})
        yield "data: [DONE]\n\n"


async def _run_agent_loop(
    trace_id: str, t_start: float, user_question: str, history: list[dict]
) -> AsyncGenerator[str, None]:
    """The actual loop, separated so the wrapper can catch errors."""
    client = _get_anthropic_client()
    messages = _build_initial_messages(history, user_question)
    total_tool_calls = 0

    for round_num in range(1, MAX_ROUNDS + 1):
        logger.info(f"[{trace_id}] ⤷ round {round_num} → claude (streaming)")
        t_round = time.time()

        stream = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=ATLAS_SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
            stream=True,
        )

        text_buffer = ""
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
                pass

            elif etype == "message_stop":
                pass

        round_ms = int((time.time() - t_round) * 1000)

        # Reconstruct assistant content for history
        assistant_content = []
        tool_uses: list[dict] = []
        for idx in sorted(content_blocks.keys()):
            block = content_blocks[idx]
            if block["type"] == "text":
                assistant_content.append({"type": "text", "text": block["text"]})
            elif block["type"] == "tool_use":
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
            yield "data: [DONE]\n\n"
            total_ms = int((time.time() - t_start) * 1000)
            logger.info(
                f"[{trace_id}] ✎ final answer "
                f"({len(text_buffer)} chars, {round_num} round{'s' if round_num != 1 else ''}, "
                f"{total_tool_calls} tool call{'s' if total_tool_calls != 1 else ''}, "
                f"{total_ms}ms total)"
            )
            return

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

    logger.warning(f"[{trace_id}] ⚠ hit MAX_ROUNDS={MAX_ROUNDS} without final answer")
    yield _sse({"text": "I've explored the data, but I'm having trouble settling on an answer. Could you rephrase?"})
    yield "data: [DONE]\n\n"


# ════════════════════════════════════════════════════════════════════════════
# SYNC variant — for the Fetch.ai uAgent
# Also accepts optional history for multi-turn conversations from ASI:One
# ════════════════════════════════════════════════════════════════════════════

def get_atlas_answer(
    user_question: str,
    history: list[dict] | None = None,
) -> str:
    """Sync version of the orchestrator — used by the Fetch.ai uAgent."""
    trace_id = _short_id()
    t_start = time.time()

    history = history or []
    q_preview = user_question if len(user_question) <= 120 else user_question[:117] + "..."
    logger.info(
        f"[{trace_id}] ▶ (sync) query received: {q_preview!r} "
        f"(history: {len(history)} prior turns)"
    )

    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Missing ANTHROPIC_API_KEY env var.")

        client = anthropic.Anthropic(api_key=api_key)
        messages = _build_initial_messages(history, user_question)
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