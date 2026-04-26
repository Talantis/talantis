"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

/**
 * YearFilter — dropdown to select a year. Mirrors UniversityFilter's API.
 *
 * Props:
 *   value    — currently selected year (number) or "" for All years
 *   onChange — fn(newValue)
 *   years    — array of numbers (defaults to 2021–2025)
 */

const DEFAULT_YEARS = [2021, 2022, 2023, 2024, 2025];

export default function YearFilter({
  value = "",
  onChange = () => {},
  years = DEFAULT_YEARS,
}) {
  const [open, setOpen] = useState(false);

  const display = value === "" ? "All years" : String(value);

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-3 px-5 py-3 bg-navy-soft border border-line rounded-xl hover:border-gold transition-colors min-w-[160px] text-left"
      >
        <span className="flex-1 font-body text-cream">{display}</span>
        <ChevronDown
          size={16}
          className={`text-cream-dim transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute top-full mt-2 left-0 right-0 bg-navy-soft border border-line rounded-xl shadow-xl z-20 max-h-80 overflow-y-auto">
          <button
            onClick={() => {
              onChange("");
              setOpen(false);
            }}
            className="block w-full px-5 py-3 text-left font-body text-cream-dim hover:bg-navy hover:text-gold transition-colors"
          >
            All years
          </button>
          {years.map((y) => (
            <button
              key={y}
              onClick={() => {
                onChange(y);
                setOpen(false);
              }}
              className="block w-full px-5 py-3 text-left font-body text-cream hover:bg-navy hover:text-gold transition-colors border-t border-line-soft"
            >
              {y}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
