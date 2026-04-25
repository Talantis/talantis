/**
 * TalantisMark — the v5 Planted favicon rendered inline.
 * The T planted through the island. Use in nav bars, buttons,
 * small footer contexts — anywhere the full premium mark would be overkill.
 *
 * Each rendered instance gets unique SVG IDs to avoid collision when
 * multiple marks appear on the same page.
 *
 * Props:
 *   size        — pixel width/height (default 32)
 *   className   — extra Tailwind classes
 */
let instanceCount = 0;

export default function TalantisMark({ size = 32, className = "" }) {
  // Generate a unique ID per render so gradients don't collide across instances
  const id = ++instanceCount;
  const gradientId = `tal-water-${id}`;
  const clipId = `tal-clip-${id}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Talantis"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="55%" stopColor="#0a1628" />
          <stop offset="75%" stopColor="#0f1e3a" />
          <stop offset="100%" stopColor="#14264a" />
        </linearGradient>
        <clipPath id={clipId}>
          <rect width="32" height="32" rx="7" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clipId})`}>
        <rect width="32" height="32" fill={`url(#${gradientId})`} />
        {/* T — drawn first, island will cover its base */}
        <rect x="14.5" y="3" width="3" height="20" fill="#f5ecd7" />
        <rect x="8.5" y="3" width="15" height="2.4" fill="#f5ecd7" />
        <rect x="8.5" y="2" width="1.8" height="1" fill="#f5ecd7" />
        <rect x="21.7" y="2" width="1.8" height="1" fill="#f5ecd7" />
        <rect x="10" y="5.4" width="0.5" height="0.8" fill="#0a1628" />
        <rect x="21.5" y="5.4" width="0.5" height="0.8" fill="#0a1628" />
        {/* Island — covers the lower trunk of the T */}
        <path
          d="M 3 23 L 10 20 L 14 18 L 16 17.5 L 18 18 L 22 20 L 29 23 Z"
          fill="#d4a548"
        />
        {/* Water ripples */}
        <line x1="5" y1="26" x2="27" y2="26" stroke="#4fb3bf" strokeWidth="0.2" opacity="0.4" />
        <line x1="8" y1="28.5" x2="24" y2="28.5" stroke="#4fb3bf" strokeWidth="0.2" opacity="0.25" />
      </g>
    </svg>
  );
}
