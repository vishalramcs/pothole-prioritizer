"""P0 API tests against a real (migrated + seeded) Postgres. Each test is rolled back."""
import io
import math
from datetime import date
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import text

from app.core.config import get_settings
from app.repositories import potholes, uploads
from app.services import detector, status

SAMPLES = Path(__file__).resolve().parents[2] / "sample_data" / "images"
STATUSES = ["Pending", "Scheduled", "In Progress", "Repaired"]
ALLOWED = {
    ("Scheduled", "Pending"), ("Pending", "In Progress"), ("Scheduled", "In Progress"),
    ("Pending", "Repaired"), ("Scheduled", "Repaired"), ("In Progress", "Repaired"),
}


def road_id(conn, name="Demo Highway") -> int:
    return conn.execute(text("SELECT road_id FROM roads WHERE name = :n"), {"n": name}).scalar_one()


def make_pothole(conn, current="Pending", lat=12.97, lng=77.59, road="Demo Highway") -> int:
    up = uploads.insert(conn, storage_path="uploads/test.jpg", media_type="image", lat=lat, lng=lng,
                        gps_source="manual", road_id=road_id(conn, road), image_width=100, image_height=100)
    pid = potholes.insert(conn, upload_id=up, road_id=road_id(conn, road), lat=lat, lng=lng,
                          severity_score=0.5, severity_level="Medium")
    crew = conn.execute(text("SELECT min(crew_id) FROM crews")).scalar_one()
    if current in ("Scheduled", "In Progress", "Repaired"):
        status.schedule(conn, pid, crew, 1, date.today())
    if current in ("In Progress", "Repaired"):
        status.change_status(conn, pid, "In Progress")
    if current == "Repaired":
        status.change_status(conn, pid, "Repaired")
    return pid


def order_of(conn, pid):
    return conn.execute(text("SELECT * FROM repair_orders WHERE pothole_id = :p"), {"p": pid}).mappings().first()


def jpeg(size=(640, 480)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (90, 90, 90)).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def fake_detector(monkeypatch):
    """Two fixed boxes: area ratios 0.09 (High) and 0.01 (Low) on a 640x480 image."""
    boxes = [
        {"bbox_x": 10, "bbox_y": 10, "bbox_w": 192, "bbox_h": 144, "confidence": 0.9},
        {"bbox_x": 300, "bbox_y": 300, "bbox_w": 64, "bbox_h": 48, "confidence": 0.6},
    ]
    monkeypatch.setattr(detector, "detect", lambda img, min_conf: [dict(b) for b in boxes])


# ---------- status model (TRD 4.9) ----------

@pytest.mark.parametrize("current", STATUSES)
@pytest.mark.parametrize("new", STATUSES)
def test_every_status_change_follows_trd_table(client, conn, current, new):
    pid = make_pothole(conn, current)
    r = client.patch(f"/api/potholes/{pid}/status", json={"status": new})
    if (current, new) in ALLOWED:
        assert r.status_code == 200, r.json()
        assert r.json()["status"] == new
    else:
        assert r.status_code == 409
        assert r.json() == {"error": "Invalid status change"}
        assert potholes.get(conn, pid)["status"] == current


def test_unschedule_deletes_order(client, conn):
    pid = make_pothole(conn, "Scheduled")
    assert order_of(conn, pid) is not None
    client.patch(f"/api/potholes/{pid}/status", json={"status": "Pending"})
    assert order_of(conn, pid) is None


def test_start_keeps_order(client, conn):
    pid = make_pothole(conn, "Scheduled")
    client.patch(f"/api/potholes/{pid}/status", json={"status": "In Progress"})
    assert order_of(conn, pid) is not None


def test_repaired_sets_times(client, conn):
    pid = make_pothole(conn, "Scheduled")
    client.patch(f"/api/potholes/{pid}/status", json={"status": "Repaired"})
    p = potholes.get(conn, pid)
    assert p["repaired_at"] is not None and p["zone_id"] is None
    assert order_of(conn, pid)["completed_at"] is not None


