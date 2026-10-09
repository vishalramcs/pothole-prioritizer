"""area_ratio -> severity_score -> level, using config values (TRD 4.2).

A relative 2D estimate: a pothole closer to the camera looks bigger. It is not depth.
"""


def area_ratio(bbox_w: float, bbox_h: float, image_w: int, image_h: int) -> float:
    return min((bbox_w * bbox_h) / (image_w * image_h), 1.0)


def severity(ratio: float, cfg: dict[str, float]) -> tuple[float, str]:
    """Returns (severity_score 0..1, level Low/Medium/High)."""
    score = min(ratio / cfg["AREA_RATIO_MAX"], 1.0)
    if score < cfg["SEV_MEDIUM_MIN"]:
        return score, "Low"
    if score < cfg["SEV_HIGH_MIN"]:
        return score, "Medium"
    return score, "High"
