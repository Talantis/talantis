"use client";

import { useEffect, useState } from "react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import InternChart from "@/components/chart/InternChart";
import UniversityFilter from "@/components/chart/UniversityFilter";

// Clearbit's free Logo API was shut down — rewrite the seeded URLs
// to Google's S2 favicon service, which is free and needs no key.
function rewriteLogoUrl(url) {
  if (!url) return url;
  const match = url.match(/logo\.clearbit\.com\/([^/?#]+)/);
  if (!match) return url;
  return `https://www.google.com/s2/favicons?domain=${match[1]}&sz=128`;
}

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
        let rows;
        if (!university) {
          const aggregated = (data || []).reduce((acc, r) => {
            const key = r.company;
            if (!acc[key]) {
              acc[key] = {
                company: r.company,
                count: 0,
                logo_url: rewriteLogoUrl(r.logo_url),
              };
            }
            acc[key].count += Number(r.intern_count) || 0;
            return acc;
          }, {});

          rows = Object.values(aggregated)
            .sort((a, b) => a.company.localeCompare(b.company))
            .slice(0, 12);
        } else {
          rows = (data || [])
            .map((r) => ({
              company: r.company,
              count: Number(r.intern_count) || 0,
              logo_url: rewriteLogoUrl(r.logo_url),
            }))
            .sort((a, b) => a.company.localeCompare(b.company))
            .slice(0, 12);
        }

        setChartData(rows);
      })
      .catch((err) => {
        console.error("Failed to load chart data:", err);
        setChartError(err.message);
        setChartData([]);
      })
      .finally(() => setChartLoading(false));
  }, [university]);

  // Derived metrics from chartData
  const totalHires = chartData.reduce((sum, r) => sum + r.count, 0);
  const topCompany = chartData.length
    ? chartData.reduce((a, b) => (a.count > b.count ? a : b))
    : null;
  const avgHires = chartData.length
    ? (totalHires / chartData.length).toFixed(1)
    : "—";

  return (
    <>
      <Nav />

      <main>
        {/* ============================================================
            EXPLORE — Tightened layout that fits a typical 900-1080px
            viewport without scroll. Padding, font sizes, and chart
            height are all tuned for "everything visible at first glance"
            instead of dramatic mythic spacing.
            ============================================================ */}
        <section className="max-w-7xl mx-auto px-6 md:px-12 pt-6 pb-4">
          <p className="font-body italic text-base md:text-lg text-cream-dim max-w-3xl leading-snug">
            The map exists. It just hasn&rsquo;t been drawn yet.
            Ask Atlas where the talent is hiding.
          </p>
        </section>

        {/* ============================================================
            METRICS CARDS — three rounded cards, tighter padding
            ============================================================ */}
        <section className="max-w-7xl mx-auto px-6 md:px-12 pb-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

            {/* Total Hires */}
            <div className="rounded-2xl" style={{
              background: "#13243d",
              border: "1px solid rgba(255,255,255,0.1)",
              padding: "20px 24px",
            }}>
              <div className="flex items-center gap-3 mb-2">
                <div style={{
                  background: "rgba(27,174,148,0.15)",
                  borderRadius: "10px",
                  padding: "8px",
                  display: "flex",
                }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#5bc4c0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                </div>
                <span className="font-body text-sm text-cream-dim">Total Hires</span>
              </div>
              <div className="font-display text-4xl text-cream font-bold">
                {chartLoading ? "—" : totalHires}
              </div>
            </div>

            {/* Top Company */}
            <div className="rounded-2xl" style={{
              background: "#13243d",
              border: "1px solid rgba(255,255,255,0.1)",
              padding: "20px 24px",
            }}>
              <div className="flex items-center gap-3 mb-2">
                <div style={{
                  background: "rgba(27,174,148,0.15)",
                  borderRadius: "10px",
                  padding: "8px",
                  display: "flex",
                }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#5bc4c0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="8" r="6"/>
                    <path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>
                  </svg>
                </div>
                <span className="font-body text-sm text-cream-dim">Top Company</span>
              </div>
              <div className="font-display text-3xl text-cream font-bold leading-tight">
                {chartLoading ? "—" : topCompany?.company ?? "—"}
              </div>
              {topCompany && (
                <div className="font-body text-xs mt-1" style={{ color: "#1bae94" }}>
                  {topCompany.count} hires
                </div>
              )}
            </div>

            {/* Average Hires */}
            <div className="rounded-2xl" style={{
              background: "#13243d",
              border: "1px solid rgba(255,255,255,0.1)",
              padding: "20px 24px",
            }}>
              <div className="flex items-center gap-3 mb-2">
                <div style={{
                  background: "rgba(27,174,148,0.15)",
                  borderRadius: "10px",
                  padding: "8px",
                  display: "flex",
                }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#5bc4c0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
                    <polyline points="16 7 22 7 22 13"/>
                  </svg>
                </div>
                <span className="font-body text-sm text-cream-dim">Average Hires</span>
              </div>
              <div className="font-display text-4xl text-cream font-bold">
                {chartLoading ? "—" : avgHires}
              </div>
            </div>

          </div>
        </section>

        {/* ============================================================
            FILTER + CHART
            Atlas's dedicated section is gone — the FAB is the entry point.
            ============================================================ */}
        <section className="max-w-7xl mx-auto px-6 md:px-12 pb-12">
          <div className="mb-3 flex items-center gap-6">
            <span className="font-body italic text-xs tracking-wider-md uppercase text-gold">
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

          <div className="mt-2 font-body italic text-xs text-cream-dim">
            {university
              ? `Internships from ${university} · Summer 2024`
              : "Top hiring companies · Summer 2024"}
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
