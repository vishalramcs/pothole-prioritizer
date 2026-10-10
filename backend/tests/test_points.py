"""Citizen reward points: the rules, and that an upload never fails because of points or email."""
import io
import smtplib

from PIL import Image
from sqlalchemy import text

from app.core.config import get_settings
from app.repositories import points as ledger
from app.services import detector
from tests.test_api_core import fake_detector, upload  # noqa: F401  (fixture used by name)


def jpeg_taken(when: str) -> bytes:
    img = Image.new("RGB", (640, 480), (90, 90, 90))
    exif = Image.Exif()
    exif[0x0132] = when  # EXIF DateTime
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def test_new_pothole_then_same_again_then_someone_else(api, conn, fake_detector):  # noqa: F811
    asha = api("citizen")
    first = upload(asha, conn).json()["points"]
    assert (first["earned"], first["total"], first["stored"]) == (10, 10, True)
    again = upload(asha, conn).json()["points"]  # same photo, same place: same potholes
    assert again["earned"] == 0 and "already" in again["reason"] and again["total"] == 10
    other = upload(api("citizen"), conn).json()["points"]  # another citizen confirms them
    assert (other["earned"], other["total"]) == (2, 2)


def test_no_pothole_earns_nothing(api, conn, monkeypatch):
    monkeypatch.setattr(detector, "detect", lambda img, c: [])
    p = upload(api("citizen"), conn).json()["points"]
    assert (p["earned"], p["reason"]) == (0, "No pothole detected")


def test_officials_get_no_points(client, conn, fake_detector):  # noqa: F811
    assert upload(client, conn).json()["points"] is None


def test_daily_cap(api, conn, fake_detector):  # noqa: F811
    c = api("citizen")
    uid = c.get("/api/auth/me").json()["user_id"]
    ledger.insert(conn, uid, "x@test.example", None, None, 46, "earlier today")
    p = upload(c, conn).json()["points"]
    assert p["earned"] == 4 and "daily limit" in p["reason"] and p["total"] == 50
    conn.execute(text("UPDATE points_ledger SET points = 50 WHERE user_id = :u AND reason = 'earlier today'"), {"u": uid})
    p = upload(c, conn, lat=47.5).json()["points"]  # a different place: new potholes, but no points left today
    assert p["earned"] == 0 and p["reason"].startswith("Daily limit")


def test_old_photo_earns_nothing_but_is_still_saved(api, conn, fake_detector):  # noqa: F811
    r = upload(api("citizen"), conn, data=jpeg_taken("2020:01:01 10:00:00"))
    assert r.status_code == 200 and len(r.json()["potholes"]) == 2
    assert r.json()["points"]["earned"] == 0 and "older than 7 days" in r.json()["points"]["reason"]


def test_ledger_failure_still_shows_points(api, conn, fake_detector, monkeypatch):  # noqa: F811
    def broken(*a, **k):
        raise RuntimeError("ledger down")
    monkeypatch.setattr(ledger, "insert", broken)
    r = upload(api("citizen"), conn)
    assert r.status_code == 200 and len(r.json()["potholes"]) == 2  # the upload itself is kept
    assert r.json()["points"] == {**r.json()["points"], "earned": 10, "total": None, "stored": False}


def test_email_not_configured_says_so(api, conn, fake_detector, monkeypatch):  # noqa: F811
    monkeypatch.setattr(get_settings(), "smtp_host", "")
    assert upload(api("citizen"), conn).json()["points"]["email"]["status"] == "not_configured"


def test_failing_smtp_does_not_break_the_upload(api, conn, fake_detector, monkeypatch):  # noqa: F811
    monkeypatch.setattr(get_settings(), "smtp_host", "smtp.invalid")
    monkeypatch.setattr(get_settings(), "mail_from", "srpps@test.example")

    def refuse(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(smtplib, "SMTP", refuse)
    r = upload(api("citizen"), conn)  # the background send runs and fails inside this call
    assert r.status_code == 200 and r.json()["points"]["earned"] == 10
    assert r.json()["points"]["email"]["status"] == "sending"  # queued, never claimed as sent
