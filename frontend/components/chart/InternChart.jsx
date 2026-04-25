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

/**
 * InternChart — the money shot. Bar chart of interns per company.
 * Styled to the Talantis brand: gold bars on navy, cream labels.
 *
 * TODO: wire up to /api/internships once the backend is live.
 *
 * Props:
 *   data   — array of { company, count, logo? }
 */

// Placeholder data — swap for real API response
const PLACEHOLDER_DATA = [
  { company: "Stripe",  count: 23 },
  { company: "Meta",    count: 21 },
  { company: "Google",  count: 18 },
  { company: "Amazon",  count: 15 },
  { company: "Apple",   count: 12 },
  { company: "Plaid",   count: 9  },
  { company: "Brex",    count: 7  },
  { company: "Ramp",    count: 5  },
];

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { company, count } = payload[0].payload;
  return (
    <div className="bg-navy-soft border border-gold px-4 py-3 shadow-xl">
      <div className="font-display text-lg text-cream">{company}</div>
      <div className="font-body text-sm text-cream-dim">
        <span className="text-gold font-medium">{count}</span> interns
      </div>
    </div>
  );
}

export default function InternChart({ data = PLACEHOLDER_DATA }) {
  return (
    <div className="w-full h-[480px] bg-navy-soft border border-line p-8">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 20, left: 20, bottom: 40 }}>
          <XAxis
            dataKey="company"
            stroke="#c9b88a"
            tick={{ fill: "#c9b88a", fontFamily: "var(--font-inter-tight)", fontSize: 12 }}
            axisLine={{ stroke: "#2a3a5c" }}
            tickLine={false}
          />
          <YAxis
            stroke="#c9b88a"
            tick={{ fill: "#c9b88a", fontFamily: "var(--font-inter-tight)", fontSize: 12 }}
            axisLine={{ stroke: "#2a3a5c" }}
            tickLine={false}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "rgba(212, 165, 72, 0.08)" }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill="#d4a548" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
