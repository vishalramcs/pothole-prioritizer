# Data notes: what is real, estimated, synthetic and rule-based

**This is not a fully real dataset.** Real pothole photos are combined with real OpenStreetMap context at made-up
locations, plus estimated and synthetic columns. Read the table before quoting any result.

Built with:
```
python prepare_images.py
python prepare_rdd2022.py
python severity.py
python build_real_dataset.py --images pothole_images --bbox 10.95,76.90,11.10,77.05 --fill-missing-synthetic --severity cnn_severity.csv --out data_real
```
then only rows with `road_match_ok == 1` are used.

| Columns | Status | Source |
|---|---|---|
| Image pixels and pothole boxes | **real** | 1,041 photos with hand-drawn boxes: 241 from Roboflow "Potholes Detection" (CC BY 4.0, via Hugging Face `Ryukijano/Pothole-detection-Yolov8`, flipped duplicates removed) and 800 (seeded sample of 1,530) RDD2022 India images with a pothole box, class D40 (CC BY 4.0, figshare 21431547). Files from RDD2022 start with `rdd_` |
| `lat`, `lon` (`location_source = random_bbox`) | **synthetic** | The photos have no GPS. Each was given a random point (seed 42) in the Coimbatore box 10.95,76.90 to 11.10,77.05. The point is **not** where the photo was taken |
| `road_class`, `osm_highway_tag`, `road_name`, `road_snap_dist_m` | **real for that point** | Nearest OpenStreetMap road to the random point (Overpass download of 9 Oct 2026, cached in `data_real/osm_cache.json`) |
| `speed_limit_kmph` | **mostly estimated** | OSM `maxspeed` tag for very few rows (2 of the first 145); the rest use a default per road class |
| `dist_hospital_m`, `dist_school_m`, `dist_fire_station_m`, `dist_bus_stop_m`, `critical_facilities_500m` | **real for that point** | Distances to OSM facilities (clinics count as hospitals in this script) |
| `traffic_vehicles_per_day` | **estimated** | Random draw around a typical value for the road class (`traffic_source = estimated_from_road_class`) |
| `is_junction`, `is_curve_or_bridge`, `past_accidents_nearby`, `complaint_count`, `days_unrepaired`, `rain_or_poor_lighting` | **synthetic** | Random values (seed 42), listed in the `synthetic_columns` column |
| `severity`, `pothole_area_ratio`, `pothole_count` | **weak labels** | Computed from the hand-drawn boxes (`severity.py`); no depth, no expert severity grade |
| `priority_score`, `priority_rank` | **rule-based** | `add_priority()` in `build_real_dataset.py`. There is no public ground truth for repair priority |
| `split` | derived | Whole ~3 km grid cells go to train/val/test. Because image locations are random, this separates **areas of context**, not photo sources |

Rows: 1,041 built, **597 kept** (`road_match_ok == 1`: random point within 30 m of a mapped road). Split: 406 train, 102 val, 89 test.
Road classes kept: 468 residential, 79 town, 22 arterial, 28 highway. Severity differs by source (RDD2022 dashcam potholes are distant: median weak severity 0.13 vs 0.37 for the Roboflow close-ups).
The OSM data is the download of 9 Oct 2026 (`data_real/osm_cache.json`, reused with `--osm-json`).

## Sources checked and rejected

- **Outerview Global Potholes Dataset** (Hugging Face, CC BY 4.0; imagery from Mapillary). Attractive because every
  photo has real GPS (553 in Mumbai; `prepare_outerview.py` fetches them). Rejected: its "pothole" labels come from
  Outerview's own AI. Running our detector at confidence 0.4 kept 136 of 553 (`detect_boxes.py`), and a visual check
  of 12 random kept photos found only about 3 plausible potholes (the rest: dirt, rubble, litter, paving, a manhole,
  a grate); 12 random rejected photos showed none. Training on it would mean training on mostly wrong labels.
- **Roboflow full export** of "Potholes Detection" (13,767 images) and **Kaggle** sets: need a login or API key, so
  not downloaded automatically (RDD2022 India was used instead). Manual route: download the YOLOv8 export from
  universe.roboflow.com/project-ssayl/potholes-detection-d4rma in a browser and unzip it into `raw/ryukijano`.

Consequences:
- A model trained on `priority_score` learns the `add_priority` formula, and severity heads learn the box formula. Good test scores mean the model reproduces those formulas, not that it knows real-world priority.
- "Generalises to unseen areas" here means: it scores context from grid cells it never saw. The photos themselves are not tied to those areas.
- Licences: photos CC BY 4.0 (attribute "Potholes Detection" by Roboflow user project-ssayl, and RDD2022 by Arya et al., CRDDC 2022); OSM data (c) OpenStreetMap contributors, ODbL.
