import Link from "next/link";
import TalantisMark from "./TalantisMark";

/**
 * Nav — the top navigation bar. Appears on every page.
 * Talantis mark on the left, minimal links on the right.
 * Mythic and restrained, not a marketing header.
 */
export default function Nav() {
  return (
    <header className="relative z-10 border-b border-line">
      <nav className="max-w-7xl mx-auto px-6 md:px-12 py-6 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-3 group"
        >
          <TalantisMark size={32} />
          <span className="font-display text-2xl text-cream">
            T<em className="italic">a</em>lantis
          </span>
        </Link>

        <div className="flex items-center gap-8">
          <Link
            href="/explore"
            className="font-body font-bold text-xs tracking-wider-md uppercase text-cream-dim hover:text-gold transition-colors"
          >
            Explore
          </Link>
          <Link
            href="/#atlas"
            className="font-display font-bold italic text-sm tracking-wider-md uppercase text-cream-dim hover:text-gold transition-colors"
          >
            Ask Atlas
          </Link>
        </div>
      </nav>
    </header>
  );
}
