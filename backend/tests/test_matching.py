"""TRD 4.4 duplicate / repeat matching, through the upload API. Each test is rolled back."""
import pytest

from app.repositories import potholes
from app.services import detector
from tests.test_api_core import jpeg, road_id

LAT, LNG = 45.0, 10.0  # nowhere near any real data in the dev database
METERS_20 = 20 / 111_320


def box(w, h):
    return {"bbox_x": 0, "bbox_y": 0, "bbox_w": w, "bbox_h": h, "confidence": 0.9}


@pytest.fixture
def send(client, conn, monkeypatch):
    """send([boxes], lat=...) uploads a 640x480 photo whose detector returns exactly those boxes."""
    def _send(boxes, lat=LAT, lng=LNG):
        monkeypatch.setattr(detector, "detect", lambda img, c: [dict(b) for b in boxes])
        r = client.post("/api/uploads", data={"road_id": road_id(conn), "lat": lat, "lng": lng},
                        files={"file": ("p.jpg", jpeg(), "image/jpeg")})
        assert r.status_code == 200, r.json()
        return r.json()["potholes"]
    return _send


def test_several_potholes_in_one_photo_stay_separate(send):
    out = send([box(100, 100), box(100, 100), box(50, 50)])
    assert [p["match"] for p in out] == ["new"] * 3
    assert len({p["pothole_id"] for p in out}) == 3


def test_same_spot_twice_merges_one_to_one(send, conn):
    first = send([box(200, 100), box(100, 50)])
    second = send([box(200, 100), box(100, 50), box(60, 40)])
    assert [p["match"] for p in second] == ["repeat", "repeat", "new"]
    # highest severity pairs with highest severity
    assert second[0]["pothole_id"] == first[0]["pothole_id"]
    assert second[1]["pothole_id"] == first[1]["pothole_id"]
    for p in first:
        assert potholes.get(conn, p["pothole_id"])["detection_count"] == 2


def test_repeat_raises_priority(send, conn):
    p = send([box(100, 100)])[0]
    again = send([box(100, 100)])[0]
    assert again["pothole_id"] == p["pothole_id"]
    assert again["priority_score"] == pytest.approx(p["priority_score"] + 0.10 / 3)  # repeat 1/3 x W_REPEAT


def test_more_severe_sighting_replaces_evidence(send, conn):
    p = send([box(50, 50)])[0]
    bigger = send([box(300, 200)])[0]
    stored = potholes.get(conn, p["pothole_id"])
    assert stored["upload_id"] == bigger["upload_id"] != p["upload_id"]
    assert stored["severity_score"] > p["severity_score"]
    send([box(10, 10)])  # a smaller sighting later must not lower it
    assert potholes.get(conn, p["pothole_id"])["severity_score"] == stored["severity_score"]


def test_after_repair_creates_new_record_with_recurrence(client, send, conn):
    old = send([box(100, 100)])[0]
    client.patch(f"/api/potholes/{old['pothole_id']}/status", json={"status": "Repaired"})
    back = send([box(100, 100)])[0]
    assert back["match"] == "recurrence" and back["pothole_id"] != old["pothole_id"]
    assert potholes.get(conn, back["pothole_id"])["recurrence_count"] == 1
    # and if that one is repaired and it returns again, the count keeps climbing
    client.patch(f"/api/potholes/{back['pothole_id']}/status", json={"status": "Repaired"})
    third = send([box(100, 100)])[0]
    assert potholes.get(conn, third["pothole_id"])["recurrence_count"] == 2


def test_uploads_20m_apart_do_not_merge(send):
    send([box(100, 100)])
    assert send([box(100, 100)], lat=LAT + METERS_20)[0]["match"] == "new"
