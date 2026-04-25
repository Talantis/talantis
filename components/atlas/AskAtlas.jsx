"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import AtlasLogo from "@/components/AtlasLogo";

/**
 * AskAtlas — natural language query interface (live streaming).
 *
 * Streaming protocol:
 *   The backend at POST /api/insights returns Server-Sent Events:
 *     data: {"text": "..."}    narrative chunk → append
 *     data: {"tool": "name"}   tool-call notification → show in UI
 *     data: [DONE]              end of stream
 *
 * We use fetch() with a manual stream reader instead of EventSource because
 * EventSource only supports GET, but our endpoint is POST. This is the same
 * pattern ChatGPT, Claude.ai, and Vercel AI SDK use under the hood.
 *
 * Props:
 *   university — optional currently-selected university (passed as context)
 */

// Pre-canned demo prompts that exercise all three Atlas tools
const SUGGESTIONS = [
  // Tool 1: filter_internships
  "How many UCLA students interned at Stripe last year?",
  // Tool 2: compare_companies
  "Compare Citadel and Jane Street's hiring patterns.",
  // Tool 3: find_similar_schools (the wow demo)
  "We're Stripe. Where are Plaid, Brex, and Ramp finding talent we're missing?",
];

// Friendly labels for the tool indicator
const TOOL_LABELS = {
  filter_internships:    "scanning the dataset",
  compare_companies:     "comparing pipelines",
  find_similar_schools:  "tracing hidden coastlines",
};

export default function AskAtlas({ university = null }) {
  const [input, setInput] = useState("");
  const [response, setResponse] = useState("");
  const [activeTool, setActiveTool] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const abortRef = useRef(null);
  const responseRef = useRef(null);

  // Auto-scroll the response area as text streams in
  useEffect(() => {
    if (responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight;
    }
  }, [response]);

  // Cancel any in-flight request when the component unmounts
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  // ───────────────────────────────────────────────────────────────────────
  // Single submit path: takes a question string, runs the SSE stream
  // ───────────────────────────────────────────────────────────────────────
  async function askAtlas(question) {
    if (!question?.trim() || loading) return;

    setLoading(true);
    setResponse("");
    setActiveTool(null);
    setError(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch("/api/insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: question.trim(), university }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Atlas returned ${res.status}: ${res.statusText}`);
      }
      if (!res.body) {
        throw new Error("Atlas returned an empty response.");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by blank lines (\n\n).
        // We may receive a partial event at the end of a chunk, so we split,
        // keep the trailing piece in the buffer, and process complete events.
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          const dataLine = event
            .split("\n")
            .find((l) => l.startsWith("data: "));
          if (!dataLine) continue;

          const payload = dataLine.slice(6).trim();
          if (payload === "[DONE]") {
            return; // finally block resets state
          }

          try {
            const parsed = JSON.parse(payload);
            if (parsed.text) {
              setResponse((prev) => prev + parsed.text);
            } else if (parsed.tool) {
              setActiveTool(parsed.tool);
            }
          } catch {
            // Malformed JSON — skip silently. Keeps UI alive even if backend
            // ever sends an unrecognized payload.
          }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") return; // user navigated away
      console.error("Atlas streaming error:", err);
      setError(err.message || "Atlas couldn't reach the data.");
    } finally {
      setLoading(false);
      setActiveTool(null);
      abortRef.current = null;
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    const q = input;
    setInput("");
    askAtlas(q);
  }

  function handleSuggestion(s) {
    askAtlas(s);
  }

  function handleReset() {
    setResponse("");
    setError(null);
    setActiveTool(null);
  }

  const showSuggestions = !response && !loading && !error;

  return (
    <div className="bg-navy-soft border border-line">
      {/* Header */}
      <div className="flex items-center gap-4 px-8 py-6 border-b border-line">
        <AtlasLogo size={40} />
        <div className="flex-1">
          <div className="font-display text-xl text-cream">Atlas</div>
          <div className="font-display italic text-xs tracking-wider-md uppercase text-gold">
            The Guide
          </div>
        </div>
        {(response || error) && !loading && (
          <button
            onClick={handleReset}
            className="font-display italic text-xs tracking-wider-md uppercase text-cream-dim hover:text-gold transition-colors"
          >
            New Question
          </button>
        )}
      </div>

      {/* Conversation area */}
      <div
        ref={responseRef}
        className="px-8 py-10 min-h-[240px] max-h-[480px] overflow-y-auto"
      >
        {/* Idle — show suggestions */}
        {showSuggestions && (
          <div className="space-y-4">
            <p className="font-display italic text-lg text-cream-dim">
              &ldquo;Ask me about the shape of talent. Where it flows, where it
              pools, where it hides.&rdquo;
            </p>
            <div className="flex flex-col gap-2 pt-4">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSuggestion(s)}
                  className="text-left text-sm px-4 py-3 bg-navy border border-line-soft hover:border-gold text-cream-dim hover:text-gold transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Loading — no response yet */}
        {loading && !response && (
          <div className="flex items-center gap-3 font-display italic text-cream-dim">
            <Loader2 size={16} className="animate-spin text-gold" />
            <span>
              Atlas is{" "}
              {activeTool
                ? TOOL_LABELS[activeTool] || "working"
                : "mapping the shore"}
              <span className="inline-block animate-pulse">...</span>
            </span>
          </div>
        )}

        {/* Streamed response */}
        {response && (
          <div className="font-display text-lg leading-relaxed text-cream whitespace-pre-wrap">
            {response}
            {loading && (
              <span className="inline-block w-2 h-5 ml-1 bg-gold animate-pulse align-middle" />
            )}
          </div>
        )}

        {/* Tool indicator while a response is already streaming */}
        {loading && response && activeTool && (
          <div className="mt-4 flex items-center gap-2 font-display italic text-xs tracking-wider-md uppercase text-gold">
            <Loader2 size={12} className="animate-spin" />
            <span>{TOOL_LABELS[activeTool] || activeTool}</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="font-display italic text-cream-dim border-l-2 border-red-500/50 pl-4">
            <div className="text-sm">Atlas couldn&rsquo;t reach the shore.</div>
            <div className="text-xs text-cream-dim/70 mt-1 font-body not-italic">
              {error}
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-3 border-t border-line px-4 py-4"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={loading ? "Atlas is thinking..." : "Ask Atlas..."}
          disabled={loading}
          className="flex-1 bg-transparent border-none outline-none font-body text-cream placeholder:text-cream-dim px-4 py-2 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="flex items-center gap-2 px-5 py-2 bg-gold text-navy font-body font-medium hover:bg-gold-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span>{loading ? "..." : "Ask"}</span>
          {!loading && <Send size={14} />}
        </button>
      </form>
    </div>
  );
}
