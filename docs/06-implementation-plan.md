# 6. Implementation Plan

**Project:** SRPPS | **Version:** 0.4 draft

```
Problem release time: YYYY-MM-DD HH:MM   (fill in)
Submission deadline:  YYYY-MM-DD HH:MM   (fill in)
Team / roles:         ML: ___  Backend: ___  Frontend: ___  (fill in)
```

Workflow: **Understand → Plan → Build → Test → Explain → Commit → Demo**

Golden rule: a working project the team understands beats an impressive one they can't explain.

---

## 1. Ground rules

- Development starts only after the problem statements are released. Submit only what was built in the window.
- Git + GitHub from the first commit. Real history only: no fake commits, no history rewriting to hide when/how work was done.
- Small commits after each working milestone, with meaningful messages (`Add upload endpoint`, not `update`).
- Disclose significant AI help, external datasets, and models in the README.
- No secrets in Git. `.env` ignored, `.env.example` committed.
- No substantive development after the deadline.
- Before any complicated feature: write Goal, Approach, Simpler alternative, Trade-off, and a 30 to 60 second judge explanation.

## 2. Repo layout

A tested skeleton is provided (see `docs/07-project-structure.md` for the full tree and what each folder is for):

```
pothole-prioritizer/
├── backend/     Python + FastAPI (routers -> services -> repositories)
├── frontend/    Next.js + React + Tailwind
├── supabase/    migrations/ and seed.sql
├── sample_data/ demo photos + licences
├── docs/        these documents
├── .gitignore
└── README.md
```

## 3. Time budget (guideline, not a rule)

| Phase | Share of window | Goal |
|---|---|---|
| 1. Understand and set up | 5 to 10% | Requirements, repo, skeleton runs |
| 2. Build core (P0) | 40 to 50% | Upload → detect → score → map → track |
| 3. Test and stabilize | 15 to 20% | Fix bugs, edge cases |
| 4. Improve (P1, then P2) | 10 to 15% | Traffic, repeat, zones, plan, analytics |
| 5. Submission | ~10% | README, Git check, final test, submit |
| 6. Judge prep | Remaining | Practice demo and Q&A |

Convert these to clock times once release time and deadline are known.

## 4. Tasks

Owner and status columns to be filled by the team. DoD = definition of done.

### Phase 1: Setup (P0)

| # | Task | DoD | Commit message |
|---|---|---|---|
| 1.1 | Create GitHub repo and commit the provided skeleton | Repo cloned by all members | `Initialize project structure` |
| 1.2 | Backend runs and connects to the database (skeleton has `/api/health` and `/api/health/db`) | `uvicorn app.main:app --reload` works; `/api/health/db` says reachable | `Add backend skeleton` |
| 1.3 | Pick and download pothole model/dataset, record source and licence | Model loads and runs on one image | `Add detector loading` |
| 1.4 | Map page in Next.js: Leaflet loaded with `next/dynamic` and `ssr: false` | Map renders in dev and `npm run build` passes | `Add map page` |
| 1.5 | Create Supabase project, run the migrations and seed, create the private `road-images` bucket, fill `backend/.env` (Session pooler string) | `/api/health/db` returns reachable against Supabase | `Connect backend to Supabase` |

### Phase 2: Core (P0)

| # | Task | DoD | Commit message |
|---|---|---|---|
| 2.1 | `POST /uploads`: validate file, GPS (EXIF/manual), save | Row in `uploads` | `Add upload endpoint` |
| 2.2 | Detector on upload; save potholes with boxes | Potholes rows created for a test image | `Connect detector to upload` |
| 2.3 | Severity function with unit tests | Known inputs give expected levels | `Add severity calculation` |
| 2.4 | Priority function (weights from config) with unit tests | Weights sum check, known inputs, expected score | `Add priority scoring` |
| 2.5 | `GET /potholes` + map markers by band | Markers visible, colored | `Show potholes on map` |
| 2.6 | Image endpoint (`GET /potholes/{id}/image`) + side panel with box drawn on a canvas and score breakdown | Click shows photo with box and breakdown | `Add pothole detail panel` |
| 2.7 | One status-change function implementing TRD 4.9, endpoint, Repairs page, unit tests for every allowed and disallowed change | All transitions behave as the table says; 409 otherwise | `Add repair tracking` |
| 2.8 | Upload page with preview and results | Full upload flow works in browser | `Add upload page` |

### Phase 3: Test and stabilize

