"""Weighted priority score, band, optional safety override (TRD 4.5)."""

WEIGHTS = ("W_SEVERITY", "W_TRAFFIC", "W_IMPORTANCE", "W_REPEAT")


def check_weights(cfg: dict[str, float]) -> None:
    """Raise ValueError unless the four weights sum to 1.0 (tolerance 0.001)."""
    total = sum(cfg[w] for w in WEIGHTS)
    if abs(total - 1.0) > 0.001:
        raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")


def repeat_score(detection_count: int, recurrence_count: int, cfg: dict[str, float]) -> float:
    return min(((detection_count - 1) + recurrence_count) / cfg["REPEAT_CAP"], 1.0)


def priority(severity_score: float, traffic: float, importance: float, repeat: float,
             cfg: dict[str, float]) -> dict:
    """Score, band, safety override flag, and the per-factor breakdown shown in the detail panel."""
    parts = {
        "severity": (severity_score, cfg["W_SEVERITY"]),
        "traffic": (traffic, cfg["W_TRAFFIC"]),
        "importance": (importance, cfg["W_IMPORTANCE"]),
        "repeat": (repeat, cfg["W_REPEAT"]),
    }
    score = min(sum(v * w for v, w in parts.values()), 1.0)  # min(): float rounding can give 1.0000000002
    band = "Critical" if score >= cfg["BAND_CRITICAL"] else "Moderate" if score >= cfg["BAND_MODERATE"] else "Low"
    floor = cfg["SAFETY_FLOOR_SEVERITY"]
    override = floor > 0 and severity_score >= floor and band != "Critical"
    return {
        "priority_score": score,
        "priority_band": "Critical" if override else band,
        "safety_override": override,
        "breakdown": {k: {"value": v, "weight": w, "contribution": v * w} for k, (v, w) in parts.items()},
    }
