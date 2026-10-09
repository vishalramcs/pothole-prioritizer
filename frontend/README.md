# frontend/

Next.js (App Router) + React + TypeScript + Tailwind CSS. Talks only to the Python API, never to Supabase directly.

```
npm install
cp .env.example .env.local
npm run dev        # http://localhost:3000
```

Map note: Leaflet needs the browser, so load map components with `next/dynamic` and `ssr: false`.
Routes and screens are described in `docs/03-app-flow.md`; look and tokens in `docs/04-design-brief.md`.
