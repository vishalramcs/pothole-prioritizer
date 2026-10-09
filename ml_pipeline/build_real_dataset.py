"""
Build a REAL-context pothole dataset from real images + OpenStreetMap.

What is real:   image locations (EXIF GPS or your CSV), road class / road name / speed tag,
                distances to hospitals, schools, fire stations, bus stops (all from OSM).
What is NOT:    traffic volume (estimated from road class), complaint/accident/age columns
                (only filled if you pass --fill-missing-synthetic, and then flagged),
                priority_score (rule-based label, there is no public ground truth).

Needs internet (OSM Overpass). Install: pip install numpy pandas pillow

Examples
  # photos with GPS in EXIF (e.g. your own phone photos, Mapillary downloads)
  python build_real_dataset.py --images photos/ --out data_real

  # images without GPS: give your own coordinates per image
  python build_real_dataset.py --images imgs/ --locations locations.csv --out data_real
      (locations.csv columns: image_file,lat,lon)

  # no coordinates at all (e.g. RDD2022): assign points inside a bounding box. These are
  # flagged location_source=random_bbox, so the road/facility values are real for that
  # point but the point itself is not where the image was taken.
  python build_real_dataset.py --images imgs/ --bbox 10.95,76.90,11.10,77.05 --out data_real

  # add severity from your CNN (csv: image_file,severity[,pothole_area_ratio,pothole_count,depth_cm])
  python build_real_dataset.py ... --severity cnn_severity.csv
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request
import numpy as np
import pandas as pd

OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

# OSM highway tag -> project road class
ROAD_MAP = {"motorway": "highway", "motorway_link": "highway", "trunk": "highway", "trunk_link": "highway",
            "primary": "highway", "primary_link": "highway",
            "secondary": "arterial", "secondary_link": "arterial",
            "tertiary": "town", "tertiary_link": "town", "unclassified": "town",
            "residential": "residential", "living_street": "residential", "service": "residential"}
IMPORTANCE = {"highway": 1.0, "arterial": 0.7, "town": 0.4, "residential": 0.2}
DEFAULT_SPEED = {"highway": 80, "arterial": 50, "town": 35, "residential": 25}
TRAFFIC_MEDIAN = {"highway": 40000, "arterial": 15000, "town": 5000, "residential": 800}
QUERY_WAYS = "|".join(ROAD_MAP)


# ---------------------------------------------------------------- locations
def exif_gps(path):
    """Return (lat, lon) from image EXIF, or None."""
    try:
        from PIL import Image
        gps = Image.open(path).getexif().get_ifd(0x8825)
        if not gps or 2 not in gps or 4 not in gps:
            return None
        def deg(v, ref):
            d = float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
            return -d if ref in ("S", "W") else d
        return deg(gps[2], gps.get(1, "N")), deg(gps[4], gps.get(3, "E"))
    except Exception:
        return None


def get_locations(files, img_dir, loc_csv, bbox, seed):
    loc = {}
    if loc_csv:
        t = pd.read_csv(loc_csv)
        loc = {r.image_file: (float(r.lat), float(r.lon), "csv") for r in t.itertuples()}
    rng = np.random.default_rng(seed)
    out = []
    for f in files:
        if f in loc:
            out.append(loc[f]); continue
        g = exif_gps(os.path.join(img_dir, f))
        if g:
            out.append((g[0], g[1], "exif")); continue
        if bbox:
            la0, lo0, la1, lo1 = bbox
            out.append((rng.uniform(la0, la1), rng.uniform(lo0, lo1), "random_bbox")); continue
        out.append((np.nan, np.nan, "missing"))
    return out


# ---------------------------------------------------------------- OSM
def fetch_overpass(south, west, north, east, cache):
    if cache and os.path.exists(cache):
        print(f"Using cached OSM data: {cache}")
        return json.load(open(cache))
    bb = f"{south},{west},{north},{east}"
    q = f"""[out:json][timeout:120];
