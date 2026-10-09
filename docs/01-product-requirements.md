# 1. Product Requirements Document (PRD)

**Project:** Smart Road Pothole Prioritization System (SRPPS)
**Version:** 0.4 draft
**Owner:** TBD
**Problem release time:** YYYY-MM-DD HH:MM
**Submission deadline:** YYYY-MM-DD HH:MM

---

## 1. Problem

Road authorities get thousands of pothole and road-damage complaints. Maintenance crews have limited time and budget. If every complaint is treated equally, repairs on dangerous, high-traffic roads get delayed.

## 2. Goal

Turn road images into a **dynamic repair-priority map** and an **optimized repair plan**, using pothole severity, traffic, road importance, location, and available resources.

**Core objective (one line):** image → detected pothole → priority score → map → repair order.

## 3. Users

| User | Needs |
|---|---|
| **Field reporter** (inspector, citizen, or survey vehicle operator) | Upload a photo or video with a location quickly, see what was detected |
| **Maintenance planner** (authority staff) | See which potholes matter most, group them into zones, get a repair sequence for the crews available, track what's done |
| **Manager** | See road-condition analytics and repair progress |

For the hackathon these can be one login-free app with three views. No auth (see non-goals).

## 4. User stories

1. As a reporter, I upload a road image with GPS so the pothole gets recorded.
2. As a reporter, I see the detected potholes with size and severity right after upload.
3. As a planner, I see all potholes on a map, coloured by priority.
4. As a planner, I see which potholes sit on busy or important roads.
5. As a planner, I see locations that keep getting damaged.
6. As a planner, I see potholes grouped into maintenance zones.
7. As a planner, I enter how many crews I have and get a repair sequence.
8. As a planner, I mark a repair as in progress or done.
9. As a manager, I see counts, trends, and top problem roads.

## 5. Functional requirements

Tiers: **P0** must have, **P1** important, **P2** nice to have, **P3** avoid.

| ID | Requirement | Tier | Problem statement item |
|---|---|---|---|
| FR-01 | Upload a road image (JPG/PNG) with location | P0 | Detect potholes from images |
| FR-02 | Detect potholes in the image and return bounding boxes with confidence | P0 | Detect potholes |
| FR-03 | Estimate relative size and a Low/Medium/High severity per pothole | P0 | Estimate size and severity |
| FR-04 | Get GPS from image EXIF, typed coordinates, or a map click | P0 | Map using GPS |
| FR-05 | Show potholes on an interactive map | P0 | Map using GPS |
| FR-06 | Compute a repair priority score (0 to 1) and band (Low/Moderate/Critical) | P0 | Priority score |
| FR-07 | Track repair status: Pending, Scheduled, In Progress, Repaired | P0 | Track completed and pending repairs |
| FR-08 | Include traffic density and road importance in the score | P1 | Consider traffic and road importance |
| FR-09 | Detect repeated damage at the same location and raise the score | P1 | Identify repeated damage |
| FR-10 | Group nearby pending potholes into maintenance zones | P1 | Group into maintenance zones |
| FR-11 | Upload a short video and detect potholes on sampled frames | P2 | Detect from video |
| FR-12 | Manage crews (name, daily capacity) and generate a repair sequence per crew for N days; report potholes that don't fit | P2 | Optimize sequence of repairs |
| FR-13 | Analytics page: counts by status/severity, top roads, time to repair | P2 | Road-condition analytics |

## 6. Non-goals

- User accounts, login, roles (P3)
- Real-time camera streaming, mobile app (P3)
- True 3D depth measurement (we estimate relative size from the 2D image)
- Live traffic feeds (we use clearly labelled mock values)
- Production-grade routing (we use a simple greedy sequence, not full route optimization)

## 7. Success criteria (for the demo)

These are "can we show it" checks, not performance claims.

- [ ] Upload an image with GPS and see detected potholes within a few seconds
- [ ] Map shows potholes coloured by priority band
- [ ] Two potholes with the same severity get different priority because of road/traffic
- [ ] A repeat location visibly scores higher than a one-off
- [ ] Zones appear on the map and can be listed
- [ ] Two crews with a daily capacity and a number of days produce an ordered plan; anything that doesn't fit is reported, not silently dropped
- [ ] Marking a repair done updates the map and analytics
- [ ] Team can explain every part in under a minute each

## 8. Assumptions and constraints

- 24-hour build window; one official problem statement; team of 3 to 6.
- A pretrained YOLO pothole model is used, disclosed in the README.
- Stack: Python backend, Next.js (React + Tailwind) frontend, Supabase (hosted Postgres + Storage). The app needs internet unless run against a local database.
- Traffic density and road importance are **mock/lookup values**, because real data isn't available in the window. This is stated in the app and README.
- Severity is a 2D estimate. Camera distance and angle affect it. Documented as a limitation.
- Weights and thresholds are tunable starting guesses, not standards.
- All potholes in one photo share that photo's GPS point (precision about phone GPS accuracy, roughly 5 to 10 m).
- Priority is about impact, not only damage: with the seeded mock data, a pothole on the quiet local road cannot reach Critical (see TRD 4.5).
- A pothole has one status (Pending, Scheduled, In Progress, Repaired); repair orders only carry the plan (see TRD 4.9).

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Model gives false positives/negatives | Wrong map | Confidence threshold, show boxes so humans can sanity-check, test on local photos |
| GPS missing from photos | Can't map | Manual entry and map click fallback |
| Model training/GPU not available | Delay | Use pretrained weights, run on CPU, small images |
| Scope creep | Core not finished | Strict P0 first; cut list in implementation plan |
| Can't explain the code | Judging risk | Simple modules, explainability check before "done" |

## 10. Open questions

- Which pothole model/dataset do we use? (see Technical Requirements, section 8)
- Do we have real or demo road data for traffic/importance?
- Team size and who owns ML, backend, frontend?
