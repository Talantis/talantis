"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Loader2 } from "lucide-react";

/**
 * InternChart — the money shot. Bar chart of interns per company.
 * Styled to the Talantis brand: gold bars on navy, cream labels.
 *
 * Now wired to live data from the parent page.
 *
 * Props:
 *   data    — array of { company, count, logo_url? }
 *   loading — show a spinner instead of the chart
 *   error   — show an error message instead of the chart
 */

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { company, count } = payload[0].payload;
  return (
    <div className="bg-navy-soft border border-aqua px-4 py-3 shadow-xl">
      <div className="font-display text-lg text-cream">{company}</div>
      <div className="font-body text-sm text-cream-dim">
        <span className="text-aqua font-medium">{count}</span>{" "}
        intern{count === 1 ? "" : "s"}
      </div>
    </div>
  );
}

function PolishedBar({ x, y, width, height, fill, payload, maxCount }) {
  if (height <= 0 || width <= 0) return null;
  const isTop = payload?.count === maxCount;
  const r = Math.min(4, width / 2);
  const path = `M ${x},${y + r} Q ${x},${y} ${x + r},${y} L ${x + width - r},${y} Q ${x + width},${y} ${x + width},${y + r} L ${x + width},${y + height} L ${x},${y + height} Z`;
  return (
    <g filter={isTop ? "url(#topGlow)" : undefined}>
      <path d={path} fill={fill} />
      <rect
        x={x + 1.5}
        y={y + 1}
        width={Math.max(width - 3, 0)}
        height={1.5}
        fill={isTop ? "rgba(255, 248, 220, 0.85)" : "rgba(255, 240, 200, 0.7)"}
        rx={1}
      />
    </g>
  );
}
// ADDED — LogoTick using logo_url from backend, falls back to initials
function LogoTick({ x, y, payload, data }) {
  const item = data.find(d => d.company === payload.value);
  if (!item) return null;
  const size = 28;
  return (
    <foreignObject x={x - size / 2} y={y + 4} width={size} height={size}>
      <div
        xmlns="http://www.w3.org/1999/xhtml"
        title={item.company}
        style={{
          width: size,
          height: size,
          border: "1px solid rgba(245,240,232,0.15)",
          background: "rgba(255,255,255,0.06)",
          borderRadius: 4,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
        }}
      >
        <img
          src={item.logo_url}
          alt={item.company}
          style={{
            width: 18,
            height: 18,
            objectFit: "contain",
            opacity: 0.85,
          }}
          onError={(e) => {
            e.target.style.display = "none";
            e.target.parentNode.innerHTML = `<span style="font-size:7px;color:rgba(245,240,232,0.5)">${item.company.slice(0, 3).toUpperCase()}</span>`;
          }}
        />
      </div>
    </foreignObject>
  );
}

export default function InternChart({ data = [], loading = false, error = null }) {
  // ── Loading state ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="w-full h-[480px] bg-navy-soft border border-line p-8 flex flex-col items-center justify-center gap-4">
        <Loader2 size={32} className="animate-spin text-gold" />
        <div className="font-display italic text-cream-dim">
          Charting the shoreline...
        </div>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="w-full h-[480px] bg-navy-soft border border-line p-8 flex flex-col items-center justify-center gap-2">
        <div className="font-display text-lg text-cream">
          The map is dark.
        </div>
        <div className="font-body text-sm text-cream-dim">{error}</div>
      </div>
    );
  }

  // ── Empty state ────────────────────────────────────────────────────────
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-[480px] bg-navy-soft border border-line p-8 flex items-center justify-center">
        <div className="font-display italic text-cream-dim">
          No internships found for this filter.
        </div>
      </div>
    );
  }

  // ── Chart ──────────────────────────────────────────────────────────────
  const maxCount = Math.max(...data.map((d) => d.count));

  return (
    <div className="w-full h-[480px] bg-navy-soft border border-line p-8">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 20, left: 20, bottom: 60 }}>
          <defs>
            <filter id="topGlow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="6" in="SourceAlpha" result="blur" />
              <feFlood floodColor="#7dd6df" floodOpacity="0.7" result="glow" />
              <feComposite in="glow" in2="blur" operator="in" result="aquaGlow" />
              <feMerge>
                <feMergeNode in="aquaGlow" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <XAxis
            dataKey="company"
            stroke="#c9b88a"
            tick={(props) => <LogoTick {...props} data={data} />}
            axisLine={{ stroke: "#2a3a5c" }}
            tickLine={false}
            interval={0}
            height={60}
          />
          <YAxis
            stroke="#c9b88a"
            tick={{
              fill: "#c9b88a",
              fontFamily: "var(--font-inter-tight)",
              fontSize: 12,
            }}
            axisLine={{ stroke: "#2a3a5c" }}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "rgba(79, 179, 191, 0.08)" }}
          />
          <Bar dataKey="count" shape={(props) => <PolishedBar {...props} maxCount={maxCount} />}>
            {data.map((d, index) => (
              <Cell
                key={`cell-${index}`}
                fill={d.count === maxCount ? "#f0d175" : "#d4a548"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