def test_repaired_without_order(client, conn):
    pid = make_pothole(conn, "Pending")
    assert client.patch(f"/api/potholes/{pid}/status", json={"status": "Repaired"}).status_code == 200
    assert potholes.get(conn, pid)["repaired_at"] is not None


def test_status_unknown_pothole_and_bad_value(client):
    assert client.patch("/api/potholes/999999/status", json={"status": "Repaired"}).status_code == 404
    r = client.patch("/api/potholes/1/status", json={"status": "Done"})
    assert r.status_code == 400 and "error" in r.json()


# ---------- upload (TRD 5, 6) ----------

def upload(client, conn, data=None, **form):
    # a spot with no facilities nearby, so the expected scores below have no facility term
    form = {"road_id": road_id(conn), "lat": 47.0, "lng": 12.0, **form}
    form = {k: v for k, v in form.items() if v is not None}
    return client.post("/api/uploads", data=form, files={"file": ("photo.jpg", data or jpeg(), "image/jpeg")})


def test_upload_saves_scored_potholes(client, conn, fake_detector):
    r = upload(client, conn)
    assert r.status_code == 200, r.json()
    body = r.json()
    assert (body["image_width"], body["image_height"]) == (640, 480)
    high, low = body["potholes"]
    assert high["severity_level"] == "High" and high["area_ratio"] == pytest.approx(0.09)
    assert low["severity_level"] == "Low"
    # severity 0.9 on Demo Highway (traffic 0.9, importance 1.0), no repeats, no facility
    assert high["priority_score"] == pytest.approx(0.9 * 0.40 + 0.9 * 0.20 + 1.0 * 0.15)
    assert high["priority_band"] == "Moderate"  # 0.69: just under Critical (0.70)
    listed = client.get("/api/potholes").json()
    assert {p["pothole_id"] for p in listed} >= {high["pothole_id"], low["pothole_id"]}


def test_upload_image_is_stored_and_served(client, conn, fake_detector):
    pid = upload(client, conn).json()["potholes"][0]["pothole_id"]
    r = client.get(f"/api/potholes/{pid}/image")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert Image.open(io.BytesIO(r.content)).size == (640, 480)


def test_detail_breakdown_adds_up(client, conn, fake_detector):
    pid = upload(client, conn).json()["potholes"][0]["pothole_id"]
    p = client.get(f"/api/potholes/{pid}").json()
    assert sum(b["contribution"] for b in p["breakdown"].values()) == pytest.approx(p["priority_score"])
    assert "image_path" not in p


def test_upload_no_potholes_is_not_an_error(client, conn, monkeypatch):
    monkeypatch.setattr(detector, "detect", lambda img, min_conf: [])
    r = upload(client, conn)
    assert r.status_code == 200 and r.json()["potholes"] == []


def test_upload_rejects_non_image(client, conn, fake_detector):
    r = upload(client, conn, data=b"%PDF-1.4 not an image")
    assert r.status_code == 400 and "JPG or PNG" in r.json()["error"]


def test_upload_rejects_other_image_formats(client, conn, fake_detector):
    buf = io.BytesIO()
    Image.new("RGB", (20, 20)).save(buf, "GIF")
    assert upload(client, conn, data=buf.getvalue()).status_code == 400


