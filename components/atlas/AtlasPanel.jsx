"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, MessageSquarePlus, X } from "lucide-react";
import ReactMarkdown from "react-markdown";

/**
 * AtlasPanel — the chat experience, sized for the FAB popup container.
 *
 * Owns its own conversation transcript, persists to localStorage so refreshes
 * don't lose context. The dropdown elsewhere on the page does NOT reset the
 * chat — Atlas reasons about universities through tool calls in conversation.
 *
 * SSE protocol from POST /api/insights:
 *   data: {"text": "..."}    text token → append
 *   data: {"tool": "name"}   tool indicator
 *   data: {"error": "msg"}   error to display
 *   data: [DONE]              end of stream
 *
 * Props:
 *   onClose — called when the user clicks the X to close the panel
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

const STORAGE_KEY = "talantis.atlas.chat";

function loadTranscript() {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveTranscript(messages) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  } catch {
    /* quota or write error — silent no-op */
  }
}

function clearTranscript() {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Markdown component overrides — sized for the panel (smaller than full page)
// ────────────────────────────────────────────────────────────────────────────
const markdownComponents = {
  p: ({ children }) => (
    <p className="font-body text-sm leading-relaxed text-cream mb-2.5 last:mb-0">
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
    <ul className="list-none space-y-1 my-2 pl-0">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-none space-y-1 my-2 pl-0">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="font-body text-sm leading-relaxed text-cream pl-4 relative before:content-['✦'] before:absolute before:left-0 before:text-gold before:text-[10px] before:top-1.5">
      {children}
    </li>
  ),
  code: ({ children }) => (
    <code className="font-body text-xs text-gold bg-navy px-1 py-0.5 rounded">
      {children}
    </code>
  ),
};

export default function AtlasPanel({ onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState("");
  const [activeTool, setActiveTool] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const abortRef = useRef(null);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  // Restore transcript on mount
  useEffect(() => {
    setMessages(loadTranscript());
    // Auto-focus the input when the panel opens
    setTimeout(() => inputRef.current?.focus(), 100);
  }, []);

  // Persist whenever messages change
  useEffect(() => {
    if (messages.length > 0) saveTranscript(messages);
  }, [messages]);

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streaming, activeTool]);

  // Cancel any in-flight request on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  async function askAtlas(question) {
    const trimmed = question?.trim();
    if (!trimmed || loading) return;

    const priorHistory = messages;
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setStreaming("");
    setActiveTool(null);
    setError(null);
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    let accumulated = "";
    let hadError = false;

    try {
      const res = await fetch("/api/insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, history: priorHistory }),
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
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          const dataLine = event
            .split("\n")
            .find((l) => l.startsWith("data: "));
          if (!dataLine) continue;

          const payload = dataLine.slice(6).trim();
          if (payload === "[DONE]") continue;

          try {
            const parsed = JSON.parse(payload);
            if (parsed.text) {
              accumulated += parsed.text;
              setStreaming(accumulated);
            } else if (parsed.tool) {
              setActiveTool(parsed.tool);
            } else if (parsed.error) {
              setError(parsed.error);
              hadError = true;
            }
          } catch {
            /* skip malformed event */
          }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") {
        setMessages(priorHistory);
        return;
      }
      console.error("Atlas streaming error:", err);
      setError(err.message || "Atlas couldn't reach the data.");
      hadError = true;
    } finally {
      setLoading(false);
      setActiveTool(null);
      abortRef.current = null;

      if (accumulated) {
        setMessages((prev) => [...prev, { role: "assistant", content: accumulated }]);
      }
      setStreaming("");
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

  function handleNewConversation() {
    if (loading && abortRef.current) abortRef.current.abort();
    setMessages([]);
    setStreaming("");
    setActiveTool(null);
    setError(null);
    clearTranscript();
  }

  const isEmpty = messages.length === 0 && !streaming && !error;

  return (
    <div className="flex flex-col h-full bg-navy-soft border border-line shadow-2xl">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-line flex-shrink-0">
        <div className="flex-1">
          <div className="font-body text-lg text-cream leading-tight">
            Atlas
          </div>
          <div className="font-body italic text-[10px] tracking-wider-md uppercase text-gold">
            The Guide
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={handleNewConversation}
            className="font-body italic text-[10px] tracking-wider-md uppercase text-[#5bc4c0] transition-colors flex items-center gap-1.5"
            title="Clear conversation"
          >
            <MessageSquarePlus size={12} />
            <span>New</span>
          </button>
        )}
        <button
          onClick={onClose}
          className="text-cream-dim hover:text-gold transition-colors p-1 -m-1"
          aria-label="Close Atlas"
        >
          <X size={18} />
        </button>
      </div>

      {/* ── Conversation ────────────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-5 py-4 space-y-4 min-h-0"
      >
        {/* Empty — show suggestions */}
        {isEmpty && (
          <div className="space-y-3">
            <p className="font-body italic text-sm text-cream-dim">
              &ldquo;Ask me about the shape of talent. Where it flows, where it
              pools, where it hides.&rdquo;
            </p>
            <div className="flex flex-col gap-2 pt-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSuggestion(s)}
                  className="text-left text-xs px-3 py-2.5 bg-navy border border-line-soft hover:border-gold text-cream-dim hover:text-gold transition-colors leading-snug"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Committed messages */}
        {messages.map((msg, idx) =>
          msg.role === "user" ? (
            <UserMessage key={idx} content={msg.content} />
          ) : (
            <AssistantMessage key={idx} content={msg.content} />
          )
        )}

        {/* In-progress assistant message */}
        {(streaming || (loading && !error)) && (
          <AssistantMessage
            content={streaming}
            inProgress
            activeTool={activeTool}
          />
        )}

        {/* Error */}
        {error && (
          <div className="font-body italic text-cream-dim border-l-2 border-red-500/50 pl-3 py-1">
            <div className="text-xs text-cream">
              Atlas couldn&rsquo;t reach the shore.
            </div>
            <div className="text-[10px] text-cream-dim/80 mt-1.5 font-body not-italic break-words">
              {error}
            </div>
          </div>
        )}
      </div>

      {/* ── Input ───────────────────────────────────────────────────────── */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 border-t border-line px-3 py-3 flex-shrink-0"
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={loading ? "Atlas is thinking..." : "Ask Atlas..."}
          disabled={loading}
          className="flex-1 bg-transparent border-none outline-none font-body text-sm text-cream placeholder:text-cream-dim px-3 py-1.5 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="flex items-center gap-1.5 px-3.5 py-1.5 bg-gold text-navy text-sm font-body font-medium hover:bg-gold-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span>{loading ? "..." : "Ask"}</span>
          {!loading && <Send size={12} />}
        </button>
      </form>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Message components
// ════════════════════════════════════════════════════════════════════════════

function UserMessage({ content }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] bg-navy border-l-2 border-gold px-3.5 py-2">
        <div className="font-body italic text-[10px] tracking-wider-md uppercase text-gold mb-1">
          You
        </div>
        <div className="font-body text-xs leading-relaxed text-cream whitespace-pre-wrap">
          {content}
        </div>
      </div>
    </div>
  );
}

function AssistantMessage({ content, inProgress = false, activeTool = null }) {
  return (
    <div className="flex flex-col">
      <div className="font-body italic text-[10px] tracking-wider-md uppercase text-gold mb-1.5">
        Atlas
      </div>

      {inProgress && activeTool && (
        <div className="flex items-center gap-1.5 mb-1.5 font-body italic text-[10px] tracking-wider-md uppercase text-gold">
          <Loader2 size={10} className="animate-spin" />
          <span>{TOOL_LABELS[activeTool] || activeTool}</span>
        </div>
      )}

      {inProgress && !content && !activeTool && (
        <div className="flex items-center gap-2 font-body italic text-sm text-cream-dim">
          <Loader2 size={12} className="animate-spin text-gold" />
          <span>mapping the shore...</span>
        </div>
      )}

      {content && (
        <div className="atlas-response">
          <ReactMarkdown components={markdownComponents}>
            {content}
          </ReactMarkdown>
          {inProgress && (
            <span className="inline-block w-[2px] h-3.5 ml-0.5 bg-gold animate-pulse align-text-bottom" />
          )}
        </div>
      )}
    </div>
  );
}