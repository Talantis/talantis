"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

/**
 * UniversityFilter — dropdown to select a university.
 * On change, fires the onChange prop. Styled to the Talantis brand.
 *
 * TODO: replace the hardcoded list with a fetch from /api/universities.
 *
 * Props:
 *   value       — currently selected university (or "" for All)
 *   onChange    — fn(newValue)
 *   universities — array of strings (optional, has a placeholder list)
 */

const PLACEHOLDER_UNIVERSITIES = [
  "UCLA",
  "Stanford",
  "UC Berkeley",
  "USC",
  "MIT",
  "Carnegie Mellon",
  "UIUC",
  "Georgia Tech",
];

export default function UniversityFilter({
  value = "",
  onChange = () => {},
  universities = PLACEHOLDER_UNIVERSITIES,
}) {
  const [open, setOpen] = useState(false);

  const display = value || "All universities";

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-3 px-5 py-3 bg-navy-soft border border-line hover:border-gold transition-colors min-w-[240px] text-left"
      >
        <span className="flex-1 font-body text-cream">{display}</span>
        <ChevronDown
          size={16}
          className={`text-cream-dim transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute top-full mt-2 left-0 right-0 bg-navy-soft border border-line shadow-xl z-20 max-h-80 overflow-y-auto">
          <button
            onClick={() => {
              onChange("");
              setOpen(false);
            }}
            className="block w-full px-5 py-3 text-left font-body text-cream-dim hover:bg-navy hover:text-gold transition-colors"
          >
            All universities
          </button>
          {universities.map((uni) => (
            <button
              key={uni}
              onClick={() => {
                onChange(uni);
                setOpen(false);
              }}
              className="block w-full px-5 py-3 text-left font-body text-cream hover:bg-navy hover:text-gold transition-colors border-t border-line-soft"
            >
              {uni}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
