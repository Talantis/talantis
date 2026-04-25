"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import AtlasLogo from "@/components/AtlasLogo";

/**
 * AskAtlas — natural language query interface (streaming + Markdown).
 *
 * Streaming protocol:
 *   The backend at POST /api/insights returns Server-Sent Events:
 *     data: {"text": "..."}    text token → append (TRUE token-by-token now)
 *     data: {"tool": "name"}   tool-call notification → show in UI
 *     data: [DONE]              end of stream
 *
 * Why fetch + ReadableStream instead of EventSource:
 *   EventSource only supports GET. Our endpoint is POST so we can send a JSON
 *   body cleanly. We read the body as a stream and parse SSE manually — same
 *   pattern Vercel AI SDK and ChatGPT use.
 *
 * Markdown:
 *   Atlas is instructed to use plain prose, but if it returns Markdown
 *   (asterisks, bullets, etc.) we render it via react-markdown so it looks
 *   clean instead of showing raw `**bold**` text.
 *
 * Props:
 *   university — optional currently-selected university (passed as context)
 */

const SUGGESTIONS = [
  "How many UCLA students interned at Stripe last year?",
  "Compare Citadel and Jane Street's hiring patterns.",
  "We're Stripe. Where are Plaid, Brex, and Ramp finding talent we're missing?",
];

const TOOL_LABELS = {
  filter_internships:    "scanning the dataset",
  compare_companies:     "comparing pipelines",
  find_similar_schools:  "tracing hidden coastlines",
};

// ────────────────────────────────────────────────────────────────────────────
// Markdown renderer with brand-styled components.
// We override every element type so the output blends with the Atlas voice
// (cream prose on navy, gold for emphasis, restrained spacing).
// ────────────────────────────────────────────────────────────────────────────
const markdownComponents = {
  p: ({ children }) => (
    <p className="font-display text-lg leading-relaxed text-cream mb-4 last:mb-0">
      {children}
    </p>
  ),
  strong: ({ children }) => (
    <strong className="text-gold font-medium">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="text-gold italic">{children}</em>
  ),
  ul: ({ children }) => (
    <ul className="list-none space-y-2 my-4 pl-0">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-none space-y-2 my-4 pl-0 counter-reset-list">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="font-display text-lg leading-relaxed text-cream pl-6 relative before:content-['✦'] before:absolute before:left-0 before:text-gold before:text-sm before:top-1">
      {children}
    </li>
  ),
  h1: ({ children }) => (
    <h3 className="font-display text-2xl text-cream mb-3 mt-4 first:mt-0">{children}</h3>
  ),
  h2: ({ children }) => (
    <h3 className="font-display text-xl text-cream mb-2 mt-4 first:mt-0">{children}</h3>
  ),
  h3: ({ children }) => (
    <h4 className="font-display text-lg text-gold italic mb-2 mt-3 first:mt-0">{children}</h4>
  ),
  code: ({ children }) => (
    <code className="font-body text-sm text-gold bg-navy px-1.5 py-0.5 rounded">
      {children}
    </code>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-gold pl-4 italic text-cream-dim my-4">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="border-line my-6" />,
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
  // Single submit path — runs the SSE stream
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
        // Keep any partial trailing event in the buffer for the next chunk.
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          const dataLine = event
            .split("\n")
            .find((l) => l.startsWith("data: "));
          if (!dataLine) continue;

          const payload = dataLine.slice(6).trim();
          if (payload === "[DONE]") {
            return;
          }

          try {
            const parsed = JSON.parse(payload);
            if (parsed.text) {
              setResponse((prev) => prev + parsed.text);
            } else if (parsed.tool) {
              setActiveTool(parsed.tool);
            }
          } catch {
            // Malformed event — skip silently
          }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") return;
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

        {/* Streamed response — rendered as Markdown */}
        {response && (
          <div className="atlas-response">
            <ReactMarkdown components={markdownComponents}>
              {response}
            </ReactMarkdown>
            {/* Blinking gold cursor while still streaming */}
            {loading && (
              <span className="inline-block w-[3px] h-5 ml-1 bg-gold animate-pulse align-text-bottom" />
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
