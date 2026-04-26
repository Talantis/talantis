"use client";

import { useState } from "react"; // EDITED — added useState
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Loader2, ChevronLeft, ChevronRight } from "lucide-react"; // EDITED — added chevrons

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { company, count } = payload[0].payload;
  return (
    <div className="bg-navy-soft border border-gold px-4 py-3 shadow-xl">
      <div className="font-display text-lg text-cream">{company}</div>
      <div className="font-body text-sm text-cream-dim">
        <span className="text-gold font-medium">{count}</span>{" "}
        intern{count === 1 ? "" : "s"}
      </div>
    </div>
  );
}

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
          style={{ width: 18, height: 18, objectFit: "contain", opacity: 0.85 }}
          onError={(e) => {
            e.target.style.display = "none";
            e.target.parentNode.innerHTML = `<span style="font-size:7px;color:rgba(245,240,232,0.5)">${item.company.slice(0, 3).toUpperCase()}</span>`;
          }}
        />
      </div>
    </foreignObject>
  );
}

const PAGE_SIZE = 12;

export default function InternChart({ data = [], loading = false, error = null }) {
  const [page, setPage] = useState(0); // ADDED — must be before early returns

  // ── Loading state ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="w-full h-[400px] bg-navy-soft border border-line rounded-2xl p-6 flex flex-col items-center justify-center gap-4">
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
      <div className="w-full h-[400px] bg-navy-soft border border-line rounded-2xl p-6 flex flex-col items-center justify-center gap-2">
        <div className="font-display text-lg text-cream">The map is dark.</div>
        <div className="font-body text-sm text-cream-dim">{error}</div>
      </div>
    );
  }

  // ── Empty state ────────────────────────────────────────────────────────
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-[400px] bg-navy-soft border border-line rounded-2xl p-6 flex items-center justify-center">
        <div className="font-display italic text-cream-dim">
          No internships found for this filter.
        </div>
      </div>
    );
  }

  // ── Pagination ─────────────────────────────────────────────────────────
  const totalPages = Math.ceil(data.length / PAGE_SIZE);
  const pageData = data.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  // ── Chart ──────────────────────────────────────────────────────────────
  return (
    <div className="w-full bg-navy-soft border border-line rounded-2xl p-6">
      <div className="h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={pageData} margin={{ top: 20, right: 20, left: 20, bottom: 60 }}>
            <XAxis
              dataKey="company"
              stroke="#c9b88a"
              tick={(props) => <LogoTick {...props} data={pageData} />}
              axisLine={{ stroke: "#2a3a5c" }}
              tickLine={false}
              interval={0}
              height={60}
            />
            <YAxis
              stroke="#f5f0e8"
              tick={{
                fill: "#f5f0e8",
                fontFamily: "var(--font-inter-tight)",
                fontSize: 12,
              }}
              axisLine={{ stroke: "#f5f0e8", strokeOpacity: 0.25 }}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ fill: "rgba(212, 165, 72, 0.08)" }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} background={{ fill: "transparent", cursor: "pointer" }}>
              {pageData.map((_, index) => (
                <Cell key={`cell-${index}`} fill="#d4a548" />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ADDED — pagination controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-6 mt-4 pt-4 border-t border-line">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="flex items-center gap-1.5 font-body text-xs uppercase tracking-wider text-cream-dim hover:text-gold transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={14} />
            Prev
          </button>
          <span className="font-body text-xs text-cream-dim">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="flex items-center gap-1.5 font-body text-xs uppercase tracking-wider text-cream-dim hover:text-gold transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}