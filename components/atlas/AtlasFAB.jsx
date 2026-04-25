"use client";

import { useState, useEffect } from "react";
import AtlasPanel from "./AtlasPanel";

/**
 * AtlasFAB — floating action button + chat panel.
 *
 * Click toggles the chat panel. The button itself matches the brand
 * "cast section" treatment — a vertical rounded rectangle with navy
 * background, gold trim, the armillary celestial globe, and the
 * "Atlas" wordmark below. Animated ellipses on the globe are
 * preserved from the previous version.
 *
 * The panel opens upward from the button position. On mobile, the
 * panel takes full screen instead.
 */
export default function AtlasFAB() {
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(false);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <>
      {/* ─────────────────────────────────────────────────────────────────
          PANEL — the chat window. Opens upward from the FAB.
          On desktop: 380×600 anchored bottom-right above the button.
          On mobile: full screen for usable input.
          ───────────────────────────────────────────────────────────────── */}
      {open && (
        <div
          style={{
            position: "fixed",
            zIndex: 60,
            bottom: 28,
            right: 28,
          }}
          className="
            atlas-panel-container
            md:w-[380px] md:h-[600px]
          "
        >
          <AtlasPanel onClose={() => setOpen(false)} />
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          BUTTON — branded rounded rectangle. Hidden when panel is open
          on mobile (so the panel is full-screen). On desktop the
          button stays put behind/below the panel; we still hide it for
          a cleaner look.
          ───────────────────────────────────────────────────────────────── */}
      {!open && (
        <div
          style={{
            position: "fixed",
            bottom: 28,
            right: 28,
            zIndex: 50,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          {/* Tooltip label — only on desktop */}
          <span
            style={{
              background: "#0a1628",
              border: "1px solid #d4a548",
              color: "#f5ecd7",
              fontSize: 12,
              fontFamily: "var(--font-inter-tight, sans-serif)",
              whiteSpace: "nowrap",
              padding: "5px 10px",
              borderRadius: 6,
              opacity: hovered ? 1 : 0,
              transform: hovered ? "translateX(0)" : "translateX(6px)",
              transition: "opacity 0.2s, transform 0.2s",
              pointerEvents: "none",
              userSelect: "none",
            }}
          >
            Chat with Atlas
          </span>

          {/* Button itself */}
          <button
            onClick={() => setOpen(true)}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            aria-label="Chat with Atlas"
            style={{
              width: 96,
              height: 96,
              borderRadius: 18,
              // Elevated navy — slightly lighter than the page bg (#0a1628) so
              // the button reads as a distinct surface without needing a border.
              background: hovered ? "#1a3358" : "#142847",
              border: "none",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 4,
              padding: "8px 0 10px",
              cursor: "pointer",
              transform: hovered ? "scale(1.05)" : "scale(1)",
              transition: "transform 0.2s, background 0.2s, box-shadow 0.2s",
              flexShrink: 0,
              // Drop shadow does the visual lifting — replaces the gold border
              // as the "this is a button" affordance.
              boxShadow: hovered
                ? "0 12px 32px rgba(0,0,0,0.55)"
                : "0 8px 24px rgba(0,0,0,0.45)",
            }}
          >
            {/* Armillary globe + star + plinth */}
            <svg
              width="50"
              height="50"
              viewBox="0 0 56 56"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
              style={{ flexShrink: 0 }}
            >
              {/* Outer sphere */}
              <circle
                cx="28" cy="30" r="14"
                stroke="#d4a548" strokeWidth="1.4"
                opacity="0.9" fill="none"
              />

              {/* Animated horizontal ellipses (the magic) */}
              <ellipse
                cx="28" cy="30" rx="14" ry="4.5"
                stroke="#d4a548" strokeWidth="1" opacity="0.55" fill="none"
                style={{
                  transformOrigin: "28px 30px",
                  animation: "atlasEllipse 3s linear infinite",
                }}
              />
              <ellipse
                cx="28" cy="30" rx="14" ry="4.5"
                stroke="#d4a548" strokeWidth="1" opacity="0.35" fill="none"
                style={{
                  transformOrigin: "28px 30px",
                  animation: "atlasEllipse 3s linear infinite reverse",
                }}
              />

              {/* Static vertical ellipse + meridian for depth */}
              <ellipse
                cx="28" cy="30" rx="4.5" ry="14"
                stroke="#d4a548" strokeWidth="1" opacity="0.4" fill="none"
              />
              <line
                x1="14" y1="30" x2="42" y2="30"
                stroke="#d4a548" strokeWidth="1" opacity="0.25"
              />

              {/* Atlas figure plinth — shoulders lifting the globe */}
              <path
                d="M 19 47 L 22 43 L 25 44 L 28 43 L 31 44 L 34 43 L 37 47 Z"
                fill="#d4a548"
                opacity="0.9"
              />

              {/* Guiding star at top of globe (white/cream) */}
              <g transform="translate(28, 13)">
                <path
                  d="M 0 -3.5 L 0.9 -0.9 L 3.5 0 L 0.9 0.9 L 0 3.5 L -0.9 0.9 L -3.5 0 L -0.9 -0.9 Z"
                  fill="#f5ecd7"
                />
              </g>
            </svg>

            {/* "Atlas" wordmark — display font, mixed white/gold like the logo */}
            <span
              style={{
                fontFamily: "var(--font-cormorant), 'Cormorant Garamond', serif",
                fontSize: 16,
                lineHeight: 1,
                color: "#f5ecd7",
                letterSpacing: "0.02em",
                userSelect: "none",
              }}
            >
              Atl<span style={{ color: "#d4a548", fontStyle: "italic" }}>a</span>s
            </span>
          </button>
        </div>
      )}

      <style>{`
        @keyframes atlasEllipse {
          0%   { transform: scaleX(1); }
          25%  { transform: scaleX(0.1); }
          50%  { transform: scaleX(-1); }
          75%  { transform: scaleX(-0.1); }
          100% { transform: scaleX(1); }
        }

        /* Mobile: panel takes full screen */
        @media (max-width: 767px) {
          .atlas-panel-container {
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            width: 100% !important;
            height: 100% !important;
          }
        }
      `}</style>
    </>
  );
}