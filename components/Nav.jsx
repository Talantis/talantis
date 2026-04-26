"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import TalantisMark from "./TalantisMark";

/**
 * Nav — top navigation bar, present on every page.
 *
 * Layout: Talantis mark+wordmark flush left, Explore / Submit / About flush right.
 *
 * About behavior:
 *   - On the landing page, smooth-scrolls to the #cast section
 *   - On any other page, navigates to "/#cast" (browser handles the anchor)
 *
 * The graceful-scroll-vs-navigate decision is made at click time, not via plain
 * <a href="#cast">, because Next's <Link> with a hash works correctly only when
 * already on the target page.
 */
export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  function handleAboutClick(e) {
    e.preventDefault();

    // If we're already on the landing page, smooth-scroll
    if (pathname === "/") {
      const target = document.getElementById("cast");
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
    }

    // Otherwise, navigate to "/#cast" — the browser will jump to the anchor
    router.push("/#cast");
  }

  return (
    <header className="relative z-10 border-b border-line">
      <nav className="px-6 md:px-10 py-5 flex items-center justify-between">
        {/* Logo + wordmark — flush left */}
        <Link
          href="/"
          className="flex items-center gap-3 group"
        >
          <TalantisMark size={32} />
          <span className="font-display text-2xl text-cream">
            T<em className="italic">a</em>lantis
          </span>
        </Link>

        {/* Links — flush right */}
        <div className="flex items-center gap-6 md:gap-8">
          <Link
            href="/explore"
            className="font-body font-bold text-xs tracking-wider-md uppercase text-cream-dim hover:text-gold transition-colors"
          >
            Explore
          </Link>
          <Link
            href="/submit"
            className="font-body font-bold text-xs tracking-wider-md uppercase text-cream-dim hover:text-gold transition-colors"
          >
            Submit
          </Link>
          <button
            onClick={handleAboutClick}
            className="font-body font-bold text-xs tracking-wider-md uppercase text-cream-dim hover:text-gold transition-colors"
          >
            About
          </button>
        </div>
      </nav>
    </header>
  );
}