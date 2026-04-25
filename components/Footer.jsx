import TalantisMark from "./TalantisMark";

/**
 * Footer — minimal, mythic, just the essentials.
 */
export default function Footer() {
  return (
    <footer className="relative z-10 border-t border-line mt-32">
      <div className="max-w-7xl mx-auto px-6 md:px-12 py-12 flex flex-wrap items-end justify-between gap-6">
        <div className="flex items-center gap-4">
          <TalantisMark size={40} />
          <div className="font-display text-xl">
            T<em className="italic">a</em>lantis
          </div>
        </div>
        <div className="font-body text-xs tracking-wider-sm uppercase text-cream-dim text-right">
          A legendary island of talents<br />
          LA Hacks · Spring 2026
        </div>
      </div>
    </footer>
  );
}