def test_upload_too_large(client, conn, fake_detector, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    assert upload(client, conn).status_code == 413


def test_upload_without_any_gps(client, conn, fake_detector):
    r = upload(client, conn, lat=None, lng=None)
    assert r.status_code == 400 and "No GPS" in r.json()["error"]


def test_upload_half_coordinates_and_out_of_range(client, conn, fake_detector):
    assert upload(client, conn, lng=None).status_code == 400
    assert upload(client, conn, lat=95).status_code == 400


def test_upload_unknown_road(client, conn, fake_detector):
    assert upload(client, conn, road_id=999999).status_code == 400


def test_upload_detection_failure_is_422(client, conn, monkeypatch):
    def boom(img, min_conf):
        raise RuntimeError("model crashed")
    monkeypatch.setattr(detector, "detect", boom)
    r = upload(client, conn)
    assert r.status_code == 422 and r.json() == {"error": "Detection failed, try again"}


def test_upload_uses_exif_gps(client, conn, fake_detector):
    from app.services import gps
    img = Image.new("RGB", (640, 480))
    exif = img.getexif()
    exif.get_ifd(gps.GPS_IFD).update({1: "N", 2: (12.0, 58.0, 0.0), 3: "E", 4: (77.0, 35.0, 0.0)})
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    body = upload(client, conn, data=buf.getvalue(), lat=None, lng=None).json()
    assert body["gps_source"] == "exif" and body["lat"] == pytest.approx(12.9667, abs=1e-3)


def test_large_image_is_shrunk(client, conn, fake_detector):
    body = upload(client, conn, data=jpeg((5000, 2500))).json()
    assert (body["image_width"], body["image_height"]) == (4000, 2000)


# ---------- roads and config ----------

def test_road_edit_rescores(client, conn, fake_detector):
    pid = upload(client, conn).json()["potholes"][0]["pothole_id"]
    before = potholes.get(conn, pid)["priority_score"]
    r = client.put(f"/api/roads/{road_id(conn)}", json={"traffic_score": 0.1, "importance_score": 1.0})
    assert r.status_code == 200
    assert potholes.get(conn, pid)["priority_score"] == pytest.approx(before - 0.8 * 0.20)


def test_config_rejects_bad_weights(client):
    r = client.put("/api/config", json={"values": {"W_SEVERITY": 0.9}})
    assert r.status_code == 400 and "sum to 1.0" in r.json()["error"]
    assert client.put("/api/config", json={"values": {"NOPE": 1}}).status_code == 400
    ok = client.put("/api/config", json={"values": {"W_SEVERITY": 0.30, "W_REPEAT": 0.20}})
    assert ok.status_code == 200 and ok.json()["W_REPEAT"] == 0.20


# ---------- real model on real photos (skipped without weights) ----------

needs_model = pytest.mark.skipif(not (Path(detector.BACKEND_DIR) / get_settings().model_path).exists(),
                                 reason="run scripts/download_model.py")


@needs_model
def test_real_model_finds_pothole_and_ignores_clean_road(client, conn):
    hit = upload(client, conn, data=(SAMPLES / "pothole_06.jpg").read_bytes())
    assert hit.status_code == 200 and len(hit.json()["potholes"]) >= 1
    clean = upload(client, conn, data=(SAMPLES / "clean_01.jpg").read_bytes())
    assert clean.status_code == 200 and clean.json()["potholes"] == []


# ---------- location factor: critical facilities ----------

def add_hospital(conn, lat, lng):
    from app.repositories import facilities
    facilities.upsert_many(conn, [{"osm_id": f"node/test-{lat}-{lng}", "name": "Test Hospital",
                                   "kind": "hospital", "lat": lat, "lng": lng}])


def test_upload_near_hospital_scores_facility(client, conn, fake_detector):
    add_hospital(conn, 47.0, 12.0 + 100 / 75_900)  # ~100 m east (1 degree of longitude ~ 75.9 km at 47 N)
    p = upload(client, conn).json()["potholes"][0]
    stored = potholes.get(conn, p["pothole_id"])
    assert stored["nearest_facility"] == "Test Hospital (hospital)"
    assert stored["nearest_facility_m"] == pytest.approx(100, abs=2)
    assert stored["facility_score"] == pytest.approx(math.exp(-100 / 500), abs=0.01)
    detail = client.get(f"/api/potholes/{p['pothole_id']}").json()
    assert detail["breakdown"]["facility"]["contribution"] == pytest.approx(0.15 * stored["facility_score"])


def test_facility_import_rescores_existing_potholes(client, conn, fake_detector):
    from app.services import priority
    p = upload(client, conn).json()["potholes"][0]
    add_hospital(conn, 47.0, 12.0)
    priority.rescore_all(conn, refresh_facilities=True)
    stored = potholes.get(conn, p["pothole_id"])
    assert stored["facility_score"] == pytest.approx(1.0)
    assert stored["priority_score"] == pytest.approx(p["priority_score"] + 0.15)
