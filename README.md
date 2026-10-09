# Smart Road Pothole Prioritization System (SRPPS)

## Team
TODO: team name, members, roles (ML / backend / frontend)

## Problem Statement
Hackathon problem statement 5: **Smart Road Pothole Prioritization System.** (The planning docs in `docs/` say 6; the official statement is numbered 5.)
Identify road damage from available data and help authorities decide which locations to repair first, considering severity, traffic, road importance, location and available maintenance resources; support maintenance planning; give an understandable basis for the ranking; and provide a way to evaluate how well the prioritization works.

- Problem release time: TODO (YYYY-MM-DD HH:MM)
- Submission deadline: TODO (YYYY-MM-DD HH:MM)

## Solution
A reporter uploads a road photo or short video with its location and road. A pretrained YOLO model finds the potholes; each gets a relative severity from how much of the image it covers, and a 0 to 1 repair priority that also weighs the road's traffic, its importance, repeat damage at that spot, and how close it is to a hospital, clinic, school or fire station (OpenStreetMap). Planners see every pothole on a map coloured by priority, group nearby ones into maintenance zones, enter their crews and how many repairs each can do per day, and get a day-by-day repair sequence. Marking repairs as started or done updates the map and the analytics. An Evaluation page measures the strategy against first-come-first-served, severity-only and random ordering, and checks how much the ranking depends on the chosen weights.

Pipeline: image → detected pothole → severity → priority score → map → zones → repair order.

## Features
Ticked = built, and covered by automated tests and a manual check in Chrome against the local database.

- [x] Pothole detection from images (P0)
- [x] Size and severity estimate (P0) (relative, from the 2D image)
- [x] GPS map (P0) (EXIF GPS, typed coordinates, or map click)
- [x] Priority score (P0) with per-factor breakdown
- [x] Repair tracking (P0) (Pending / Scheduled / In Progress / Repaired)
- [x] Traffic and road importance (P1) (mock values, labelled "demo data")
- [x] Repeat-damage detection (P1) (same pothole seen again; damage back after repair)
- [x] Maintenance zones (P1) (DBSCAN)
- [x] Video input (P2) (one frame per second, same pothole across frames merged)
- [x] Repair sequence optimization (P2) (greedy, per crew and day; overflow reported)
- [x] Analytics (P2) (charts with data tables)
- [x] Location factor: proximity to hospitals, clinics, schools, fire stations (OpenStreetMap)
- [x] Evaluation of the prioritization: baselines, exposure, travel, weight sensitivity

Not done: a screen to edit road traffic/importance (the API `PUT /api/roads/{id}` works; there is no form), hosted Supabase test (see How to Run).

## Technologies
Python 3.12, FastAPI, SQLAlchemy 2 Core + psycopg 3, Ultralytics YOLO (YOLOv8s weights), scikit-learn (DBSCAN), OpenCV, Pillow; Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS 4, react-leaflet + OpenStreetMap, Chart.js; PostgreSQL (Supabase, or a local Postgres through `pgserver` for development and offline demos). Exact versions: `backend/requirements.txt`, `frontend/package.json`.

## Architecture / Technical Approach
```
Browser (Next.js) ──JSON / multipart──> FastAPI ──> detector (YOLO) ──> severity ──> priority
                                            │                                          │
                                            ├── repeat matching (haversine, 15 m) ─────┤
                                            ├── zones (DBSCAN) ──> planner (greedy) ───┤
                                            └── storage (Supabase bucket or disk)      v
                                                                                  Postgres
```
The browser only talks to the Python API. Routers parse HTTP, services hold the logic, repositories hold the SQL. Every request runs in one database transaction that commits **before** the response is sent, so a failed save is never reported as success. Formulas, constants and their sources: `docs/02-technical-requirements.md` section 4. Every constant lives in the `config` table.

| What | Where |
|---|---|
| Detection | `backend/app/services/detector.py` |
| Severity / priority | `backend/app/services/severity.py`, `priority.py` |
| Upload pipeline, repeat matching | `backend/app/services/uploads.py`, `matching.py` |
| Zones, planner | `backend/app/services/zones.py`, `planner.py` |
| Location factor | `backend/app/services/facilities.py`, `scripts/import_facilities.py` |
| Evaluation | `backend/app/services/evaluation.py` |
| Status rules | `backend/app/services/status.py` |
| Video | `backend/app/services/video.py` |
| Pages | `frontend/src/app/` |

Measured on the development laptop (CPU only): detection takes about 0.12 s per 1280 px photo once the model is loaded; the first request after start loads the model and takes a few seconds; a 4-second test clip took about 9 s end to end.

## How to Run
Tested on Windows 11 with Python 3.12 and Node 24, against a local Postgres. **Not yet tested against a hosted Supabase project.**