(
  way["highway"~"^({QUERY_WAYS})$"]({bb});
  nw["amenity"~"^(hospital|clinic|school|fire_station)$"]({bb});
  node["highway"="bus_stop"]({bb});
);
out geom;"""
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for url in OVERPASS:
        try:
            print("Querying", url)
            with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=180) as r:
                js = json.load(r)
            if cache:
                json.dump(js, open(cache, "w"))
            return js
        except Exception as e:
            last = e; print("  failed:", e); time.sleep(2)
    sys.exit(f"Could not reach Overpass ({last}). Run this on a machine with internet access.")


def parse_osm(js):
    segs, facilities, bus = [], [], []   # segs: x1,y1,x2,y2 as lat/lon, class, tag, name, speed
    for el in js.get("elements", []):
        tags = el.get("tags", {})
        geom = el.get("geometry")
        if el["type"] == "way" and "highway" in tags and tags["highway"] in ROAD_MAP and geom:
            cls = ROAD_MAP[tags["highway"]]
            sp = parse_speed(tags.get("maxspeed"))
            for a, b in zip(geom[:-1], geom[1:]):
                segs.append((a["lat"], a["lon"], b["lat"], b["lon"], cls, tags["highway"],
                             tags.get("name", ""), sp))
            continue
        # points of interest
        if el["type"] == "node":
            lat, lon = el.get("lat"), el.get("lon")
        elif geom:
            lat = float(np.mean([g["lat"] for g in geom])); lon = float(np.mean([g["lon"] for g in geom]))
        else:
            continue
        if lat is None:
            continue
        if tags.get("highway") == "bus_stop":
            bus.append((lat, lon))
        elif tags.get("amenity") in ("hospital", "clinic", "school", "fire_station"):
            kind = {"clinic": "hospital"}.get(tags["amenity"], tags["amenity"])
            facilities.append((lat, lon, kind))
    return segs, facilities, bus


def parse_speed(v):
    if not v:
        return np.nan
    m = re.search(r"\d+", str(v))
    if not m:
        return np.nan
    s = float(m.group())
    return s * 1.609 if "mph" in str(v) else s


# ---------------------------------------------------------------- geometry
def to_xy(lat, lon, lat0):
    return (np.asarray(lon) * 111320.0 * np.cos(np.radians(lat0)), np.asarray(lat) * 110540.0)


def nearest_distance(px, py, qx, qy):
    """min distance from each point to a set of points (chunked)."""
    if len(qx) == 0:
        return np.full(len(px), np.inf)
    out = np.empty(len(px))
    for i in range(0, len(px), 200):
        d = np.hypot(px[i:i + 200, None] - qx[None, :], py[i:i + 200, None] - qy[None, :])
        out[i:i + 200] = d.min(axis=1)
    return out


def count_within(px, py, qx, qy, r):
    if len(qx) == 0:
        return np.zeros(len(px), int)
    out = np.empty(len(px), int)
    for i in range(0, len(px), 200):
        d = np.hypot(px[i:i + 200, None] - qx[None, :], py[i:i + 200, None] - qy[None, :])
        out[i:i + 200] = (d <= r).sum(axis=1)
    return out


def snap_to_roads(px, py, segs, lat0, tol=10.0):
    """Nearest road segment per point; among roads within `tol` m of the nearest, take the most important."""
    s = pd.DataFrame(segs, columns=["la1", "lo1", "la2", "lo2", "cls", "tag", "name", "speed"])
    x1, y1 = to_xy(s.la1, s.lo1, lat0); x2, y2 = to_xy(s.la2, s.lo2, lat0)
    imp = s.cls.map(IMPORTANCE).values
    res = []
    for i in range(len(px)):
        dx, dy = x2 - x1, y2 - y1
        L2 = np.maximum(dx * dx + dy * dy, 1e-9)
        t = np.clip(((px[i] - x1) * dx + (py[i] - y1) * dy) / L2, 0, 1)
        d = np.hypot(px[i] - (x1 + t * dx), py[i] - (y1 + t * dy))
        dmin = d.min()
        cand = np.where(d <= dmin + tol)[0]
        j = cand[np.argmax(imp[cand])]
        res.append((s.cls.iat[j], s.tag.iat[j], s.name.iat[j], s.speed.iat[j], float(d[j])))
    return pd.DataFrame(res, columns=["road_class", "osm_highway_tag", "road_name", "osm_maxspeed", "road_snap_dist_m"])


# ---------------------------------------------------------------- priority label
def prox(d, scale=500.0):
    return np.exp(-d / scale)


def add_priority(df):
    imp = df.road_class.map(IMPORTANCE).values
    fac = np.maximum.reduce([prox(df.dist_hospital_m.values), 0.8 * prox(df.dist_school_m.values),
                             0.6 * prox(df.dist_fire_station_m.values), 0.3 * prox(df.dist_bus_stop_m.values, 300)])
    traffic_n = np.clip(np.log1p(df.traffic_vehicles_per_day) / np.log1p(60000), 0, 1)
    speed_n = np.clip(df.speed_limit_kmph / 100, 0, 1)
    age_n = (np.clip(df.days_unrepaired / 90, 0, 1) * 0.5 + np.clip(df.complaint_count / 10, 0, 1) * 0.5).fillna(0)
    risk = np.clip(0.4 * df.is_junction + 0.3 * df.is_curve_or_bridge + 0.1 * np.clip(df.past_accidents_nearby / 4, 0, 1)
                   + 0.2 * df.rain_or_poor_lighting, 0, 1).fillna(0)
    ctx = 0.30 * imp + 0.25 * fac + 0.20 * traffic_n + 0.10 * speed_n + 0.15 * risk
    sev = df.severity.values
    p = sev * (0.35 + 0.65 * ctx) + 0.08 * age_n
    near = ((df.dist_hospital_m < 300) | (df.dist_school_m < 300)) & (sev > 0.25)
    p = np.where(near, np.maximum(p, 0.45 + 0.3 * sev), p)
    p = np.where((sev > 0.85) & df.road_class.isin(["highway", "arterial"]), np.maximum(p, 0.92), p)
    df["priority_score"] = np.clip(p, 0, 1).round(4)
    df["priority_rank"] = df.priority_score.rank(ascending=False, method="first").astype(int)
    return df


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--locations", help="csv: image_file,lat,lon")
    ap.add_argument("--bbox", help="lat_min,lon_min,lat_max,lon_max (fallback for images with no GPS)")
    ap.add_argument("--severity", help="csv: image_file,severity[,pothole_area_ratio,pothole_count,depth_cm]")
    ap.add_argument("--osm-json", help="cached/saved Overpass response (skips the download)")
    ap.add_argument("--fill-missing-synthetic", action="store_true",
                    help="fill complaints/accidents/age/junction columns with flagged synthetic values")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data_real")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)  # before the OSM cache is written into it

    files = sorted(f for f in os.listdir(a.images) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    if not files:
        sys.exit("No images found.")
    bbox = tuple(float(v) for v in a.bbox.split(",")) if a.bbox else None
    locs = get_locations(files, a.images, a.locations, bbox, a.seed)
    df = pd.DataFrame({"pothole_id": [f"P{i:05d}" for i in range(len(files))], "image_file": files,
                       "lat": [l[0] for l in locs], "lon": [l[1] for l in locs],
                       "location_source": [l[2] for l in locs]})
    miss = df.lat.isna().sum()
    if miss:
        print(f"WARNING: {miss} images have no location and are dropped (give --locations or --bbox).")
        df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    print("Location sources:", df.location_source.value_counts().to_dict())

    pad = 0.01
    south, north = df.lat.min() - pad, df.lat.max() + pad
    west, east = df.lon.min() - pad, df.lon.max() + pad
    if (north - south) > 0.6 or (east - west) > 0.6:
        print("WARNING: points span a very large area; the OSM query may be slow or time out.")
    js = json.load(open(a.osm_json)) if a.osm_json else fetch_overpass(south, west, north, east,
                                                                         os.path.join(a.out, "osm_cache.json"))
    segs, fac, bus = parse_osm(js)
    print(f"OSM: {len(segs)} road segments, {len(fac)} hospitals/schools/fire stations, {len(bus)} bus stops")
    if not segs:
        sys.exit("No roads found in the area. Check coordinates.")

    lat0 = float(df.lat.mean())
    px, py = to_xy(df.lat, df.lon, lat0)
    snapped = snap_to_roads(px, py, segs, lat0)
    df = pd.concat([df, snapped], axis=1)
    # a point more than 30 m from any mapped road is probably not on that road (common with random_bbox points)
    df["road_match_ok"] = (df.road_snap_dist_m <= 30).astype(int)
    bad = int((df.road_match_ok == 0).sum())
    if bad:
        print(f"WARNING: {bad} of {len(df)} points are >30 m from any OSM road (road_match_ok=0). "
              "Filter them out for a clean dataset: df[df.road_match_ok == 1].")
    df["speed_limit_kmph"] = df.osm_maxspeed.fillna(df.road_class.map(DEFAULT_SPEED)).round()
    df["speed_source"] = np.where(df.osm_maxspeed.notna(), "osm_tag", "class_default")

    F = pd.DataFrame(fac, columns=["lat", "lon", "kind"])
    for kind, col in [("hospital", "dist_hospital_m"), ("school", "dist_school_m"), ("fire_station", "dist_fire_station_m")]:
        k = F[F.kind == kind]
        qx, qy = to_xy(k.lat, k.lon, lat0)
        df[col] = nearest_distance(px, py, qx, qy).round(0)
    bx, by = to_xy([b[0] for b in bus], [b[1] for b in bus], lat0) if bus else (np.array([]), np.array([]))
    df["dist_bus_stop_m"] = nearest_distance(px, py, bx, by).round(0)
    fx, fy = to_xy(F.lat, F.lon, lat0) if len(F) else (np.array([]), np.array([]))
    df["critical_facilities_500m"] = count_within(px, py, fx, fy, 500)
    # no facility of a type in the area -> large finite distance instead of inf
    for c in ["dist_hospital_m", "dist_school_m", "dist_fire_station_m", "dist_bus_stop_m"]:
        df[c] = df[c].replace(np.inf, 20000.0)

    rng = np.random.default_rng(a.seed)
    df["traffic_vehicles_per_day"] = [int(rng.lognormal(np.log(TRAFFIC_MEDIAN[c]), 0.3)) for c in df.road_class]
    df["traffic_source"] = "estimated_from_road_class"

    synth = ["traffic_vehicles_per_day"]
    for c in ["is_junction", "is_curve_or_bridge", "past_accidents_nearby", "complaint_count",
              "days_unrepaired", "rain_or_poor_lighting"]:
        df[c] = np.nan
    if a.fill_missing_synthetic:
        n = len(df)
        df["is_junction"] = (rng.random(n) < 0.18).astype(int)
        df["is_curve_or_bridge"] = (rng.random(n) < 0.10).astype(int)
        df["past_accidents_nearby"] = rng.poisson(0.4 + 1.2 * (df.road_class == "highway"))
        df["complaint_count"] = rng.poisson(2.5, n) + 1
        df["days_unrepaired"] = rng.integers(1, 90, n)
        df["rain_or_poor_lighting"] = (rng.random(n) < 0.25).astype(int)
        synth += ["is_junction", "is_curve_or_bridge", "past_accidents_nearby", "complaint_count",
                  "days_unrepaired", "rain_or_poor_lighting"]
    df["synthetic_columns"] = ",".join(synth)

    if a.severity:
        sv = pd.read_csv(a.severity)
        df = df.merge(sv, on="image_file", how="left")
        missing = int(df.severity.isna().sum())
        if missing:  # never invent a severity: drop images the severity step did not cover
            print(f"WARNING: {missing} images have no severity in {a.severity} and are dropped.")
            df = df.dropna(subset=["severity"]).reset_index(drop=True)
        if len(df):
            df = add_priority(df)
    else:
        print("No --severity file: severity/priority columns not added yet (add them after CNN inference).")

    # spatial split: grid cells of ~0.03 deg assigned whole to train/val/test
    cell = (np.floor((df.lat - df.lat.min()) / 0.03).astype(int) * 1000 + np.floor((df.lon - df.lon.min()) / 0.03).astype(int))
    u = np.unique(cell)
    r = np.random.default_rng(a.seed + 2).permutation(len(u))
    cut1, cut2 = int(0.7 * len(u)), int(0.85 * len(u))
    lab = {c: ("train" if k < cut1 else "val" if k < cut2 else "test") for c, k in zip(u, r)}
    df["split"] = [lab[c] for c in cell]

    df.to_csv(os.path.join(a.out, "pothole_dataset_real_context.csv"), index=False)
    print(f"\nWrote {len(df)} rows -> {a.out}/pothole_dataset_real_context.csv")
    print(df.road_class.value_counts().to_dict())


if __name__ == "__main__":
    main()
