"""Video upload, P2 (TRD 4.8): frame sampling, IoU merge across consecutive frames, stored frames."""
import os
import tempfile

import cv2
import numpy as np
import pytest

from app.repositories import potholes
from app.services import detector, video
from tests.test_api_core import road_id


def b(x, y, w=100, h=100, conf=0.8):
    return {"bbox_x": x, "bbox_y": y, "bbox_w": w, "bbox_h": h, "confidence": conf}


def test_iou():
    assert video.iou(b(0, 0), b(0, 0)) == 1.0
    assert video.iou(b(0, 0), b(200, 200)) == 0.0
    assert video.iou(b(0, 0), b(50, 0)) == pytest.approx(50 * 100 / (2 * 10_000 - 50 * 100))


def test_same_pothole_across_frames_merges_keeping_best_confidence():
    frames = [[b(0, 0, conf=0.5)], [b(10, 5, conf=0.9)], [b(20, 10, conf=0.6), b(400, 400)]]
    kept = video.merge_tracks(frames, iou_min=0.3)
    assert len(kept) == 2
    assert max(k["confidence"] for k in kept) == 0.9


def test_low_overlap_is_a_different_pothole():
    assert len(video.merge_tracks([[b(0, 0)], [b(80, 80)]], iou_min=0.3)) == 2


def test_two_boxes_in_one_frame_never_merge():
    assert len(video.merge_tracks([[b(0, 0), b(5, 5)]], iou_min=0.3)) == 2


def clip(frames=4, fps=1) -> bytes:
    path = os.path.join(tempfile.mkdtemp(), "c.mp4")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))
    for i in range(frames):
        w.write(np.full((240, 320, 3), 40 + i * 30, np.uint8))
    w.release()
    with open(path, "rb") as f:
        return f.read()


def send_video(client, conn, data, **form):
    form = {"road_id": road_id(conn), "lat": 46.0, "lng": 11.0, **form}
    form = {k: v for k, v in form.items() if v is not None}
    return client.post("/api/uploads", data=form, files={"file": ("ride.mp4", data, "video/mp4")})


def test_video_upload_merges_and_stores_frames(client, conn, monkeypatch):
    calls = iter([[b(10, 10, conf=0.5)], [b(14, 12, conf=0.9)], [], [b(200, 100, w=60, h=60)]])
    monkeypatch.setattr(detector, "detect", lambda img, c: next(calls))
    r = send_video(client, conn, clip(frames=4, fps=1))
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["media_type"] == "video" and body["frames_sampled"] == 4
    assert len(body["potholes"]) == 2
    first = min(body["potholes"], key=lambda p: p["frame_index"])
    assert first["confidence"] == 0.9 and first["frame_index"] == 1
    stored = potholes.get(conn, first["pothole_id"])
    assert stored["frame_time_s"] == pytest.approx(1.0) and stored["frame_storage_path"].endswith("frame_1.jpg")
    assert client.get(f"/api/uploads/{body['upload_id']}/frames/1").status_code == 200
    assert client.get(f"/api/uploads/{body['upload_id']}/frames/2").status_code == 404  # no pothole in it
    assert client.get(f"/api/potholes/{first['pothole_id']}/image").status_code == 200
    assert client.get(f"/api/uploads/{body['upload_id']}/image").status_code == 404


def test_video_needs_coordinates(client, conn):
    r = send_video(client, conn, clip(), lat=None, lng=None)
    assert r.status_code == 400 and "location" in r.json()["error"]


def test_not_a_video(client, conn):
    r = send_video(client, conn, b"definitely not a video")
    assert r.status_code == 400 and "video" in r.json()["error"]
