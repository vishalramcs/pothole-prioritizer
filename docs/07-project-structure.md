# 7. Project Structure

**Project:** SRPPS | **Version:** 0.4 draft

Monorepo: Python backend, Next.js frontend, Supabase SQL. One Git repository.

## 1. Folder tree

Files marked **(works)** exist and were tested in the skeleton. Everything else is a stub with a docstring saying what goes there.

```
pothole-prioritizer/
├── README.md                          project README (skeleton, fill the TODOs)
├── .gitignore                         secrets, venvs, weights, uploads, node_modules
├── docs/                              these documents + the planning workbook
│
├── supabase/
│   ├── migrations/
│   │   ├── 0001_init_schema.sql       tables, constraints, indexes (works)
│   │   └── 0002_enable_rls.sql        row level security on every table (works)
│   └── seed.sql                       config, mock roads, 2 crews (works)
│
├── backend/                           Python + FastAPI
│   ├── requirements.txt               pinned core deps; ML deps commented out
│   ├── pytest.ini
│   ├── .env.example                   DATABASE_URL, Supabase keys, CORS, model path
│   ├── app/
│   │   ├── main.py                    app + CORS + router (works)
│   │   ├── core/
│   │   │   ├── config.py              settings from env (works)
│   │   │   └── db.py                  engine + one-transaction-per-request dependency (works)
│   │   ├── api/
│   │   │   ├── router.py              mounts everything under /api (works)
│   │   │   └── routers/
│   │   │       ├── health.py          /api/health, /api/health/db (works)
│   │   │       └── uploads, potholes, roads, crews, zones, plan,
│   │   │           repairs, analytics, config   (.py stubs; endpoints listed in each docstring)
│   │   ├── schemas/                   Pydantic request/response models (stub)
│   │   ├── services/                  the logic from TRD section 4 (stubs)
│   │   │   ├── detector.py  gps.py  geo.py  severity.py  priority.py
│   │   │   ├── matching.py  zones.py  planner.py  status.py
│   │   │   └── storage.py  video.py  analytics.py
│   │   └── repositories/              all SQL lives here (stubs)
│   │       └── potholes.py  uploads.py  roads.py  crews.py
│   │           zones.py  repair_orders.py  config.py
│   ├── ml/
│   │   ├── README.md                  where weights go and what to record
│   │   └── weights/                   git-ignored model files
│   ├── scripts/load_demo_data.py      demo potholes (stub)
│   └── tests/                         health + DB URL tests (work)
│
├── frontend/                          Next.js (App Router) + React + TypeScript + Tailwind
│   ├── package.json  tsconfig.json  next.config.ts  eslint.config.mjs   (from create-next-app)
│   ├── .env.example                   NEXT_PUBLIC_API_URL
│   └── src/
│       ├── app/
│       │   ├── layout.tsx             shell with nav bar (works)
│       │   ├── globals.css            design tokens as Tailwind theme (works)
│       │   ├── page.tsx               Map Dashboard (placeholder)
│       │   └── upload/  zones-plan/  repairs/  analytics/   (placeholder pages)
│       ├── components/
│       │   ├── layout/NavBar.tsx      (works)
│       │   └── map/  panels/  upload/  plan/  repairs/  charts/  ui/   (empty, .gitkeep)
│       ├── hooks/                     (empty)
│       └── lib/
│           ├── api.ts                 fetch wrapper for the Python API
│           ├── types.ts               TypeScript types mirroring the schema
│           └── constants.ts           nav links
│
└── sample_data/
    ├── README.md                      record source + licence for every image
    └── images/
```

## 2. Rules for where code goes

- **Routers** only parse HTTP and call a service. No SQL, no scoring math.
- **Services** hold the logic from TRD section 4. They call repositories. They do not know about HTTP.
- **Repositories** hold SQL. One module per table.
- **Transactions:** a request uses one connection from `get_conn()`. Plan and zone recompute rely on that.
- **Status changes** go through `services/status.py` only (TRD 4.9).
- **Constants** (weights, thresholds, radii) come from the `config` table, not from code.
- **Frontend** talks only to the Python API through `src/lib/api.ts`. No Supabase client in the browser.
- **Map code** is client-only (`next/dynamic`, `ssr: false`).

## 3. Environment variables

| Where | Name | Purpose |
|---|---|---|
| backend/.env | `DATABASE_URL` | Supabase Session pooler string |
| backend/.env | `DB_USE_NULLPOOL` | `true` only for the Transaction pooler |
| backend/.env | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Storage access, **server only** |
| backend/.env | `STORAGE_BUCKET` | Private bucket name (`road-images`) |
| backend/.env | `CORS_ORIGINS` | Allowed frontend origins (default `http://localhost:3000`) |
| backend/.env | `MODEL_PATH`, `MAX_UPLOAD_MB` | Detector weights path, upload limit |
| frontend/.env.local | `NEXT_PUBLIC_API_URL` | Python API base URL (default `http://localhost:8000/api`) |

## 4. First-run commands

Tested on the skeleton with a local PostgreSQL 16 standing in for Supabase (not a hosted Supabase project) and Python 3.12 / Node 22.

```bash
# 1. Database: in the Supabase SQL Editor run, in order:
#    supabase/migrations/0001_init_schema.sql, 0002_enable_rls.sql, supabase/seed.sql
#    then create a private Storage bucket named road-images.

# 2. Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in DATABASE_URL etc.
pytest                             # 5 pass, 1 skipped without TEST_DATABASE_URL
uvicorn app.main:app --reload      # http://localhost:8000/docs

# 3. Frontend (second terminal)
cd frontend
npm install
cp .env.example .env.local
npm run lint && npm run build      # both pass on the skeleton
npm run dev                        # http://localhost:3000
```

Check: `http://localhost:8000/api/health/db` should say `reachable`.

## 5. Not in the skeleton (add when you reach that task)

- ML dependencies (`ultralytics`, `scikit-learn`, `numpy`): commented out in `requirements.txt` because they are large and untested here. Install and pin them at task 2.2 / 4.3.
- Leaflet and Chart.js are already in `frontend/package.json`; nothing imports them yet.
- Detection, scoring, matching, zones, planner, and all feature endpoints and pages.
- A hosted-Supabase test: only a local Postgres was used here.
