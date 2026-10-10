"""Logins and what each role may do: citizens report potholes, officials use everything."""
import pytest

from app.services import auth
from tests.test_api_core import fake_detector, upload  # noqa: F401  (fixture used by name)

OFFICIAL_ONLY = [
    ("get", "/api/potholes"), ("get", "/api/zones"), ("get", "/api/crews"), ("get", "/api/repairs"),
    ("get", "/api/analytics/summary"), ("get", "/api/config"), ("get", "/api/evaluation"),
    ("post", "/api/plan"), ("post", "/api/zones/recompute"), ("put", "/api/roads/1"),
]


def test_password_hash_round_trip():
    h = auth.hash_password("correct horse")
    assert h.startswith("scrypt$") and "correct horse" not in h
    assert auth.check_password("correct horse", h) and not auth.check_password("wrong", h)
    assert not auth.check_password("x", "not-a-hash")


def test_citizen_signs_up_logs_out_and_back_in(api):
    c = api()
    r = c.post("/api/auth/register", json={"name": "Asha", "email": "Asha@Example.com", "password": "pothole-1"})
    assert r.status_code == 200 and r.json()["role"] == "citizen" and r.json()["email"] == "asha@example.com"
    assert "password_hash" not in r.json()
    assert c.get("/api/auth/me").json()["name"] == "Asha"
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401  # the session is gone, not just the cookie
    r = c.post("/api/auth/login", json={"email": "asha@example.com", "password": "pothole-1", "role": "citizen"})
    assert r.status_code == 200 and c.get("/api/auth/me").status_code == 200


def test_signup_is_citizens_only_and_rejects_duplicates(api):
    c = api()
    body = {"name": "A", "email": "a@example.com", "password": "pothole-1", "role": "official"}
    assert c.post("/api/auth/register", json=body).json()["role"] == "citizen"  # a role field is ignored
    assert c.post("/api/auth/register", json=body).status_code == 409
    assert c.post("/api/auth/register", json={**body, "email": "b@example.com", "password": "short"}).status_code == 400


def test_login_failures(api, conn):
    auth.create_user(conn, "off@example.com", "Officer", "pothole-1", "official")
    c = api()
    wrong = c.post("/api/auth/login", json={"email": "off@example.com", "password": "nope-nope", "role": "official"})
    unknown = c.post("/api/auth/login", json={"email": "who@example.com", "password": "nope-nope", "role": "official"})
    assert wrong.status_code == unknown.status_code == 401 and wrong.json() == unknown.json()  # no account probing
    as_citizen = c.post("/api/auth/login", json={"email": "off@example.com", "password": "pothole-1", "role": "citizen"})
    assert as_citizen.status_code == 403 and "Official" in as_citizen.json()["error"]


@pytest.mark.parametrize("method,path", OFFICIAL_ONLY)
def test_official_endpoints_are_closed_to_others(api, method, path):
    assert getattr(api(), method)(path).status_code == 401
    assert getattr(api("citizen"), method)(path).status_code == 403


def test_logged_out_cannot_upload(api, conn):
    assert upload(api(), conn).status_code == 401


def test_citizen_reports_with_a_description_and_officials_read_it(api, client, conn, fake_detector):  # noqa: F811
    citizen = api("citizen")
    r = upload(citizen, conn, description="  Deep one near the bus stop, two bikes fell  ")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert citizen.get(f"/api/uploads/{body['upload_id']}/image").status_code == 200  # their own photo
    assert api("citizen").get(f"/api/uploads/{body['upload_id']}/image").status_code == 404  # not someone else's
    detail = client.get(f"/api/potholes/{body['potholes'][0]['pothole_id']}").json()
    assert detail["description"] == "Deep one near the bus stop, two bikes fell" and detail["reporter_role"] == "citizen"


def test_description_is_limited(api, conn, fake_detector):  # noqa: F811
    assert upload(api("citizen"), conn, description="x" * 1001).status_code == 400