| # | Task | DoD |
|---|---|---|
| 3.1 | Run the testing table in the TRD | Results recorded honestly, bugs logged |
| 3.2 | Handle bad inputs and no-detection cases | Clear messages, no crashes |
| 3.3 | Demo seed: `supabase/seed.sql` (already has config, roads, crews) plus `backend/scripts/load_demo_data.py` for demo potholes | A fresh Supabase project plus the script gives a populated map |
| 3.4 | Explainability check on each core module | Team can explain what/where/why |
| 3.5 | Ranking sanity check (TRD testing table) and detector check on real local photos | Results recorded honestly, including misses and false alarms |

### Phase 4: Improve

| # | Task | Tier | Commit message |
|---|---|---|---|
| 4.1 | Roads table, traffic/importance in score, mock badge | P1 | `Add traffic and road importance` |
| 4.2 | Duplicate/repeat matching per TRD 4.4 (same-upload potholes never merge, one-to-one matching) with unit tests, plus score term | P1 | `Add repeat damage detection` |
| 4.3 | DBSCAN zones + zone display | P1 | `Add maintenance zones` |
| 4.4 | Crews endpoints + planner per TRD 4.7 (transactional; reports unscheduled potholes; replanning repeatable) with unit tests | P2 | `Add repair planner` |
| 4.5 | Analytics endpoint + charts | P2 | `Add analytics page` |
| 4.6 | Video frame sampling, frame columns, box-overlap merge (TRD 4.8) | P2 | `Add video upload` |

### Phase 5: Submission

| # | Task | DoD |
|---|---|---|
| 5.1 | Fill in the root `README.md` skeleton (all required sections, below); replace every TODO | Reviewed by a teammate |
| 5.2 | Scan repo for secrets | None found |
| 5.3 | Fresh-clone test: follow README on a clean machine/folder | App runs from instructions |
| 5.4 | Final commit and push; verify on GitHub | Latest code visible |
| 5.5 | Submit | Confirmation recorded |

## 5. README sections required

A skeleton with all of these sections is provided as `README.md` at the repo root. Nothing in it is true until you edit it: features are unchecked, run steps are TODO.


Project name · Team · Problem statement · Solution · Features · Technologies · Architecture · How to run · Demo · External resources · AI usage · Limitations

## 6. Cut list (drop in this order if behind)

1. Video input (4.6)
2. Analytics page (4.5), keep the SQL queries as a fallback
3. Repair planner (4.4), keep zones
4. Zones (4.3)

Never cut: detection, severity, GPS map, priority score, repair tracking. Avoid risky rewrites late in the window.

## 7. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Model weights won't load / too slow | Smaller model variant; lower image resolution; pre-computed detections for demo images (state clearly that they were pre-computed) |
| EXIF GPS missing | Manual coordinates and map click |
| Map tiles blocked at venue | Cache a few tiles or use screenshots as backup, state it |
| Venue Wi-Fi poor, or Supabase unreachable | Supabase needs internet. Before the event, dry-run the same migrations on a local Postgres (or a local Supabase through its CLI, which needs Docker) and point `DATABASE_URL` at it. Untested: practice it. Keep a screen recording as backup |
| Supabase direct connection fails on the venue network | The direct connection is IPv6-only on many plans; use the Session pooler string (IPv4) |
| Supabase project paused or misconfigured on demo day | Open the dashboard and hit `/api/health/db` before presenting |
| Teammate blocked | Pair on the blocker; skip to the next P0/P1 item |

## 8. Judge readiness

Prepare answers (from the real implementation, not guesses) to:

- What problem? What did you build? How does it work end to end?
- Which file handles detection, scoring, zones, planning?
- Why YOLO? Why DBSCAN? Why these weights?
- Where did the data and model come from? How did you use AI?
- What happens if detection fails? What doesn't it handle?
- What would you improve with more time?

Weak points to own up to: 2D severity, mock traffic data, greedy sequencing, assumed weights.

## 9. Demo plan

Follow the demo path in the App Flow doc. Rehearse at least twice. Keep a backup screen recording and a local copy of demo images. Never fabricate a successful result: if something fails live, explain it and show the fallback.

## 10. Final submission checklist

```
Problem:     [ ] correct statement  [ ] core objective  [ ] essential requirements
Code:        [ ] works  [ ] understandable  [ ] explainable  [ ] no needless complexity  [ ] no secrets
Git:         [ ] repo exists  [ ] authentic history  [ ] meaningful commits  [ ] final changes committed  [ ] pushed
README:      [ ] team  [ ] problem  [ ] solution  [ ] tech  [ ] run  [ ] demo  [ ] external resources  [ ] AI usage  [ ] limitations
Originality: [ ] no copied team code  [ ] no pre-existing project as new  [ ] no fake history  [ ] resources acknowledged
Demo:        [ ] works  [ ] main flow tested  [ ] team understands it  [ ] can explain architecture  [ ] can answer judge questions
```
