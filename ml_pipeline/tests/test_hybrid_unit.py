"""Model code checks that need no data download (random weights, fake rows)."""
import numpy as np
import pandas as pd
import torch

from hybrid import NUMERIC, ROAD_CLASSES, Hybrid, features, loss_fn


def fake_rows(n=3):
    return pd.DataFrame({
        "traffic_vehicles_per_day": [800, 15000, 40000][:n], "speed_limit_kmph": [25, 50, 80][:n],
        "dist_hospital_m": [0, 500, 20000][:n], "dist_school_m": [100, 1000, 20000][:n],
        "dist_fire_station_m": [3000, 3000, 3000][:n], "dist_bus_stop_m": [50, 50, 50][:n],
        "critical_facilities_500m": [3, 1, 0][:n], "is_junction": [1, 0, np.nan][:n],
        "is_curve_or_bridge": [0, 0, 1][:n], "past_accidents_nearby": [0, 2, 1][:n],
        "rain_or_poor_lighting": [0, 1, 0][:n], "complaint_count": [3, 1, 5][:n], "days_unrepaired": [10, 40, 80][:n],
    })


def test_features_transform():
    f = features(fake_rows())
    assert list(f.columns) == NUMERIC
    assert np.allclose(f.prox_hospital, [1.0, np.exp(-1), np.exp(-40)])
    assert f.is_junction.tolist() == [1, 0, 0]  # missing flag -> 0
    assert np.isclose(f.log_traffic[0], np.log1p(800))


def test_forward_shapes_and_ranges():
    torch.manual_seed(0)
    m = Hybrid(pretrained=False)
    p, s = m(torch.randn(2, 3, 224, 224), torch.tensor([0, 3]), torch.randn(2, len(NUMERIC)))
    assert p.shape == s.shape == (2,)
    assert ((p > 0) & (p < 1)).all() and ((s > 0) & (s < 1)).all()


def test_only_layer4_and_heads_train():
    m = Hybrid(pretrained=False)
    trainable = {n.split(".")[0] + "." + n.split(".")[1] for n, p in m.named_parameters() if p.requires_grad and n.startswith("cnn")}
    assert trainable == {"cnn.layer4"}


def test_ranking_loss_only_uses_clear_pairs():
    p = torch.tensor([0.50, 0.51, 0.90])
    good = torch.tensor([0.40, 0.41, 0.95])
    bad = torch.tensor([0.95, 0.41, 0.40])  # top pothole ranked last
    s = torch.zeros(3)
    assert loss_fn(bad, s, p, s) > loss_fn(good, s, p, s)


def test_road_classes_match_build_script():
    from build_real_dataset import IMPORTANCE
    assert set(ROAD_CLASSES) == set(IMPORTANCE)
