/**
 * AtlasLogo — the armillary sphere mark (Atlas = the guide).
 * Use in the chat/query interface, email mocks, anywhere Atlas speaks.
 *
 * Props:
 *   size        — pixel width/height (default 280)
 *   className   — extra Tailwind classes
 */
export default function AtlasLogo({ size = 280, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 280 280"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Atlas"
    >
      <rect width="280" height="280" rx="62" fill="#0a1628" />
      {/* Celestial sphere */}
      <circle cx="140" cy="120" r="60" stroke="#d4a548" strokeWidth="2" opacity="0.8" fill="none" />
      <ellipse cx="140" cy="120" rx="60" ry="20" stroke="#d4a548" strokeWidth="1" opacity="0.5" fill="none" />
      <ellipse cx="140" cy="120" rx="60" ry="40" stroke="#d4a548" strokeWidth="1" opacity="0.4" fill="none" />
      <ellipse cx="140" cy="120" rx="20" ry="60" stroke="#d4a548" strokeWidth="1" opacity="0.5" fill="none" />
      <ellipse cx="140" cy="120" rx="40" ry="60" stroke="#d4a548" strokeWidth="1" opacity="0.4" fill="none" />
      {/* Atlas's shoulders lifting the sphere */}
      <path
        d="M 100 200 L 110 180 L 120 185 L 140 180 L 160 185 L 170 180 L 180 200 Z"
        fill="#d4a548" opacity="0.9"
      />
      {/* Guiding star */}
      <g transform="translate(140, 50)">
        <path
          d="M 0 -6 L 1.5 -1.5 L 6 0 L 1.5 1.5 L 0 6 L -1.5 1.5 L -6 0 L -1.5 -1.5 Z"
          fill="#f5ecd7"
        />
      </g>
    </svg>
  );
}
