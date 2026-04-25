"use client";

import { useState } from "react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import InternChart from "@/components/chart/InternChart";
import UniversityFilter from "@/components/chart/UniversityFilter";
import AskAtlas from "@/components/atlas/AskAtlas";

export default function ExplorePage() {
  const [university, setUniversity] = useState("");

  // TODO: fetch real data from the backend when university changes
  // const { data } = useSWR(`/api/internships?university=${university}`, fetcher);

  return (
    <>
      <Nav />

      <main>
        {/* ============================================================
            PAGE HEADER
            ============================================================ */}
        <section className="max-w-7xl mx-auto px-6 md:px-12 pt-20 pb-12">
          <div className="font-display italic text-sm tracking-wider-lg uppercase text-gold mb-6">
            — The Map —
          </div>
          <h1 className="font-display text-section mb-6">
            Where <em>talent</em> actually flows.
          </h1>
          <p className="font-display italic text-xl text-cream-dim max-w-2xl leading-snug">
            Pick a university. See who's hiring their students.
            Ask Atlas what it means.
          </p>
        </section>

        {/* ============================================================
            FILTER + CHART
            ============================================================ */}
        <section className="max-w-7xl mx-auto px-6 md:px-12 pb-20">
          <div className="mb-8 flex items-center gap-6">
            <span className="font-display italic text-xs tracking-wider-md uppercase text-gold">
              Filter by
            </span>
            <UniversityFilter value={university} onChange={setUniversity} />
          </div>

          <InternChart />

          <div className="mt-4 font-display italic text-sm text-cream-dim">
            {university
              ? `Internships from ${university} · Summer 2025`
              : "Top hiring companies · Summer 2025"}
          </div>
        </section>

        {/* ============================================================
            ASK ATLAS
            ============================================================ */}
        <section className="max-w-4xl mx-auto px-6 md:px-12 pb-32">
          <div className="font-display italic text-sm tracking-wider-lg uppercase text-gold mb-6 flex items-center gap-4">
            <span className="w-10 h-px bg-gold" />
            <span>The Guide</span>
          </div>
          <h2 className="font-display text-4xl md:text-5xl mb-10">
            Ask <em>Atlas</em>.
          </h2>

          <AskAtlas />
        </section>
      </main>

      <Footer />
    </>
  );
}
