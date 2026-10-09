"""Step 6: why is each pothole where it is in the ranking?

- outputs/ranked_potholes.csv: model ranking with the label formula's breakdown (factor x weight per pothole)
- outputs/shap_tabular.csv/.png: SHAP on the model's TABULAR branch. The image part is held at the average
  training image embedding, so the values show how the context features move the model's priority.
- outputs/priority_map.html: Folium map coloured by predicted priority (locations are the random demo
  points from build_real_dataset, not where the photos were taken; the map says so).
Run after evaluate.py (needs outputs/scored.csv).
"""
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import shap
import torch

from build_real_dataset import priority_parts
from hybrid import EVAL_TF, NUMERIC, ROAD_CLASSES, Rows, features, load_model, seed_everything

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def mean_image_embedding(model, df, scaler) -> torch.Tensor:
    loader = torch.utils.data.DataLoader(Rows(df, scaler(features(df)), EVAL_TF), batch_size=32)
    with torch.no_grad():
        return torch.cat([model.cnn(img) for img, *_ in loader]).mean(0, keepdim=True)


def main() -> None:
    seed_everything()
    df = pd.read_csv(OUT / "scored.csv")
    model, scaler = load_model()

    # 1. formula breakdown + ranked table
    parts = priority_parts(df).round(4)
    top3 = parts.apply(lambda r: ", ".join(f"{k} {v:.2f}" for k, v in r.sort_values(ascending=False).head(3).items()), axis=1)
    ranked = pd.concat([df[["pothole_id", "image_file", "split", "road_class", "road_name", "pred_priority",
                            "priority_score", "pred_severity", "severity"]], parts], axis=1)
    ranked.insert(0, "model_rank", df.pred_priority.rank(ascending=False, method="first").astype(int))
    ranked["top_factors"] = top3
    ranked.sort_values("model_rank").to_csv(OUT / "ranked_potholes.csv", index=False)
    print("ranked_potholes.csv written; top 5:")
    print(ranked.sort_values("model_rank").head(5)[["model_rank", "pothole_id", "road_class", "pred_priority", "top_factors"]]
          .to_string(index=False))

    # 2. SHAP on the tabular branch (road class index + scaled numeric features)
    train, test = df[df.split == "train"], df[df.split == "test"]
    emb = mean_image_embedding(model, train, scaler)
    cols = ["road_class"] + NUMERIC

    def tab_matrix(part):
        return np.c_[part.road_class.map(ROAD_CLASSES.index).to_numpy(), scaler(features(part))]

    def f(x: np.ndarray) -> np.ndarray:
        x = torch.tensor(x, dtype=torch.float32)
        road = x[:, 0].round().clamp(0, len(ROAD_CLASSES) - 1).long()
        with torch.no_grad():
            z = torch.cat([emb.expand(len(x), -1), model.tabular(road, x[:, 1:])], dim=1)
            return model.priority_head(z).squeeze(1).numpy()

    background = shap.kmeans(tab_matrix(train), 10)
    sv = shap.KernelExplainer(f, background).shap_values(tab_matrix(test), nsamples=300, silent=True)
    imp = pd.DataFrame({"feature": cols, "mean_abs_shap": np.abs(sv).mean(0)}).sort_values("mean_abs_shap", ascending=False)
    imp.to_csv(OUT / "shap_tabular.csv", index=False)
    print("\nmean |SHAP| on the test split (tabular branch):")
    print(imp.round(4).to_string(index=False))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(6, 4))
    plt.barh(imp.feature[::-1], imp.mean_abs_shap[::-1], color="#1f3864")
    plt.xlabel("mean |SHAP value| on model priority")
    plt.tight_layout()
    plt.savefig(OUT / "shap_tabular.png", dpi=120)

    # 3. Folium map
    m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=12, tiles="OpenStreetMap")
    m.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;top:10px;left:50px;z-index:9999;background:white;padding:6px;font:14px sans-serif">'
        "Predicted repair priority. Locations are random demo points, not where the photos were taken.</div>"))
    for r in ranked.itertuples():
        color = "#c62828" if r.pred_priority >= 0.6 else "#ef8f00" if r.pred_priority >= 0.35 else "#2e7d32"
        folium.CircleMarker([df.lat[r.Index], df.lon[r.Index]], radius=4 + 8 * r.pred_priority, color="white", weight=1,
                            fill=True, fill_color=color, fill_opacity=0.9,
                            popup=f"#{r.model_rank} {r.pothole_id} ({r.road_class})<br>priority {r.pred_priority:.2f}"
                                  f"<br>{r.top_factors}").add_to(m)
    m.save(str(OUT / "priority_map.html"))
    print("\npriority_map.html written")


if __name__ == "__main__":
    main()
