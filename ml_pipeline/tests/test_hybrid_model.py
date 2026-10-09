"""The plan's two required orderings, checked on the label formula AND on the trained model."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from build_real_dataset import add_priority

HERE = Path(__file__).resolve().parents[1]
CHECKPOINT = HERE / "models" / "hybrid_best.pt"

QUIET = {"is_junction": 0, "is_curve_or_bridge": 0, "past_accidents_nearby": 0, "rain_or_poor_lighting": 0,
         "complaint_count": 2, "days_unrepaired": 30, "dist_fire_station_m": 3000.0, "dist_bus_stop_m": 2000.0}
NEAR_HOSPITAL_RESIDENTIAL = {**QUIET, "road_class": "residential", "traffic_vehicles_per_day": 800, "speed_limit_kmph": 25,
                             "dist_hospital_m": 50.0, "dist_school_m": 2000.0, "critical_facilities_500m": 1}
HIGHWAY_NO_FACILITIES = {**QUIET, "road_class": "highway", "traffic_vehicles_per_day": 40000, "speed_limit_kmph": 80,
                         "dist_hospital_m": 20000.0, "dist_school_m": 20000.0, "critical_facilities_500m": 0}
RESIDENTIAL_NO_FACILITIES = {**NEAR_HOSPITAL_RESIDENTIAL, "dist_hospital_m": 20000.0, "critical_facilities_500m": 0}
SMALL, MEDIUM, SEVERE = 0.12, 0.50, 0.90


def label(context: dict, severity: float) -> float:
    return float(add_priority(pd.DataFrame([{**context, "severity": severity}])).priority_score[0])


def test_labels_medium_near_hospital_outrank_small_on_highway():
    assert label(NEAR_HOSPITAL_RESIDENTIAL, MEDIUM) > label(HIGHWAY_NO_FACILITIES, SMALL)


def test_labels_severe_highway_outranks_severe_residential():
    assert label(HIGHWAY_NO_FACILITIES, SEVERE) > label(RESIDENTIAL_NO_FACILITIES, SEVERE)


def image_closest_to(severity: float) -> str:
    sev = pd.read_csv(HERE / "cnn_severity.csv")
    return sev.iloc[int(np.argmin((sev.severity - severity).abs()))].image_file


needs_model = pytest.mark.skipif(not CHECKPOINT.exists(), reason="train first: python hybrid.py")


@needs_model
def test_model_medium_near_hospital_outranks_small_on_highway():
    from hybrid import load_model, score
    model, scaler = load_model()
    near = score(model, scaler, image_closest_to(MEDIUM), NEAR_HOSPITAL_RESIDENTIAL)[0]
    highway = score(model, scaler, image_closest_to(SMALL), HIGHWAY_NO_FACILITIES)[0]
    assert near > highway, (near, highway)


@needs_model
def test_model_severe_highway_outranks_severe_residential():
    from hybrid import load_model, score
    model, scaler = load_model()
    img = image_closest_to(SEVERE)
    assert score(model, scaler, img, HIGHWAY_NO_FACILITIES)[0] > score(model, scaler, img, RESIDENTIAL_NO_FACILITIES)[0]
