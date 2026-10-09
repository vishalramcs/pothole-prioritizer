# ML pipeline: learned pothole priority (real images + OpenStreetMap context)

A research companion to the SRPPS web app. It trains a two-branch network that takes a pothole photo plus
road/location context and outputs a repair priority and a severity, then schedules repairs under a budget,
explains the ranking, and evaluates it against simple baselines.

**Read this first.** The training labels come from our own formulas: severity from the annotated box sizes, and
priority from `add_priority()` in `build_real_dataset.py`. **The model learns those formulas.** It cannot know
anything about real-world urgency that the formulas do not encode, and the photo locations are random points
(see `DATA_NOTES.md` for what is real, estimated, synthetic and rule-based).

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1. Images | `prepare_images.py`, `prepare_rdd2022.py` | `pothole_images/`, `pothole_labels/`: **1,041 photos with hand-drawn pothole boxes** from two CC BY 4.0 sources: 241 from Roboflow "Potholes Detection" (via Hugging Face `Ryukijano/Pothole-detection-Yolov8`, flipped duplicates removed) and a seeded 800 of the 1,530 RDD2022 India images that contain a pothole (class D40) |
| 2. Severity | `severity.py` | `cnn_severity.csv`: **weak labels** from the boxes, `(0.5*clip(area/0.3) + 0.2*clip(count/8)) / 0.7` (no depth data) |
| 3. Context | `build_real_dataset.py` | `data_real/`: OSM road class, facilities and bus stops for random points in the Coimbatore box; estimated traffic; synthetic risk/complaint columns; rule-based priority; spatial split |
| 4. Model | `hybrid.py` | `models/hybrid_best.pt`, `outputs/train_curve.*`: ResNet18 image branch (ImageNet weights, only layer4 trained) + tabular MLP (road-class embedding + 13 context features) -> priority head; auxiliary severity head on the image branch. Loss MSE(priority) + 0.5 MSE(severity) + 0.3 margin-ranking loss |
| 7. Evaluation | `evaluate.py` | `outputs/scored.csv`, `outputs/evaluation.json` |
| 5. Scheduling | `schedule.py` | `outputs/daily_schedule.csv`: cost/hours from severity (assumed rates), 0/1 knapsack vs greedy, DBSCAN cluster bonus, nearest-neighbour route, crew-days |
| 6. Explain | `explain.py` | `outputs/ranked_potholes.csv` (formula breakdown per pothole), `outputs/shap_tabular.*`, `outputs/priority_map.html` |

## How to run
From `ml_pipeline/`, with Python 3.12 and `numpy pandas pillow torch torchvision scikit-learn scipy matplotlib
ultralytics huggingface_hub shap folium` (CPU is enough):
```bash
python -c "from huggingface_hub import snapshot_download as s; s('Ryukijano/Pothole-detection-Yolov8', repo_type='dataset', local_dir='raw/ryukijano')"
python prepare_images.py
python prepare_rdd2022.py # downloads only India.zip (0.53 GB) out of the 13 GB RDD2022 archive
python severity.py
python build_real_dataset.py --images pothole_images --bbox 10.95,76.90,11.10,77.05 --fill-missing-synthetic --severity cnn_severity.csv --out data_real
python hybrid.py          # ~7 min on an 8-core laptop CPU (early stopping)
python evaluate.py        # also needs ../backend/ml/weights/pothole.pt for the detector mAP
python schedule.py        # --budget 200000 --crews 2 --hours 8
python explain.py
pytest                    # 19 tests
```
`python build_real_dataset.py ... --osm-json data_real/osm_cache.json` reuses a saved OSM download. Seeds are fixed (42). Step 3 needs the OpenStreetMap Overpass API; its servers are often busy (we got 406, 500
and 504 before a retry worked). Data folders are git-ignored; scripts rebuild them.

## Results (1,041 images; 597 on a mapped road: 406 train, 102 val, 89 test; test = grid cells never seen in training)

Training: early stop at epoch 22, best validation loss 0.0425 (train 0.003). Test priority MAE 0.079, RMSE 0.122.

**Does the model reproduce the reference ranking on unseen areas?**

| Ranking by | Spearman, train | Spearman, test | NDCG@10, test |
|---|---|---|---|
| Model (hybrid net) | 0.952 | 0.679 | 0.630 |
| Severity only | 0.958 | **0.951** | **0.776** |
| First come, first served | 0.099 | 0.327 | 0.374 |
| Random (seed 42) | 0.006 | -0.070 | 0.394 |

