/**
 * TalantisLogo — the premium mark (compass + island + reflection + star).
 * Use for hero placements, pitch decks, marketing moments.
 * For browser tab / small contexts, use /public/favicon files instead.
 *
 * Props:
 *   size        — pixel width/height (default 280)
 *   className   — extra Tailwind classes
 */
export default function TalantisLogo({ size = 280, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 280 280"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Talantis"
    >
      <rect width="280" height="280" rx="62" fill="#0a1628" />
      {/* Compass rings */}
      <circle cx="140" cy="140" r="120" stroke="#d4a548" strokeWidth="1" opacity="0.4" />
      <circle cx="140" cy="140" r="100" stroke="#d4a548" strokeWidth="0.5" opacity="0.25" />
      {/* Cardinal tick marks */}
      <g stroke="#d4a548" strokeWidth="1" opacity="0.6">
        <line x1="140" y1="20" x2="140" y2="32" />
        <line x1="140" y1="248" x2="140" y2="260" />
        <line x1="20" y1="140" x2="32" y2="140" />
        <line x1="248" y1="140" x2="260" y2="140" />
      </g>
      {/* Horizon */}
      <line
        x1="40" y1="140" x2="240" y2="140"
        stroke="#d4a548" strokeWidth="0.5" opacity="0.3"
        strokeDasharray="2,4"
      />
      {/* Island (above) */}
      <path
        d="M 70 140 L 90 125 L 105 110 L 118 95 L 128 85 L 140 70 L 152 82 L 162 92 L 175 108 L 188 120 L 200 132 L 210 140 Z"
        fill="#d4a548" opacity="0.95"
      />
      {/* Reflection (below) */}
      <path
        d="M 70 140 L 90 155 L 105 170 L 118 185 L 128 195 L 140 210 L 152 198 L 162 188 L 175 172 L 188 160 L 200 148 L 210 140 Z"
        fill="#d4a548" opacity="0.35"
      />
      {/* Star above the peak */}
      <g transform="translate(140, 60)">
        <path
          d="M 0 -8 L 2 -2 L 8 0 L 2 2 L 0 8 L -2 2 L -8 0 L -2 -2 Z"
          fill="#f5ecd7"
        />
      </g>
      {/* Water ripples */}
      <g stroke="#4fb3bf" strokeWidth="0.5" fill="none" opacity="0.4">
        <path d="M 60 155 Q 80 152, 100 155 T 140 155 T 180 155 T 220 155" />
        <path d="M 70 170 Q 90 167, 110 170 T 150 170 T 190 170 T 210 170" opacity="0.6" />
      </g>
    </svg>
  );
}