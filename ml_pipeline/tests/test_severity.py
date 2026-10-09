import pytest

from severity import weak_severity


def test_no_potholes_is_zero():
    assert weak_severity([]) == {"severity": 0.0, "pothole_area_ratio": 0.0, "pothole_count": 0}


def test_one_box_covering_30_percent_is_area_maxed():
    s = weak_severity([(0.6, 0.5)])
    assert s["pothole_area_ratio"] == 0.3
    assert s["severity"] == pytest.approx((0.5 * 1 + 0.2 * 1 / 8) / 0.7, abs=1e-4)


def test_many_boxes_cap_at_one():
    s = weak_severity([(0.5, 0.5)] * 10)  # 250% summed area, 10 boxes
    assert s["pothole_area_ratio"] == 1.0 and s["severity"] == 1.0
