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
| 1. Images | `prepare_images.py` | `pothole_images/`, `pothole_labels/`: 241 unique photos with YOLO boxes (Roboflow "Potholes Detection", CC BY 4.0, via Hugging Face `Ryukijano/Pothole-detection-Yolov8`; flipped duplicates removed) |
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
python severity.py
python build_real_dataset.py --images pothole_images --bbox 10.95,76.90,11.10,77.05 --fill-missing-synthetic --severity cnn_severity.csv --out data_real
python hybrid.py          # ~2 min on an 8-core laptop CPU (early stopping)
python evaluate.py        # also needs ../backend/ml/weights/pothole.pt for the detector mAP
python schedule.py        # --budget 200000 --crews 2 --hours 8
python explain.py
pytest                    # 19 tests
```
Seeds are fixed (42). Step 3 needs the OpenStreetMap Overpass API; its servers are often busy (we got 406, 500
and 504 before a retry worked). Data folders are git-ignored; scripts rebuild them.

## Results (145 rows on a mapped road: 93 train, 31 val, 21 test; test = grid cells never seen in training)

**Does the model reproduce the reference ranking on unseen areas?**

| Ranking by | Spearman, train | Spearman, test | NDCG@10, test |
|---|---|---|---|
| Model (hybrid net) | 0.989 | 0.743 | 0.856 |
| Severity only | 0.885 | **0.857** | **0.910** |
| First come, first served | 0.025 | -0.277 | 0.550 |
| Random (seed 42) | 0.105 | -0.255 | 0.467 |

Test priority MAE 0.110, RMSE 0.151. The model fits the training areas almost perfectly but, on unseen areas,
**ranks worse than simply sorting by severity**. Reason: in `add_priority` severity multiplies all context
(`severity x (0.35 + 0.65 x context)`), so the reference ranking is mostly severity (Spearman 0.90 with severity
on all rows), and 93 training rows are not enough for the context branch to add signal (see SHAP below).

**Same budget (INR 2 lakh), 2 crews x 8 h, different orders:**

| Strategy | Repairs | Reference priority addressed | High severity fixed within 2 days | Avg repair day, top-25% priority | Vehicle exposure (M) |
|---|---|---|---|---|---|
| Reference formula (upper bound) | 53 | 63.2% | 34.5% | 2.78 | 7.85 |
| **Model** | 52 | **58.4%** | 20.7% | **3.59** | **8.01** |
| Severity only | 52 | 55.9% | **48.3%** | 4.86 | 8.12 |
| First come, first served | 66 | 47.2% | 17.2% | 5.70 | 8.21 |
| Random (seed 42) | 66 | 46.8% | 20.7% | 5.97 | 8.22 |

Vehicle exposure = sum of traffic x severity x days open (days already waiting, which are synthetic, plus days
until repair; not repaired = horizon + 1). The model beats first-come-first-served and random on every measure
and severity-only on priority addressed and time-to-repair for top-priority potholes, but fixes fewer high-severity
potholes quickly than severity-only. Exposure differences are small (2.4% below FCFS) because the synthetic
waiting days dominate that sum. FCFS and random repair more potholes because they pick cheaper (less severe) ones.

**Scheduling:** knapsack picks priority 25.80 for INR 199,975 vs greedy priority-per-rupee 25.76 (greedy is within
0.2% of optimal here). Grouping the selected repairs by DBSCAN cluster saves **13.8%** crew travel (330 vs 383 km
over 10 days with 2 crews) against visiting them in plain priority order. Travel is large because the random points span
a 16 km box.

**Sensitivity:** changing any one context weight of the label formula by -20% or +20% left the top 10 unchanged in
every case (Spearman >= 0.999). Even removing road importance entirely moves scores by at most 0.04. The ranking is
robust to the weights mainly because it is dominated by severity.

**Severity head vs weak labels (test):** MAE 0.110, macro-F1 0.483 over low/medium/high; confusion matrix
(rows = label, columns = prediction) `[[9, 2, 0], [3, 6, 0], [0, 1, 0]]`. The test split has a single high-severity
image, so the high class score is meaningless.

**Detection:** the web app's detector (`Samdutse/pothole-yolov8`) reaches **mAP@0.5 = 0.737** on these 241 annotated
images. It was trained on a different Roboflow pothole set; we cannot rule out overlapping photos.

**Explainability:** `outputs/ranked_potholes.csv` shows, per pothole, every term of the label formula (severity base,
each context factor x weight, age, safety-floor uplift). SHAP on the tabular branch (image fixed at the average
training embedding) gives mean |SHAP| of at most 0.003 per feature (largest: school and hospital proximity), so
**the trained model relies almost entirely on the image**. The plan's required orderings still hold: a medium
pothole next to a hospital outranks a small one on a highway (0.339 vs 0.138), and a severe highway pothole
outranks a severe residential one (0.674 vs 0.653, a thin margin; the label gives 0.920 vs 0.459). Tests:
`tests/test_hybrid_model.py`.

## Limitations
- Labels are our own formulas (weak box-based severity, rule-based priority). The model reproduces them; it is not validated against real repair decisions.
- Photo locations are random points (`location_source = random_bbox`), so road and facility context is real for the point but unrelated to the photo.
- Traffic is estimated from road class; junction/curve/accident/complaint/age columns are synthetic. Speed limits are class defaults for 143 of 145 rows.
- Small data: 145 rows (5 highway, 7 arterial). The image branch overfits (train loss 0.003 vs validation 0.058); the context branch learns almost nothing.
- Repair costs and crew hours use assumed rates (`schedule.py` constants), not tender data.
- The same 241 photos are used for every step; there is no second, independent image source.
- On this data, sorting by severity alone ranks unseen areas better than the trained model. To make the context matter, the label formula (or real priority data) would have to weight context more, and many more rows would be needed.