**1. Database.** Pick one:
- *Supabase:* in the SQL Editor run, in order, `supabase/migrations/0001_init_schema.sql`, `0002_enable_rls.sql`, `0003_demo_flag.sql`, `0004_facilities.sql`, then `supabase/seed.sql`. Create a private Storage bucket `road-images`. Use the **Session pooler** connection string.
- *Local (no internet needed for the database):* step 2 below starts one.

**2. Backend** (first terminal)
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate             # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt     # large: ultralytics pulls in torch
python scripts/download_model.py    # detector weights -> ml/weights/pothole.pt
cp .env.example .env                # Windows: copy .env.example .env
# Local database instead of Supabase:
pip install pgserver
python scripts/local_db.py          # prints DATABASE_URL=...; put it in .env and blank SUPABASE_URL
                                    # (with no SUPABASE_URL, images are stored in backend/uploads/)
python scripts/load_demo_data.py    # optional demo potholes (labelled as demo data in the UI)
python scripts/import_facilities.py # optional: hospitals/schools from OpenStreetMap (needs internet once)
uvicorn app.main:app                # http://localhost:8000/docs
```
Check: `http://localhost:8000/api/health/db` says `reachable`.

The local Postgres keeps running in the background and gets a new port each time it starts: after a reboot, run `python scripts/local_db.py` again and update `DATABASE_URL`. Stop it with `python scripts/local_db.py --stop`.

**3. Frontend** (second terminal)
```bash
cd frontend
npm ci
cp .env.example .env.local          # only needed if the API is not on localhost:8000
npm run dev                         # http://localhost:3000
```

**Tests**
```bash
cd backend
set TEST_DATABASE_URL=<the same local DATABASE_URL>   # macOS/Linux: export TEST_DATABASE_URL=...
pytest                              # 106 tests; database tests are skipped without TEST_DATABASE_URL
cd ../frontend && npm run lint && npm run build
```
Database tests run inside a transaction that is rolled back, so they leave no data behind. Use a local database for them, not the demo Supabase project.

## Demo
1. Run `python scripts/load_demo_data.py`, open **Zones and Plan** and click **Recompute zones**, then start on the **Map**.
2. **Upload** a photo from `sample_data/images` on *Demo Main Road*: boxes, severity and priority appear.
3. Upload the same photo at the same coordinates again: the results say "Yes, same pothole (seen again)" and its priority rises (repeat damage).
4. **Zones and Plan**: recompute zones, keep the 2 seeded crews, set 3 days, **Generate plan**.
5. **Repairs**: mark one Scheduled pothole repaired, then show the **Map** (hollow marker with status "All") and **Analytics**.

6. **Evaluation**: show that SRPPS fixes every Critical pothole on day 1 while severity-only and random do not, and that the top 10 do not change when any weight moves by 20%.

Prepared answers: "Why is the High pothole on Demo Lane only Moderate?" Priority is about impact, not only damage: with the seeded traffic of 0.20 a local road can reach at most 0.585, or 0.735 right next to a hospital (TRD 4.5). "Why is everything in the demo High severity?" All sample photos are close-ups, so each pothole fills much of the frame; road-level photos give Medium and Low.

## Results: does the prioritization work?
Measured with the Evaluation page (`GET /api/evaluation`), seeded crews (2 crews x 5 repairs per day), Critical counted as fixed if repaired on day 1. Exposure = sum of traffic x severity x days the pothole stays open (lower is better).

Location factor computed from 2,063 OpenStreetMap facilities (746 schools, 682 hospitals, 625 clinics, 10 fire stations) imported for central Bengaluru; the demo potholes are a median 380 m from the nearest one.

**Demo data** (reproducible: `load_demo_data.py` + `import_facilities.py` on a fresh database), 13 open potholes, 7 Critical, 1 day:

| Strategy | Priority addressed | Critical fixed day 1 | Avg days to repair Critical | Exposure | Crew travel |
|---|---|---|---|---|---|
| **SRPPS** | 81.3% | **100%** | **1.0** | **8.19** | **8.6 km** |
| Priority only (no zones) | 81.3% | 100% | 1.0 | 8.19 | 25.4 km |
| First come, first served | 81.0% | 100% | 1.0 | 8.19 | 9.9 km |
| Severity only | 79.3% | 85.7% | 1.14 | 8.81 | 15.1 km |
| Random (seed 42) | 75.9% | 71.4% | 1.29 | 9.41 | 42.2 km |

**58 open potholes in Bengaluru** uploaded through the app while testing (not reproducible from the repo), 10 Critical:

| Strategy | Critical fixed day 1 | Exposure, 3 days | Travel, 1 day | Travel, 3 days |
|---|---|---|---|---|
| **SRPPS** | **100%** | **18.62** | **11.1 km** | 37.0 km |
| Priority only (no zones) | 100% | 18.62 | 22.8 km | 50.2 km |
| First come, first served | 90% | 19.93 | 15.3 km | 37.0 km |
| Severity only | 70% | 19.26 | 12.1 km | 42.7 km |
| Random (seed 42) | 0% | 37.72 | 9.2 km | 49.7 km |

