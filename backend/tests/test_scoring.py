import io

import pytest
from PIL import Image

from app.services import facilities, geo, gps, priority, severity

# Seed defaults from supabase/seed.sql
CFG = {
    "W_SEVERITY": 0.40, "W_TRAFFIC": 0.20, "W_IMPORTANCE": 0.15, "W_REPEAT": 0.10, "W_FACILITY": 0.15,
    "AREA_RATIO_MAX": 0.10, "SEV_MEDIUM_MIN": 0.30, "SEV_HIGH_MIN": 0.60,
    "BAND_CRITICAL": 0.70, "BAND_MODERATE": 0.40, "REPEAT_CAP": 3, "SAFETY_FLOOR_SEVERITY": 0,
}


@pytest.mark.parametrize("ratio,score,level", [
    (0.0, 0.0, "Low"), (0.02, 0.2, "Low"), (0.03, 0.3, "Medium"), (0.059, 0.59, "Medium"),
    (0.06, 0.6, "High"), (0.5, 1.0, "High"),
])
def test_severity_levels(ratio, score, level):
    s, lvl = severity.severity(ratio, CFG)
    assert s == pytest.approx(score) and lvl == level


def test_area_ratio_capped_at_one():
    assert severity.area_ratio(100, 50, 1000, 500) == pytest.approx(0.01)
    assert severity.area_ratio(2000, 2000, 1000, 1000) == 1.0


def test_weights_must_sum_to_one():
    priority.check_weights(CFG)
    with pytest.raises(ValueError):
        priority.check_weights({**CFG, "W_REPEAT": 0.20})


@pytest.mark.parametrize("traffic,importance,no_facility,next_to_facility", [
    (0.90, 1.0, 0.83, 0.98), (0.70, 0.8, 0.76, 0.91), (0.60, 0.5, 0.695, 0.845), (0.20, 0.3, 0.585, 0.735),
])
def test_score_ceilings_match_trd_table(traffic, importance, no_facility, next_to_facility):
    """TRD 4.5 table: max score per seeded road with severity 1 and repeat 1, far from / next to a facility."""
    assert priority.priority(1.0, traffic, importance, 1.0, 0.0, CFG)["priority_score"] == pytest.approx(no_facility)
    assert priority.priority(1.0, traffic, importance, 1.0, 1.0, CFG)["priority_score"] == pytest.approx(next_to_facility)


def test_local_road_reaches_critical_only_next_to_a_facility():
    assert priority.priority(1.0, 0.20, 0.3, 1.0, 0.0, CFG)["priority_band"] == "Moderate"
    assert priority.priority(1.0, 0.20, 0.3, 1.0, 1.0, CFG)["priority_band"] == "Critical"


def test_severe_highway_pothole_is_critical():
    assert priority.priority(1.0, 0.90, 1.0, 0.0, 0.0, CFG)["priority_band"] == "Critical"


def test_medium_pothole_next_to_hospital_outranks_small_highway_pothole():
    near_hospital = priority.priority(0.5, 0.20, 0.3, 0.0, 1.0, CFG)["priority_score"]
    small_highway = priority.priority(0.2, 0.90, 1.0, 0.0, 0.0, CFG)["priority_score"]
    assert near_hospital > small_highway


def test_severe_highway_outranks_severe_residential():
    highway = priority.priority(0.9, 0.90, 1.0, 0.0, 0.0, CFG)["priority_score"]
    residential = priority.priority(0.9, 0.20, 0.3, 0.0, 0.0, CFG)["priority_score"]
    assert highway > residential


def test_safety_override_forces_critical_but_keeps_score():
    p = priority.priority(0.95, 0.20, 0.3, 0.0, 0.0, {**CFG, "SAFETY_FLOOR_SEVERITY": 0.90})
    assert p["priority_band"] == "Critical" and p["safety_override"]
    assert p["priority_score"] == pytest.approx(0.95 * 0.40 + 0.2 * 0.20 + 0.3 * 0.15)


def test_same_severity_different_road_gives_different_priority():
    busy = priority.priority(0.5, 0.90, 1.0, 0, 0, CFG)["priority_score"]
    quiet = priority.priority(0.5, 0.20, 0.3, 0, 0, CFG)["priority_score"]
    assert busy > quiet


def test_repeat_score():
    assert priority.repeat_score(1, 0, CFG) == 0
    assert priority.repeat_score(2, 1, CFG) == pytest.approx(2 / 3)
    assert priority.repeat_score(5, 2, CFG) == 1.0


def test_breakdown_contributions_add_up():
    p = priority.priority(0.5, 0.6, 0.5, 1 / 3, 0.4, CFG)
    assert sum(b["contribution"] for b in p["breakdown"].values()) == pytest.approx(p["priority_score"])


def test_haversine_known_distance():
    # 0.001 degrees of latitude is about 111 m
    assert geo.distance_m(12.0, 77.0, 12.001, 77.0) == pytest.approx(111.2, abs=0.5)


def _jpeg_with_gps(lat_ref, lat, lng_ref, lng) -> Image.Image:
    img = Image.new("RGB", (10, 10))
    exif = img.getexif()
    exif.get_ifd(gps.GPS_IFD).update({1: lat_ref, 2: lat, 3: lng_ref, 4: lng})
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return Image.open(io.BytesIO(buf.getvalue()))


def test_exif_gps_read_with_hemispheres():
    img = _jpeg_with_gps("S", (33.0, 52.0, 4.0), "W", (151.0, 12.0, 36.0))
    lat, lng = gps.exif_gps(img)
    assert lat == pytest.approx(-33.8678, abs=1e-4) and lng == pytest.approx(-151.21, abs=1e-4)


def test_no_exif_gps_returns_none():
    assert gps.exif_gps(Image.new("RGB", (10, 10))) is None
    assert gps.exif_gps(_jpeg_with_gps("N", (0.0, 0.0, 0.0), "E", (0.0, 0.0, 0.0))) is None


def test_parse_overpass_nodes_and_ways():
    data = {"elements": [
        {"type": "node", "id": 1, "lat": 12.9, "lon": 77.6, "tags": {"amenity": "hospital", "name": "City Hospital"}},
        {"type": "way", "id": 2, "center": {"lat": 12.8, "lon": 77.5}, "tags": {"amenity": "school"}},
        {"type": "node", "id": 3, "lat": 12.7, "lon": 77.4, "tags": {"amenity": "cafe"}},  # not a critical facility
        {"type": "way", "id": 4, "tags": {"amenity": "clinic"}},  # no position
    ]}
    rows = facilities.parse_overpass(data)
    assert [r["osm_id"] for r in rows] == ["node/1", "way/2"]
    assert rows[1] == {"osm_id": "way/2", "name": None, "kind": "school", "lat": 12.8, "lng": 77.5}
