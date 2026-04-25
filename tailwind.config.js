/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ============ TALANTIS BRAND PALETTE ============
        // Primary
        navy: {
          DEFAULT: '#0a1628',
          soft: '#0f1f3a',
          deep: '#050b18',
        },
        gold: {
          DEFAULT: '#d4a548',
          deep: '#a67c2e',
          light: '#e3b659',
        },
        cream: {
          DEFAULT: '#f5ecd7',
          dim: '#c9b88a',
        },
        aqua: {
          DEFAULT: '#4fb3bf',
          deep: '#1e5a6b',
        },
        // Functional
        line: '#2a3a5c',
        'line-soft': '#1a2640',
      },
      fontFamily: {
        // Display — for headlines, names, editorial moments
        display: ['var(--font-cormorant)', 'Georgia', 'serif'],
        // Body — for UI, functional text
        body: ['var(--font-inter-tight)', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        // Display sizes with the brand's tight tracking baked in
        'hero': ['clamp(64px, 9vw, 144px)', { lineHeight: '0.95', letterSpacing: '-0.02em' }],
        'section': ['clamp(40px, 5vw, 72px)', { lineHeight: '1.05', letterSpacing: '-0.01em' }],
      },
      letterSpacing: {
        'wider-sm': '0.2em',
        'wider-md': '0.3em',
        'wider-lg': '0.4em',
      },
      animation: {
        'fade-up': 'fadeUp 1s ease-out forwards',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
