"use client";

import { useEffect, useState } from "react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import InternChart from "@/components/chart/InternChart";
import UniversityFilter from "@/components/chart/UniversityFilter";
import AskAtlas from "@/components/atlas/AskAtlas";

export default function ExplorePage() {
  const [university, setUniversity] = useState("");

  // ───────────────────────────────────────────────────────────────────────
  // Live data fetching
  // ───────────────────────────────────────────────────────────────────────
  const [universityList, setUniversityList] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [chartLoading, setChartLoading] = useState(true);
  const [chartError, setChartError] = useState(null);

  // Fetch the dropdown list once on mount
  useEffect(() => {
    fetch("/api/universities")
      .then((r) => r.json())
      .then((data) => {
        // The backend returns ["UCLA", "Stanford", ...] — a flat string array
        if (Array.isArray(data)) {
          setUniversityList(data);
        }
      })
      .catch((err) => console.error("Failed to load universities:", err));
  }, []);

  // Fetch chart data whenever the selected university changes
  useEffect(() => {
    setChartLoading(true);
    setChartError(null);

    const url = university
      ? `/api/companies?university=${encodeURIComponent(university)}`
      : "/api/companies";

    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`API returned ${r.status}`);
        return r.json();
      })
      .then((data) => {
        // Backend returns rows like { company, logo_url, industry, university, intern_count }
        // The chart wants { company, count }. Take the top 12 for visual clarity.
        const rows = (data || [])
          .slice(0, 12)
          .map((r) => ({
            company: r.company,
            count: Number(r.intern_count) || 0,
            logo_url: r.logo_url,
          }));
        setChartData(rows);
      })
      .catch((err) => {
        console.error("Failed to load chart data:", err);
        setChartError(err.message);
        setChartData([]);
      })
      .finally(() => setChartLoading(false));
  }, [university]);

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
            Pick a university. See who&rsquo;s hiring their students.
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
            <UniversityFilter
              value={university}
              onChange={setUniversity}
              universities={universityList}
            />
          </div>

          <InternChart
            data={chartData}
            loading={chartLoading}
            error={chartError}
          />

          <div className="mt-4 font-display italic text-sm text-cream-dim">
            {university
              ? `Internships from ${university} · Summer 2024`
              : "Top hiring companies · Summer 2024"}
          </div>
        </section>

        {/* ============================================================
            ASK ATLAS
            Pass the selected university so Atlas has context
            ============================================================ */}
        <section className="max-w-4xl mx-auto px-6 md:px-12 pb-32">
          <div className="font-display italic text-sm tracking-wider-lg uppercase text-gold mb-6 flex items-center gap-4">
            <span className="w-10 h-px bg-gold" />
            <span>The Guide</span>
          </div>
          <h2 className="font-display text-4xl md:text-5xl mb-10">
            Ask <em>Atlas</em>.
          </h2>

          <AskAtlas university={university || null} />
        </section>
      </main>

      <Footer />
    </>
  );
}