**The model ranks unseen areas clearly worse than sorting by severity.** In `add_priority` severity multiplies all
context (`severity x (0.35 + 0.65 x context)`), so the reference ranking is almost a severity ranking, and the
network's context branch adds noise rather than signal. A first run on 145 rows showed the same (model 0.743 vs
severity 0.857); 4x more data did not close the gap.

**Same budget (INR 2 lakh, enough for about 56 of 597 repairs), 2 crews x 8 h, different orders:**

| Strategy | Repairs | Reference priority addressed | High severity fixed within 2 days | Vehicle exposure (M) |
|---|---|---|---|---|
| Reference formula (upper bound) | 59 | 30.1% | 31.1% | 25.48 |
| **Model** | 52 | **25.3%** | 24.4% | 25.59 |
| Severity only | 49 | 21.6% | **28.9%** | 25.80 |
| First come, first served | 79 | 15.5% | 4.4% | 25.37 |
| Random (seed 42) | 82 | 12.9% | 6.7% | 25.27 |

The model addresses more reference priority within the budget than severity-only (it also weighs cost-relevant
context), and both beat first-come-first-served and random by far on priority and on fixing severe potholes
quickly. Exposure and "average repair day of the top-25% potholes" barely differ (25.3 to 25.8; 6.4 to 6.7 days):
the budget covers under a tenth of the potholes, so most priority potholes stay open in every strategy, and the
synthetic waiting days dominate the exposure sum. FCFS and random repair more potholes because they pick cheaper
(less severe) ones.

**Scheduling:** knapsack priority 31.71 for exactly INR 200,000 vs greedy 31.63 (within 0.3%). Clustering did
**not** save travel here (319 vs 317 km, -0.9%): the 56 chosen repairs are scattered over a 16 km box, so few share a
cluster. On the 145-row run it saved 13.8%. The cluster bonus only helps when chosen repairs are close together.

**Sensitivity:** changing any one context weight of the label formula by -20% or +20% left the top 10 unchanged
(Spearman 1.000), again because severity dominates the formula.

**Severity head vs weak labels (test):** MAE 0.100, macro-F1 0.436; confusion (rows = label, columns = prediction,
low/medium/high) `[[58, 8, 0], [11, 9, 1], [0, 2, 0]]`. Only 2 high-severity test images.

**Detection:** the web app's detector (`Samdutse/pothole-yolov8`) reaches **mAP@0.5 = 0.464** on all 1,041 images
(0.737 on the 241 Roboflow images alone). RDD2022's dashcam potholes are small and far away, unlike the close-ups the
detector was trained on.

**Explainability:** `outputs/ranked_potholes.csv` gives every term of the label formula per pothole. SHAP on the
tabular branch: mean |SHAP| at most 0.008 (hospital proximity, then school proximity and junctions), so the model still
relies almost entirely on the image. The plan's required orderings hold on the trained model (a medium pothole next
to a hospital outranks a small highway pothole; a severe highway pothole outranks a severe residential one), checked
by `tests/test_hybrid_model.py`.

**What to take from this:** with labels from this formula, a neural network adds no ranking skill over severity; its
value would only appear with labels that depend on context more (or with real repair-priority decisions to learn from).

## Limitations
- Labels are our own formulas (weak box-based severity, rule-based priority). The model reproduces them; it is not validated against real repair decisions.
- Photo locations are random points (`location_source = random_bbox`), so road and facility context is real for the point but unrelated to the photo.
- Traffic is estimated from road class; junction/curve/accident/complaint/age columns are synthetic. Speed limits are almost all class defaults (OSM rarely tags maxspeed here).
- Small data for a learned ranking: 597 rows (28 highway, 22 arterial). The image branch fits training well (loss 0.003 vs validation 0.043); the context branch learns almost nothing.
- Two image sources look different: RDD2022 dashcam potholes are small and distant, so their box-based severity is lower (median 0.13 vs 0.37). Severity therefore partly measures camera distance.
- Repair costs and crew hours use assumed rates (`schedule.py` constants), not tender data.
- A real-GPS source (Outerview, 553 Mumbai photos) was tried and rejected because its labels are mostly wrong (see DATA_NOTES.md), so all locations remain random.
- On this data, sorting by severity alone ranks unseen areas better than the trained model. To make the context matter, the label formula (or real priority data) would have to weight context more, and many more rows would be needed.
