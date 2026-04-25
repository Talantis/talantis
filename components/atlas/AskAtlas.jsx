"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import AtlasLogo from "@/components/AtlasLogo";

/**
 * AskAtlas — natural language query interface.
 * The "wow factor" of the product. Users type a question, Atlas answers
 * with streaming text grounded in the dataset.
 *
 * TODO: wire up to the FastAPI backend at /api/ask-atlas.
 * Use EventSource (SSE) for streaming tokens as they arrive.
 */

// Pre-canned example prompts for the demo
const SUGGESTIONS = [
  "Which fintechs hire most from UCLA?",
  "Where are Meta's top competitors finding talent?",
  "What schools are emerging for AI startups?",
];

export default function AskAtlas() {
  const [input, setInput] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim()) return;

    setLoading(true);
    setResponse("");

    // ============================================================
    // TODO: Replace this stub with real SSE streaming to the backend.
    // Example:
    //   const eventSource = new EventSource(`/api/ask-atlas?q=${encodeURIComponent(input)}`);
    //   eventSource.onmessage = (e) => {
    //     const { text } = JSON.parse(e.data);
    //     setResponse(prev => prev + text);
    //   };
    //   eventSource.addEventListener('done', () => {
    //     eventSource.close();
    //     setLoading(false);
    //   });
    // ============================================================
    setTimeout(() => {
      setResponse(
        "I've mapped the shores. Three universities stand out: UIUC, Georgia Tech, and UCLA — each one feeding Stripe, Plaid, and Brex in meaningful numbers, while your own recruiting shows fewer than two hires from any of them. UIUC in particular has sent 18 interns to your peers this year. An untapped coast, if you're looking."
      );
      setLoading(false);
    }, 1200);
  }

  return (
    <div className="bg-navy-soft border border-line">
      {/* Header */}
      <div className="flex items-center gap-4 px-8 py-6 border-b border-line">
        <AtlasLogo size={40} />
        <div>
          <div className="font-display text-xl text-cream">Atlas</div>
          <div className="font-display italic text-xs tracking-wider-md uppercase text-gold">
            The Guide
          </div>
        </div>
      </div>

      {/* Conversation area */}
      <div className="px-8 py-10 min-h-[200px]">
        {!response && !loading && (
          <div className="space-y-4">
            <p className="font-display italic text-lg text-cream-dim">
              "Ask me about the shape of talent. Where it flows, where it pools, where it hides."
            </p>
            <div className="flex flex-wrap gap-3 pt-4">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  className="text-sm px-4 py-2 bg-navy border border-line-soft hover:border-gold text-cream-dim hover:text-gold transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {loading && (
          <div className="font-display italic text-cream-dim">
            Atlas is mapping the shore<span className="inline-block animate-pulse">...</span>
          </div>
        )}

        {response && (
          <div className="font-display text-lg leading-relaxed text-cream">
            {response}
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
          placeholder="Ask Atlas..."
          className="flex-1 bg-transparent border-none outline-none font-body text-cream placeholder:text-cream-dim px-4 py-2"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="flex items-center gap-2 px-5 py-2 bg-gold text-navy font-body font-medium hover:bg-gold-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span>Ask</span>
          <Send size={14} />
        </button>
      </form>
    </div>
  );
}
