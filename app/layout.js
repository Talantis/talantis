import { Cormorant_Garamond, Inter_Tight } from "next/font/google";
import "./globals.css";

// ============================================================
// FONTS
// Display: Cormorant Garamond — for headlines, names, mythic moments
// Body:    Inter Tight — for UI, functional text
// Both loaded via next/font for optimal performance.
// ============================================================
const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-cormorant",
  display: "swap",
});

const interTight = Inter_Tight({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-inter-tight",
  display: "swap",
});

// ============================================================
// METADATA — SEO, Open Graph, favicons
// Next.js auto-reads favicon files from /public/
// ============================================================
export const metadata = {
  title: "Talantis — A legendary island of talents",
  description:
    "Every company is looking in the same places. Talantis shows you the ones no one has mapped yet.",
  metadataBase: new URL("https://talantis.vercel.app"),
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  manifest: "/site.webmanifest",
  openGraph: {
    title: "Talantis — A legendary island of talents",
    description:
      "Discover where talent actually flows. Meet Atlas, your guide.",
    url: "https://talantis.vercel.app",
    siteName: "Talantis",
    images: [{ url: "/og-image.png", width: 1200, height: 630 }],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Talantis",
    description: "A legendary island of talents.",
    images: ["/og-image.png"],
  },
};

// ============================================================
// VIEWPORT — themeColor lives here in Next 14+
// ============================================================
export const viewport = {
  themeColor: "#0a1628",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${cormorant.variable} ${interTight.variable}`}>
      <body>{children}</body>
    </html>
  );
}