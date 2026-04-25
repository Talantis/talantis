"use client";

import { useState } from "react";

/**
 * AtlasFAB — floating action button that links to Atlas (the AI model).
 * Sits fixed in the bottom-right corner. Globe ellipses animate continuously.
 * On hover: scales up, shows "Chat with Atlas" label to the left.
 *
 * Props:
 *   href  — destination URL for Atlas (default "/explore")
 */
export default function AtlasFAB({ href = "/explore" }) {
  const [hovered, setHovered] = useState(false);

  return (
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
      {/* Tooltip label */}
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

      {/* Button */}
      <a
        href={href}
        aria-label="Chat with Atlas"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          width: 48,
          height: 48,
          borderRadius: "50%",
          background: "#0a1628",
          border: `1.5px solid ${hovered ? "#f5ecd7" : "#d4a548"}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          transform: hovered ? "scale(1.08)" : "scale(1)",
          transition: "transform 0.2s, border-color 0.2s",
          textDecoration: "none",
          flexShrink: 0,
        }}
      >
        <svg
          width="44"
          height="44"
          viewBox="0 0 56 56"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          {/* Outer sphere */}
          <circle cx="28" cy="28" r="18" stroke="#d4a548" strokeWidth="1.5" opacity="0.9" fill="none" />

          {/* Spinning horizontal ellipses */}
          <ellipse
            cx="28" cy="28" rx="18" ry="6"
            stroke="#d4a548" strokeWidth="1" opacity="0.55" fill="none"
            style={{
              transformOrigin: "28px 28px",
              animation: "atlasEllipse 3s linear infinite",
            }}
          />
          <ellipse
            cx="28" cy="28" rx="18" ry="6"
            stroke="#d4a548" strokeWidth="1" opacity="0.35" fill="none"
            style={{
              transformOrigin: "28px 28px",
              animation: "atlasEllipse 3s linear infinite reverse",
            }}
          />

          {/* Static vertical ellipse + crosshairs */}
          <ellipse cx="28" cy="28" rx="6" ry="18" stroke="#d4a548" strokeWidth="1" opacity="0.4" fill="none" />
          <line x1="10" y1="28" x2="46" y2="28" stroke="#d4a548" strokeWidth="1" opacity="0.25" />
          <line x1="28" y1="10" x2="28" y2="46" stroke="#d4a548" strokeWidth="1" opacity="0.25" />

          {/* Guiding star at north pole */}
          <g transform="translate(28,13)">
            <path
              d="M0 -3.5 L0.9 -0.9 L3.5 0 L0.9 0.9 L0 3.5 L-0.9 0.9 L-3.5 0 L-0.9 -0.9Z"
              fill="#f5ecd7"
            />
          </g>
        </svg>
      </a>

      <style>{`
        @keyframes atlasEllipse {
          0%   { transform: scaleX(1); }
          25%  { transform: scaleX(0.1); }
          50%  { transform: scaleX(-1); }
          75%  { transform: scaleX(-0.1); }
          100% { transform: scaleX(1); }
        }
      `}</style>
    </div>
  );
}