**Weight sensitivity:** changing any one weight by -20% or +20% left the top 10 unchanged in every case (Spearman at least 0.97 on the demo set, 0.998 on the larger set).

What this shows, honestly: SRPPS always fixes the Critical potholes first and leaves the least exposure, but its edge over first-come-first-served is small on this data (exposure 7% lower over 3 days), because these uploads were not in a harmful order to begin with. Grouping by zone halves travel against plain priority order (8.6 vs 25.4 km, 11.1 vs 22.8 km) and over 3 days matches first-come-first-served's travel while fixing more Critical potholes. The exposure metric uses two of the priority's own inputs, so a priority-based strategy is expected to do well on it. These numbers led to one design change: the first planner (whole zones ranked by average priority) fixed only 80% of Critical potholes on day 1 and travelled more, so it was replaced (TRD 4.7).

## External Resources
- **Pothole detection model:** [Samdutse/pothole-yolov8](https://huggingface.co/Samdutse/pothole-yolov8) (YOLOv8s fine-tuned on the Smartathon pothole dataset from Roboflow Universe). **Its model card states no licence**: fine for building and judging, but ask the author before publishing or selling. Drop-in alternative: [tahaUgan/pothole-yolo11n](https://huggingface.co/tahaUgan/pothole-yolo11n) (CC-BY-4.0); change `MODEL_URL` in `backend/scripts/download_model.py`. In our comparison on 10 photos (7 with potholes, 3 clean roads) the first model boxed the pothole in 6 of the 7; the second found nothing in 3 close-up shots and boxed a patch of sky on a clean road.
- **Ultralytics YOLO:** AGPL-3.0 (as far as we know; check before any commercial use).
- **Sample photos:** 5 photos from Wikimedia Commons (CC0, CC BY 4.0, CC BY-SA 4.0); authors and links in `sample_data/README.md`.
- **Libraries:** FastAPI, SQLAlchemy, psycopg (LGPL), Pillow, scikit-learn, OpenCV, pgserver, Next.js, React, Tailwind CSS, Leaflet (BSD-2), react-leaflet, Chart.js, react-chartjs-2 (open source; check each licence).
- **Map tiles and facility locations:** © OpenStreetMap contributors (ODbL), attribution shown on every map and next to facility distances.
- **Frontend base:** generated by `create-next-app`.
- **Idea reference:** [Smart-Ai-Pothole-Detector](https://github.com/JordanMicahBennett/Smart-Ai-Pothole-Detector------Powered-by-Tensorflow-TensorRT-on-Google-Colab-and-or-Jetson-Nano) by Jordan Bennett (no code or model used).

## AI Usage
Claude (Anthropic) was used for planning and drafting the documents in `docs/` and the project skeleton, and then, during the build window, **wrote most of the application code and tests**: the backend services, endpoints and SQL, the frontend pages and components, the demo data script and this README. It also found and fixed two skeleton bugs (database commits happened after the response was sent; error responses did not match the API spec), each with a test. Commits carry a `Co-Authored-By: Claude` line. TODO (team): state here that you reviewed, tested, modified and can explain the code, and add anything you changed yourselves.

## Limitations
- Severity is a relative 2D estimate (share of the image the box covers), not depth; camera distance and angle change it.
- Traffic density and road importance are mock values, labelled "demo data" in the UI.
- The location factor depends on OpenStreetMap's coverage of hospitals, clinics, schools and fire stations. The public Overpass servers are sometimes down (we hit HTTP 504/500 before a later attempt worked); the script then changes nothing and can simply be re-run.
- The evaluation is a simulation on the stored potholes, not a field trial; its exposure metric uses traffic and severity, which the priority also uses.
- All potholes in one photo or video clip share its single GPS point (phone GPS is roughly 5 to 10 m off).
- With the seeded mock data a pothole on the local road cannot reach Critical (max 0.66). Intended: priority is about impact.
- The detector was checked on only about 15 photos. It can miss potholes (at the 0.40 confidence cut-off it found nothing in one road-level pothole photo, and it ignored a broken drain grate) and can raise false alarms (it boxed a repaired crack on a clean road). It was trained on its own dataset, not on local roads.
- Weights and thresholds are unvalidated assumptions, not a road-safety standard.
- Zones use straight-line distance, not driving distance.
- Greedy sequencing is not globally optimal; with few jobs per day, spreading them over crews can cost travel (see Results).
- The planner assumes a fixed number of repairs per crew per day regardless of pothole size or repair time.
- Video: one frame per second, at most 120 frames (2 minutes); the same pothole is merged only across consecutive sampled frames by box overlap, which fails when the camera moves fast.
- A crew with any finished repairs cannot be deleted (its orders are repair history).
- Needs internet for map tiles; needs internet for Supabase unless the local Postgres is used.
- Photos may contain faces or number plates; we store only the image and its location.
