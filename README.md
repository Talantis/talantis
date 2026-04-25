# Talantis — Frontend

A legendary island of talents. Built with Next.js 14, Tailwind, and the Talantis brand system.

## Quick start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Structure

```
talantis-frontend/
├── app/
│   ├── layout.js           Root layout (fonts, favicons, metadata)
│   ├── globals.css         Brand tokens, noise overlay, base styles
│   ├── page.jsx            Home / landing
│   └── explore/
│       └── page.jsx        Main product page (chart + filter + Atlas)
│
├── components/
│   ├── TalantisLogo.jsx    Premium mark (compass + island + star)
│   ├── AtlasLogo.jsx       Atlas armillary sphere mark
│   ├── TalantisMark.jsx    v5 Planted favicon (reusable inline)
│   ├── Nav.jsx             Top navigation
│   ├── Footer.jsx          Footer
│   ├── chart/
│   │   ├── InternChart.jsx       The bar chart (Recharts, brand-styled)
│   │   └── UniversityFilter.jsx  Dropdown filter
│   └── atlas/
│       └── AskAtlas.jsx    Chat interface (streaming placeholder)
│
├── lib/
│   └── utils.js            cn() Tailwind merger
│
├── public/
│   └── [favicon files]     Drop from talantis_favicons_v5.zip here
│
├── tailwind.config.js      Brand color tokens + font config
├── next.config.js
├── package.json
└── jsconfig.json           @/* path aliases
```

## Brand system

All brand tokens live in **two places**:

1. `tailwind.config.js` — colors (navy, gold, cream, aqua), fonts (display, body), animations
2. `app/globals.css` — CSS variables, noise overlay, base typography, selection color

Use Tailwind classes wherever possible: `bg-navy`, `text-gold`, `font-display italic`, etc.

## Backend integration (TODO)

The frontend is scaffolded with stubbed data. When your FastAPI backend is live:

- **Chart data** → `InternChart.jsx` (line ~40): swap `PLACEHOLDER_DATA` for a fetch from `/api/internships?university=X`
- **University list** → `UniversityFilter.jsx` (line ~18): fetch from `/api/universities` or just hardcode
- **Atlas streaming** → `AskAtlas.jsx` (line ~35): replace the `setTimeout` stub with an EventSource connection to `/api/ask-atlas`

## Deployment

```bash
vercel --prod
```

Vercel auto-detects Next.js. Make sure your Python backend functions live in `/api/*.py` in the same repo.
