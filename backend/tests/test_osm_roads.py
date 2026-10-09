"""Real roads from OpenStreetMap at upload time, and the wider list of important buildings."""
import pytest

from app.services import detector, facilities, osm_roads
from tests.test_api_core import jpeg

LAT, LNG = 48.0, 13.0  # away from any real data


def way(way_id, highway, lat_offset_m, name=None, lanes=None, length_deg=0.002):
    """A straight east-west road lat_offset_m metres north of (LAT, LNG)."""
    lat = LAT + lat_offset_m / 110_540
    tags = {"highway": highway, **({"name": name} if name else {}), **({"lanes": str(lanes)} if lanes else {})}
    return {"type": "way", "id": way_id, "tags": tags,
            "geometry": [{"lat": lat, "lon": LNG - length_deg}, {"lat": lat, "lon": LNG + length_deg}]}


def test_road_values_by_class_and_lanes():
    assert osm_roads.road_values("trunk", None) == {"road_type": "highway", "importance_score": 1.0, "traffic_score": 0.9}
    assert osm_roads.road_values("primary_link", None)["road_type"] == "arterial"  # links count as their road
    assert osm_roads.road_values("residential", None)["traffic_score"] == 0.2
    assert osm_roads.road_values("secondary", 4)["traffic_score"] == pytest.approx(0.7)  # 0.6 + 2 extra lanes
    assert osm_roads.road_values("motorway", 8)["traffic_score"] == 1.0  # capped


def test_nearest_way_picks_closest_within_range():
    ways = [way(1, "primary", 40), way(2, "residential", 8), way(3, "trunk", 200)]
    assert osm_roads.nearest_way(ways, LAT, LNG)["id"] == 2
    assert osm_roads.nearest_way([way(3, "trunk", 200)], LAT, LNG) is None  # beyond SEARCH_M


def test_main_road_beats_a_slightly_closer_driveway():
    # GPS error: a service road 3 m away vs the main road 9 m away -> the main road
    assert osm_roads.nearest_way([way(1, "service", 3), way(2, "primary", 9)], LAT, LNG)["id"] == 2
    # but a main road far beyond the tie distance does not override a much closer street
    assert osm_roads.nearest_way([way(1, "residential", 3), way(2, "primary", 30)], LAT, LNG)["id"] == 1


@pytest.fixture
def one_box(monkeypatch, tmp_path):
    monkeypatch.setattr(osm_roads, "CACHE", tmp_path)  # never read or write the real tile cache in tests
    monkeypatch.setattr(osm_roads.time, "sleep", lambda s: None)
    monkeypatch.setattr(detector, "detect", lambda img, c: [{"bbox_x": 0, "bbox_y": 0, "bbox_w": 100, "bbox_h": 100,
                                                             "confidence": 0.9}])


def upload_without_road(client):
    return client.post("/api/uploads", data={"lat": LAT, "lng": LNG}, files={"file": ("p.jpg", jpeg(), "image/jpeg")})


def test_upload_finds_the_real_road(client, conn, monkeypatch, one_box):
    monkeypatch.setattr(osm_roads, "fetch_ways", lambda *box: [way(777, "secondary", 5, name="MG Road", lanes=4)])
    r = upload_without_road(client)
    assert r.status_code == 200, r.json()
    p = client.get(f"/api/potholes/{r.json()['potholes'][0]['pothole_id']}").json()
    assert p["road_name"] == "MG Road" and p["road_type"] == "arterial" and p["road_data_source"] == "osm_estimate"
    assert p["traffic_score"] == pytest.approx(0.7) and p["importance_score"] == 0.7
    again = upload_without_road(client).json()["potholes"][0]
    assert again["road_id"] == p["road_id"]  # the same OSM way is reused, not duplicated


def test_upload_without_road_when_osm_is_down(client, monkeypatch, one_box):
    def down(*box):
        raise osm_roads.RoadLookupError("OpenStreetMap could not be reached")
    monkeypatch.setattr(osm_roads, "fetch_ways", down)
    r = upload_without_road(client)
    assert r.status_code == 400 and "Pick the road from the list" in r.json()["error"]


def test_upload_without_road_far_from_any_road(client, monkeypatch, one_box):
    monkeypatch.setattr(osm_roads, "fetch_ways", lambda *box: [way(9, "primary", 500)])
    r = upload_without_road(client)
    assert r.status_code == 400 and "No mapped road" in r.json()["error"]


def test_important_buildings_include_transport_police_colleges():
    data = {"elements": [
        {"type": "node", "id": 1, "lat": 1, "lon": 1, "tags": {"railway": "station", "name": "City Junction"}},
        {"type": "node", "id": 2, "lat": 1, "lon": 1, "tags": {"amenity": "police"}},
        {"type": "way", "id": 3, "center": {"lat": 1, "lon": 1}, "tags": {"amenity": "university"}},
        {"type": "node", "id": 4, "lat": 1, "lon": 1, "tags": {"amenity": "bus_station"}},
        {"type": "node", "id": 5, "lat": 1, "lon": 1, "tags": {"railway": "halt"}},  # not a station
    ]}
    assert [r["kind"] for r in facilities.parse_overpass(data)] == ["railway_station", "police", "university", "bus_station"]


def test_tile_cache_makes_repeat_lookups_offline(client, monkeypatch, one_box):
    monkeypatch.setattr(osm_roads, "fetch_ways", lambda *box: [way(5, "primary", 5, name="Cached Road")])
    assert upload_without_road(client).status_code == 200

    def down(*box):
        raise osm_roads.RoadLookupError("OpenStreetMap could not be reached")
    monkeypatch.setattr(osm_roads, "fetch_ways", down)
    r = upload_without_road(client)  # same tile: answered from the cache
    assert r.status_code == 200 and r.json()["potholes"][0]["road_id"] is not None
