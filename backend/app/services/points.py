"""Reward points for citizens who report potholes. Optional extra: an upload must never fail because of it.

Per upload (not per pothole, so one photo of many potholes is not a jackpot):
  +10 if it found a pothole not on record before (or one that came back after repair),
  +2  if it only confirmed potholes already on record,
  0   if nothing was detected, every pothole in it already earned this user points, the photo's EXIF
      time is older than 7 days, or the daily limit of 50 points is used up.
The total is the sum of the user's ledger rows. If the database part fails, the points are still worked out
from the detection for display, without a total (award() never raises).
"""
import io
import logging
from datetime import datetime, timedelta

from PIL import Image
from sqlalchemy import Connection

from app.repositories import points as ledger

log = logging.getLogger(__name__)

NEW, REPEAT = 10, 2
DAILY_CAP = 50
MAX_PHOTO_AGE_DAYS = 7
_EXIF_IFD, _DATETIME_ORIGINAL, _DATETIME = 0x8769, 0x9003, 0x0132


def photo_taken_at(data: bytes) -> datetime | None:
    """When the photo was taken, from EXIF (camera local time), or None if it has no usable time."""
    try:
        exif = Image.open(io.BytesIO(data)).getexif()
        raw = exif.get_ifd(_EXIF_IFD).get(_DATETIME_ORIGINAL) or exif.get(_DATETIME)
        return datetime.strptime(str(raw).strip("\x00 "), "%Y:%m:%d %H:%M:%S") if raw else None
    except Exception:
        return None


def base_award(potholes: list[dict], too_old: bool) -> tuple[int, str, int | None]:
    """(points, reason, pothole the points are for) from the detection alone."""
    if not potholes:
        return 0, "No pothole detected", None
    if too_old:
        return 0, f"Photo is older than {MAX_PHOTO_AGE_DAYS} days", None
    new = [p for p in potholes if p.get("match") in ("new", "recurrence")]
    if new:
        return NEW, "New pothole reported", new[0]["pothole_id"]
    return REPEAT, "Confirmed a pothole already on record", potholes[0]["pothole_id"]


def award(conn: Connection, user: dict, result: dict, data: bytes | None) -> dict | None:
    """Points for this upload, or None for officials (points are for public reporters). Never raises."""
    if user.get("role") != "citizen":
        return None
    try:
        potholes = result.get("potholes") or []
        taken = photo_taken_at(data) if data is not None and result.get("media_type") != "video" else None
        too_old = taken is not None and datetime.now() - taken > timedelta(days=MAX_PHOTO_AGE_DAYS)
        earned, reason, pothole_id = base_award(potholes, too_old)
    except Exception:
        log.exception("points: could not work out points")
        return None
    try:
        with conn.begin_nested():  # a failure here must not undo the upload itself
            if earned:
                done = ledger.rewarded_potholes(conn, user["user_id"], [p["pothole_id"] for p in potholes])
                fresh = [p for p in potholes if p["pothole_id"] not in done]
                if not fresh:
                    earned, reason, pothole_id = 0, "You already earned points for this pothole", None
                else:
                    earned, reason, pothole_id = base_award(fresh, too_old)
                    left = max(DAILY_CAP - ledger.earned_today(conn, user["user_id"]), 0)
                    if earned > left:
                        earned = left
                        reason = f"Daily limit of {DAILY_CAP} points reached" if left == 0 else reason + " (daily limit reached)"
            ledger.insert(conn, user["user_id"], user["email"], result["upload_id"],
                          pothole_id if earned else None, earned, reason)
            if earned:  # the other potholes in this report are covered too, so re-uploading it earns nothing
                for p in fresh:
                    if p["pothole_id"] != pothole_id:
                        ledger.insert(conn, user["user_id"], user["email"], result["upload_id"], p["pothole_id"], 0,
                                      "Included in the same report")
            total = ledger.total(conn, user["user_id"])
        return {"earned": earned, "reason": reason, "total": total, "stored": True}
    except Exception:
        log.exception("points: ledger unavailable, showing points without a total")
        return {"earned": earned, "reason": reason, "total": None, "stored": False}
