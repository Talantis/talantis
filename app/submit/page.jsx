"use client";

import { useState } from "react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import { Send, Loader2, User, GraduationCap, Briefcase, Upload } from "lucide-react";

const COMPANIES = [
  "Adobe", "Airbnb", "Amazon", "Apple", "Figma",
  "Google", "LinkedIn", "Lyft", "Meta", "Microsoft",
  "Netflix", "Notion", "Nvidia", "Palantir", "Roblox",
  "Salesforce", "Snap", "SpaceX", "Stripe", "Uber",
];

const UNIVERSITIES = [
  "Carnegie Mellon", "Georgia Tech", "MIT", "Stanford", "UC Berkeley",
  "UCLA", "UIUC", "USC", "UT Austin", "UW Seattle",
];

const CATEGORIES = [
  "SWE", "PM", "Data", "Design", "Research", "Business", "Other",
];

const SEASONS = ["Summer", "Fall", "Winter", "Spring"];

const YEARS = ["2026", "2025", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016"];

const inputClass = `
  w-full bg-navy border border-line text-cream font-body text-sm px-4 py-3
  placeholder:text-cream focus:outline-none focus:border-gold transition-colors
`;

const selectClass = `
  w-full bg-navy border border-line text-cream font-body text-sm px-4 py-3
  focus:outline-none focus:border-gold transition-colors appearance-none cursor-pointer
`;

function SectionHeader({ icon: Icon, title }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <div style={{
        width: 36, height: 36, borderRadius: "50%",
        background: "rgba(91,196,192,0.12)",
        border: "1px solid rgba(91,196,192,0.25)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <Icon size={16} color="#5bc4c0" />
      </div>
      <h2 className="font-body text-lg text-cream">{title}</h2>
    </div>
  );
}

function Label({ children, hint }) {
  return (
    <label className="block font-body text-sm text-cream-dim mb-2">
      {children}
      {hint && (
        <span className="ml-2 font-body italic text-xs text-gold/70">{hint}</span>
      )}
    </label>
  );
}

export default function SubmitPage() {
  const [form, setForm] = useState({
    email: "", university: "", company: "", roleTitle: "",
    category: "", year: "", season: "",
  });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null); // ADDED

  function set(key, val) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const body = new FormData();
      Object.entries(form).forEach(([k, v]) => body.append(k, v));
      if (file) body.append("offer_letter", file);

      const res = await fetch("/api/submit", {
        method: "POST",
        body,
      });
      if (!res.ok) throw new Error(`Submission failed (${res.status})`);
      setSubmitted(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <>
        <Nav />
        <main className="min-h-[80vh] flex flex-col items-center justify-center px-6 text-center">
          <div className="font-body italic text-sm tracking-wider-lg uppercase text-gold mb-6">
            ✦ Charted
          </div>
          <h1 className="font-display text-5xl md:text-6xl mb-6">
            You&rsquo;re on the map.
          </h1>
          <p className="font-display italic text-xl text-cream-dim max-w-md leading-snug">
            Your internship has been added to the island. Atlas will remember.
          </p>
        </main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Nav />
      <main className="max-w-5xl mx-auto px-6 md:px-12 py-20">

        {/* Header */}
        <div className="text-center mb-16">
          <div className="font-body italic text-sm tracking-wider-lg uppercase text-gold mb-6 flex items-center justify-center gap-4">
            <span className="w-10 h-px bg-gold" />
            <span>Submit Internship</span>
            <span className="w-10 h-px bg-gold" />
          </div>
          <h1 className="font-display text-5xl md:text-6xl mb-6">
            Join the <em className="text-gold italic">Island</em>
          </h1>
          <p className="font-display italic text-xl text-cream-dim max-w-xl mx-auto leading-snug">
            Share your internship experience and help Atlas map the talent across the island.
          </p>
        </div>

        {/* Form */}
        <div style={{
          background: "#13243d",
          border: "1px solid rgba(245,240,232,0.1)",
          borderRadius: "16px",
          padding: "40px",
        }}>
          <form onSubmit={handleSubmit} className="space-y-10">

            {/* Contact */}
            <div>
              <SectionHeader icon={User} title="Contact Information" />
              <Label>Email</Label>
              <input
                type="email"
                required
                placeholder="john@example.com"
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
                className={inputClass}
                style={{ borderRadius: "8px" }}
              />
            </div>

            {/* Academic */}
            <div>
              <SectionHeader icon={GraduationCap} title="Academic Information" />
              <Label>University</Label>
              <div className="relative">
                <select
                  required
                  value={form.university}
                  onChange={(e) => set("university", e.target.value)}
                  className={selectClass}
                  style={{ borderRadius: "8px" }}
                >
                  <option value="" disabled>Select university</option>
                  {UNIVERSITIES.map((u) => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-cream-dim">
                  ▾
                </div>
              </div>
            </div>

            {/* Internship Details */}
            <div>
              <SectionHeader icon={Briefcase} title="Internship Details" />
              <div className="space-y-5">

                <div>
                  <Label>Company</Label>
                  <div className="relative">
                    <select
                      required
                      value={form.company}
                      onChange={(e) => set("company", e.target.value)}
                      className={selectClass}
                      style={{ borderRadius: "8px" }}
                    >
                      <option value="" disabled>Select company</option>
                      {COMPANIES.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-cream-dim">
                      ▾
                    </div>
                  </div>
                </div>

                <div>
                  <Label>Role Title</Label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., Software Engineer Intern"
                    value={form.roleTitle}
                    onChange={(e) => set("roleTitle", e.target.value)}
                    className={inputClass}
                    style={{ borderRadius: "8px" }}
                  />
                </div>

                <div>
                  <Label>Role Category</Label>
                  <div className="relative">
                    <select
                      required
                      value={form.category}
                      onChange={(e) => set("category", e.target.value)}
                      className={selectClass}
                      style={{ borderRadius: "8px" }}
                    >
                      <option value="" disabled>Select category</option>
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-cream-dim">
                      ▾
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Year</Label>
                    <div className="relative">
                      <select
                        required
                        value={form.year}
                        onChange={(e) => set("year", e.target.value)}
                        className={selectClass}
                        style={{ borderRadius: "8px" }}
                      >
                        <option value="" disabled>Select year</option>
                        {YEARS.map((y) => (
                          <option key={y} value={y}>{y}</option>
                        ))}
                      </select>
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-cream-dim">
                        ▾
                      </div>
                    </div>
                  </div>
                  <div>
                    <Label>Season</Label>
                    <div className="relative">
                      <select
                        required
                        value={form.season}
                        onChange={(e) => set("season", e.target.value)}
                        className={selectClass}
                        style={{ borderRadius: "8px" }}
                      >
                        <option value="" disabled>Select season</option>
                        {SEASONS.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-cream-dim">
                        ▾
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </div>

            {/* ADDED — Proof of Internship */}
            <div>
              <SectionHeader icon={Upload} title="Proof of Internship" />
              <label
                htmlFor="offer-letter"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "12px",
                  padding: "40px",
                  border: "1px dashed rgba(245,240,232,0.2)",
                  borderRadius: "8px",
                  cursor: "pointer",
                  background: "rgba(255,255,255,0.02)",
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = "#5bc4c0"}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = "rgba(245,240,232,0.2)"}
              >
                <div style={{
                  width: 48, height: 48, borderRadius: "50%",
                  background: "rgba(212,165,72,0.12)",
                  border: "1px solid rgba(212,165,72,0.25)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <Upload size={20} color="#5bc4c0" />
                </div>
                {file ? (
                  <span className="font-body text-sm text-gold">{file.name}</span>
                ) : (
                  <>
                    <span className="font-body text-sm text-gold">Upload offer letter or verification</span>
                    <span className="font-body text-xs text-cream-dim">PDF, JPG, or PNG (max 10MB)</span>
                  </>
                )}
                <input
                  id="offer-letter"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  style={{ display: "none" }}
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </label>
            </div>

            {/* Error */}
            {error && (
              <div className="font-body italic text-sm text-cream-dim border-l-2 border-red-500/50 pl-3">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full font-body font-medium text-sm tracking-wider-md uppercase text-navy py-4 transition-all duration-300 disabled:opacity-50"
              style={{
                background: "#d4a548",
                borderRadius: "8px",
              }}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 size={16} className="animate-spin" />
                  Charting...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  Submit
                  <Send size={14} />
                </span>
              )}
            </button>

          </form>
        </div>
      </main>
      <Footer />
    </>
  );
}