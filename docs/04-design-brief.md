# 4. Design Brief

**Project:** SRPPS | **Version:** 0.4 draft

---

## 1. Design goal

A planner should understand **where to send crews first** within 5 seconds of opening the map. Clarity beats decoration. The app should look credible, calm, and fast, like an operations dashboard, not a marketing page.

## 2. Principles

1. **Priority first.** The most urgent potholes are the most visible things on screen.
2. **Show the why.** Every score can be expanded into severity, traffic, importance, and repeat parts.
3. **Honest data.** Mock values (traffic, importance) are labelled "demo data" in the UI.
4. **Color is never the only signal.** Pair color with a label, icon, or marker size.
5. **Few screens, few clicks.** Upload to map in two steps.

## 3. Audience and context

Authority staff at a desk (desktop-first dashboard). Field reporters on a phone (the Upload page must work on a narrow screen). Judges viewing a projector or laptop, so large type and strong contrast.

## 4. Layout

- **Top nav:** logo/name left; links Map, Upload, Zones and Plan, Repairs, Analytics.
- **Map Dashboard:** full-width map; left filter bar (status, band, zone); right side panel (opens on marker click, closes on map click).
- **Upload:** single centered card (max ~640 px): file drop area, small map for location, road fields, submit. Result shows the image with boxes and a results table.
- **Zones and Plan:** map on the left, controls and plan list on the right.
- **Repairs:** tabs plus a table.
- **Analytics:** 2 by 2 grid of charts above a table; stacks to one column on small screens.

## 5. Visual style

| Token | Value (starting point) | Use |
|---|---|---|
| Background | `#F7F8FA` | Page |
| Surface | `#FFFFFF` | Cards, panels |
| Text | `#1B1F24` | Body |
| Muted text | `#5B6570` | Labels, hints |
| Brand/primary | `#1F3864` | Nav, primary buttons |
| Critical | `#C62828` | Band: Critical (marker, chip fill, text) |
| Moderate | `#EF8F00` | Band: Moderate (marker and chip fill only, **never as text**) |
| Moderate text | `#9A4A00` | Band: Moderate when written as text on light backgrounds |
| Low | `#2E7D32` | Band: Low (marker, chip fill, text) |
| Repaired | `#6B7785` (hollow marker) | Status: Repaired |

**Contrast checks** (computed with the WCAG formula; text needs 4.5:1):

| Pair | Ratio | Use |
|---|---|---|
| Text `#1B1F24` on `#F7F8FA` | 15.6:1 | Body text |
| Muted `#5B6570` on `#F7F8FA` | 5.6:1 | Labels |
| White on Critical `#C62828` | 5.6:1 | Critical chip |
| White on Low `#2E7D32` | 5.1:1 | Low chip |
| Dark `#1B1F24` on Moderate `#EF8F00` | 6.8:1 | Moderate chip (dark text on orange fill) |
| Moderate text `#9A4A00` on white | 6.3:1 | Moderate as text |
| Orange `#EF8F00` on white | **2.4:1** | Fails for text, so it is only used as a fill |

Markers sit on a map with changing colors, so marker color alone cannot be guaranteed to stand out. Each marker has a 2 px white outline and is also encoded by size and a "!" icon (Critical), and the legend and side panel state the band in text.

Typography: system font stack only (no web-font download; `next/font/google` needs internet at build time, which can fail on venue Wi-Fi). Sizes: 14 px body, 12 px labels, 20 px section titles, 28 px page title. Spacing in steps of 4/8/16/24 px. Corners 8 px. Light shadows only.

## 6. Components

| Component | Behaviour |
|---|---|
| **Map marker** | Circle. Colour = band, radius scales with priority score, hollow = repaired. Label icon: ! for Critical |
| **Severity chip** | Text label "Low / Medium / High" with colour. Section heading in the panel reads "Relative severity (image-based)", not "depth" |
| **Score breakdown** | Four horizontal bars (severity, traffic, importance, repeat) with their weights, total at the end |
| **Detection preview** | Uploaded image with numbered boxes; box colour by severity |
| **Zone shape** | Soft translucent circle or hull around clustered markers, label shows count and avg priority |
| **Status control** | Dropdown or segmented buttons |
| **Plan list** | Cards per crew, numbered stops, planned date headers |
| **Chart** | Bar/line with axis labels and a data table fallback |
| **Demo-data badge** | Small tag next to traffic/importance values |
| **Threshold note** | Info tooltip next to bands and severity: "Demo thresholds and weights, not validated standards. Severity is a relative estimate from the image, not measured depth." |

## 7. States

Provide for every screen: loading (spinner or skeleton), empty (short message plus a next action), error (plain-language message and retry). See the App Flow doc for exact copy.

## 8. Accessibility

- Text contrast at least 4.5:1 against its background (checked in the table in section 5; orange is used as a fill only).
- Band is conveyed by label and marker size, not color alone (helps color-blind users).
- All buttons reachable by keyboard; visible focus outline.
- Images and charts have text alternatives (alt text, data table).
- Touch targets at least 44 px on the Upload page.

## 9. Responsive behaviour

| Width | Behaviour |
|---|---|
| ≥ 1024 px | Map with filter bar and side panel side by side |
| 640 to 1023 px | Filter bar collapses to a top row; panel overlays |
| < 640 px | Single column; side panel becomes a bottom sheet; Upload is the priority screen |

## 10. Map details

- Base: OpenStreetMap tiles with attribution visible.
- Cluster markers only if more than ~200 potholes (not needed for the demo).
- Default view fits all potholes; remembers filters while navigating.
- Potholes from one photo share the same coordinates. To keep them visible, spread overlapping markers by a tiny offset (about 1 to 2 m) when drawing. This is display only; stored coordinates do not change.

## 11. Demo polish checklist

- [ ] Consistent colors and fonts on all screens
- [ ] Seeded demo data looks realistic and spread across 3 to 4 roads
- [ ] No console errors or placeholder text on screen
- [ ] Mock-data badge present
- [ ] Zoom and map position set sensibly for the demo area

## 12. Implementation notes (Next.js + Tailwind)

- **Tokens:** the colors above live in `frontend/src/app/globals.css` as CSS variables plus a Tailwind `@theme inline` block, so you get classes like `bg-brand`, `text-critical`, `bg-moderate`, `text-moderate-text`. Never use `text-moderate` for text (it fails contrast).
- **Components:** one folder per area under `frontend/src/components/` (`layout`, `map`, `panels`, `upload`, `plan`, `repairs`, `charts`, `ui`). Shared building blocks (chips, buttons, badges) go in `ui`.
- **Map:** Leaflet needs the browser. Load the map component with `next/dynamic` and `ssr: false`, and load Leaflet's CSS once.
- **Charts:** react-chartjs-2 with a data table beside each chart.
- **Responsive:** Tailwind breakpoints (`md:`, `lg:`) following the table in section 9; build the Upload page mobile-first.
- **Data:** components call the Python API through `frontend/src/lib/api.ts`; types live in `frontend/src/lib/types.ts`.
