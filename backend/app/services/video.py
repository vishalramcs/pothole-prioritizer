"""Frame sampling and box-overlap merge, P2 (TRD 4.8).

One frame every FRAME_INTERVAL_S. The same pothole shows up in consecutive sampled frames, so a detection
whose box overlaps (IoU >= VIDEO_IOU_MIN) one in the previous sampled frame is the same pothole; each track
keeps its highest-confidence detection. Unreliable when the camera moves fast (boxes jump between frames).
"""
from collections.abc import Iterator

import cv2
from PIL import Image

MAX_SAMPLED_FRAMES = 120  # shortcut: caps CPU time (2 min of video at 1 s); raise it if you need longer clips


def iou(a: dict, b: dict) -> float:
    ax2, ay2 = a["bbox_x"] + a["bbox_w"], a["bbox_y"] + a["bbox_h"]
    bx2, by2 = b["bbox_x"] + b["bbox_w"], b["bbox_y"] + b["bbox_h"]
    iw = max(0.0, min(ax2, bx2) - max(a["bbox_x"], b["bbox_x"]))
    ih = max(0.0, min(ay2, by2) - max(a["bbox_y"], b["bbox_y"]))
    inter = iw * ih
    union = a["bbox_w"] * a["bbox_h"] + b["bbox_w"] * b["bbox_h"] - inter
    return inter / union if union > 0 else 0.0


def sample_frames(path: str, interval_s: float, max_side: int) -> Iterator[tuple[int, float, Image.Image]]:
    """(frame_index, time_s, RGB frame) every interval_s seconds. Raises ValueError if it isn't a readable video."""
    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            raise ValueError("not a video")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        step = max(1, round(fps * interval_s))
        index = sampled = 0
        while sampled < MAX_SAMPLED_FRAMES:
            ok, frame = cap.read()
            if not ok:
                break
            if index % step == 0:
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                img.thumbnail((max_side, max_side))
                yield index, index / fps, img
                sampled += 1
            index += 1
        if index == 0:
            raise ValueError("no frames")
    finally:
        cap.release()


def merge_tracks(frames: list[list[dict]], iou_min: float) -> list[dict]:
    """frames[k] = detections in the k-th sampled frame. Returns one detection per physical pothole."""
    finished, active = [], []  # a track is [best detection, last detection]
    for dets in frames:
        pairs = sorted(((iou(t[1], d), ti, di) for ti, t in enumerate(active) for di, d in enumerate(dets)),
                       reverse=True)
        used_t, used_d, nxt = set(), set(), []
        for score, ti, di in pairs:  # best overlaps first, each track and detection used once
            if score < iou_min or ti in used_t or di in used_d:
                continue
            used_t.add(ti)
            used_d.add(di)
            best, d = active[ti][0], dets[di]
            nxt.append([d if d["confidence"] > best["confidence"] else best, d])
        finished += [t for ti, t in enumerate(active) if ti not in used_t]  # not seen in this frame: track ends
        nxt += [[d, d] for di, d in enumerate(dets) if di not in used_d]
        active = nxt
    return [t[0] for t in finished + active]
