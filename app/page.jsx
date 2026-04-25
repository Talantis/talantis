import Link from "next/link";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import TalantisLogo from "@/components/TalantisLogo";
import AtlasLogo from "@/components/AtlasLogo";
import { ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <>
      <Nav />

      <main>
        {/* ============================================================
            HERO — the mythic opening. Pitch line + primary mark.
            ============================================================ */}
        <section className="min-h-[85vh] flex flex-col justify-center px-6 md:px-12 max-w-7xl mx-auto py-20">
          <div className="font-display italic text-sm tracking-wider-lg uppercase text-gold mb-10 flex items-center gap-4">
            <span>✦</span>
            <span>A legendary island of talents</span>
          </div>

          <h1 className="font-display text-hero mb-10">
            T<em className="italic">a</em>lantis.
          </h1>

          <p className="font-display italic text-xl md:text-3xl text-cream-dim max-w-3xl leading-snug mb-16">
            Every company is looking in the same places.<br />
            We show you the ones no one has mapped yet.
          </p>

          <div className="flex flex-wrap gap-6">
            <Link
              href="/explore"
              className="inline-flex items-center gap-3 px-8 py-4 bg-gold text-navy font-body font-medium hover:bg-gold-light transition-colors group"
            >
              <span>Enter the island</span>
              <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              href="#atlas"
              className="inline-flex items-center gap-3 px-8 py-4 border border-line text-cream font-body font-medium hover:border-gold hover:text-gold transition-colors"
            >
              <span>Ask Atlas</span>
            </Link>
          </div>

          {/* Scroll indicator */}
          <div className="mt-20 w-px h-12 bg-gradient-to-b from-transparent to-gold opacity-50 mx-auto animate-pulse-soft" />
        </section>

        {/* ============================================================
            THE CAST — Talantis × Atlas side by side
            ============================================================ */}
        <section className="border-t border-line px-6 md:px-12 max-w-7xl mx-auto py-32">
          <div className="font-display italic text-sm tracking-wider-lg uppercase text-gold mb-6 flex items-center gap-4">
            <span className="w-10 h-px bg-gold" />
            <span>The Cast</span>
          </div>

          <p className="font-display text-2xl md:text-4xl leading-tight text-cream max-w-3xl mb-20">
            This brand has <em>two faces</em> — an island and its guide.
            Talantis is the world you enter. Atlas is the voice that walks it with you.
          </p>

          <div className="grid md:grid-cols-2 gap-px bg-line border border-line">
            {/* Talantis */}
            <div className="bg-navy-soft p-12 flex flex-col items-center text-center gap-6">
              <div className="font-display italic text-xs tracking-wider-lg uppercase text-gold">
                — The Island —
              </div>
              <TalantisLogo size={160} />
              <div className="font-display text-5xl">
                T<em className="italic">a</em>lantis
              </div>
              <div className="font-display italic text-lg text-cream-dim">
                A legendary island of talents.
              </div>
            </div>

            {/* Atlas */}
            <div id="atlas" className="bg-navy-soft p-12 flex flex-col items-center text-center gap-6">
              <div className="font-display italic text-xs tracking-wider-lg uppercase text-gold">
                — The Guide —
              </div>
              <AtlasLogo size={160} />
              <div className="font-display text-5xl">
                Atl<em className="italic">a</em>s
              </div>
              <div className="font-display italic text-lg text-cream-dim">
                The titan who maps the island.
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================
            THE STORY — brand thesis
            ============================================================ */}
        <section className="border-t border-line px-6 md:px-12 max-w-7xl mx-auto py-32">
          <div className="font-display italic text-sm tracking-wider-md uppercase text-gold mb-10">
            § 01 · The Story
          </div>

          <div className="max-w-3xl space-y-8">
            <p className="font-display text-2xl leading-relaxed text-cream">
              Every summer, thousands of students land internships across the world.
              Their journeys are <em>scattered</em> — buried in LinkedIn posts, filtered
              through private group chats, known only to those in the room.
            </p>
            <p className="font-display text-2xl leading-relaxed text-cream">
              But the patterns are there. Which schools feed which companies.
              Which pipelines are growing. Which <em>hidden islands</em> of talent the
              industry hasn't yet discovered.
            </p>
            <p className="font-display text-2xl leading-relaxed text-cream">
              Talantis is that island, made visible.
            </p>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
