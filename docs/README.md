# Project Docs: Smart Road Pothole Prioritization System

Hackathon problem statement 6. Working title: **SRPPS** (rename whenever).

| # | Document | What it answers |
|---|---|---|
| 1 | [Product Requirements](01-product-requirements.md) | What are we building, for whom, and what counts as done? |
| 2 | [Technical Requirements](02-technical-requirements.md) | Stack, algorithms, API, testing, licences |
| 3 | [App Flow](03-app-flow.md) | Screens and how a user moves through them |
| 4 | [Design Brief](04-design-brief.md) | Look, layout, colours, components |
| 5 | [Backend Schema](05-backend-schema.md) | Supabase Postgres tables, migrations, RLS, seed data, analytics queries |
| 6 | [Implementation Plan](06-implementation-plan.md) | Phases, tasks, commits, demo prep |
| 7 | [Project Structure](07-project-structure.md) | Folder tree, where code goes, env vars, first-run commands |
| - | [pothole_hackathon_plan.xlsx](pothole_hackathon_plan.xlsx) | Feature tiers, pipeline, editable priority-score model, tech choices, open items |

## Fill these in (not guessed on purpose)

```
Problem release time: YYYY-MM-DD HH:MM
Submission deadline:  YYYY-MM-DD HH:MM
Team size / roles:    TBD
```

## Status

Draft v0.4. All numbers marked "assumption" (weights, thresholds, radii) are starting guesses to tune on real data.
The docs are plans, not proof: nothing here claims a feature works until it is built and tested.

## AI usage note

These documents were drafted with help from Claude. The team must review, edit, and be able to explain everything in them. Record this in the main project README under "AI Usage".

## Changelog

**v0.4** (stack change)
- Stack is now: Python backend (FastAPI), Next.js + React + Tailwind frontend, Supabase (Postgres + Storage). SQLite and plain HTML are gone from every doc.
- New: `07-project-structure.md`, and a working skeleton next to `docs/`: `backend/`, `frontend/`, `supabase/`, `sample_data/`.
- Schema moved to Postgres as real migration files. Added `safety_override`; zones now use `ON DELETE SET NULL`; Storage paths replace file paths. The doc's SQL is copied from the migration files and was run on PostgreSQL 16.
- Backend uses SQLAlchemy + psycopg to the Postgres connection string (real transactions); `supabase-py` is only for Storage. Use the Session pooler string (the direct connection is IPv6-only on many plans).
- RLS is on for every table; the browser talks only to the Python API.
- Fonts: system stack only, because `next/font/google` needs internet at build time (found when the sandbox build failed offline).
- Plan updated with Supabase setup, a Supabase-unreachable fallback, and a note that an offline demo path is untested.

**v0.3** (second review)
- Confidence now has one job everywhere: filtering detections. The workbook's "plus confidence" wording on severity was wrong and is fixed.
- Foreign keys must be enabled on every DB connection (not just in the DDL script); added a schema version row and a migration rule.
- Upload hardening: validate image content and use generated filenames.
- Optional safety override (off by default) so a very dangerous pothole on a quiet road can still show Critical. Team decision pending.
- Added a ranking sanity test, UI wording for "relative severity" and demo thresholds, and three limitations (straight-line zones, fixed crew capacity, unvalidated scoring).

**v0.2** (review fixes)
- Duplicate matching no longer merges potholes from the same photo; matching is one-to-one across uploads and the radius is 15 m (TRD 4.4). Shared photo GPS is documented as a limitation.
- One status model: `potholes.status`. Repair orders have no status; allowed changes are in TRD 4.9.
- Planner fully specified: crews table and endpoints, `days` input, overflow reporting, transactional replan, zones recomputed first. `repair_orders.zone_id` removed because zones are rebuilt.
- API additions: image endpoints (original upload and per-pothole image), crews CRUD. Schema additions: video frame columns. Severity formula now uses the config values.
- Design brief: orange is never used as text; contrast table added; markers also encoded by size and icon.
- Scoring ceiling (0.66 on the seeded local road) stated as intended, with the table in TRD 4.5.
- Added the spreadsheet to this folder and a root `README.md` skeleton.
- Not done on purpose: a setup/run guide. It needs real commands, and there is no code to test them against yet. Write it once the app runs.
