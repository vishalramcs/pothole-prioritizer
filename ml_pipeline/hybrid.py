"""Step 4: hybrid priority model = ResNet18 image branch + tabular MLP branch.

    image (224 px) -> ResNet18 (ImageNet weights, only layer4 trained) -> 512-d --+--> severity head (aux)
    road class -> embedding (4-d) + numeric context features -> MLP -> 64-d ------+--> priority head (sigmoid)

Labels: priority_score from build_real_dataset.add_priority (a hand-written formula) and the weak box-based
severity (severity.py). The model therefore LEARNS THOSE FORMULAS; it cannot know more than they encode.
Loss = MSE(priority) + 0.5 * MSE(severity) [+ RANK_W * MarginRankingLoss on pairs within a batch].
Split: the spatial `split` column from build_real_dataset (whole grid cells go to train/val/test).

Run:  python hybrid.py            (needs data_real/pothole_dataset_real_context.csv)
"""
import json
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

HERE = Path(__file__).resolve().parent
DATA = HERE / "data_real" / "pothole_dataset_real_context.csv"
IMAGES = HERE / "pothole_images"
SEED, IMG, BATCH, EPOCHS, PATIENCE, LR = 42, 224, 16, 40, 6, 1e-3
RANK_W, MARGIN = 0.3, 0.02
ROAD_CLASSES = ["highway", "arterial", "town", "residential"]
NUMERIC = ["log_traffic", "speed", "prox_hospital", "prox_school", "prox_fire_station", "prox_bus_stop",
           "critical_facilities_500m", "is_junction", "is_curve_or_bridge", "past_accidents_nearby",
           "rain_or_poor_lighting", "complaint_count", "days_unrepaired"]


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_table(path: Path = DATA) -> pd.DataFrame:
    """Rows usable for training: on a mapped road and with a severity label."""
    df = pd.read_csv(path)
    return df[(df.road_match_ok == 1) & df.severity.notna()].reset_index(drop=True)


def features(df: pd.DataFrame) -> pd.DataFrame:
    """Raw context columns -> model inputs (same transforms as the plan: log traffic, exp(-d/500) proximity)."""
    f = pd.DataFrame(index=df.index)
    f["log_traffic"] = np.log1p(df.traffic_vehicles_per_day)
    f["speed"] = df.speed_limit_kmph
    for kind in ("hospital", "school", "fire_station"):
        f[f"prox_{kind}"] = np.exp(-df[f"dist_{kind}_m"] / 500)
    f["prox_bus_stop"] = np.exp(-df.dist_bus_stop_m / 500)
    for c in ["critical_facilities_500m", "is_junction", "is_curve_or_bridge", "past_accidents_nearby",
              "rain_or_poor_lighting", "complaint_count", "days_unrepaired"]:
        f[c] = df[c].fillna(0)
    return f[NUMERIC].astype("float32")


class Scaler:
    """Standardise numeric features with TRAIN statistics only (no leakage from val/test)."""

    def __init__(self, train: pd.DataFrame):
        self.mean = train.mean()
        self.std = train.std().replace(0, 1).fillna(1)

    def __call__(self, f: pd.DataFrame) -> np.ndarray:
        return ((f - self.mean) / self.std).to_numpy(dtype="float32")

    def to_json(self) -> dict:
        return {"mean": self.mean.to_dict(), "std": self.std.to_dict()}


TRAIN_TF = transforms.Compose([transforms.Resize((IMG, IMG)), transforms.RandomHorizontalFlip(),
                               transforms.ColorJitter(0.2, 0.2), transforms.ToTensor(),
                               transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
EVAL_TF = transforms.Compose([transforms.Resize((IMG, IMG)), transforms.ToTensor(),
                              transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])


class Rows(torch.utils.data.Dataset):
    def __init__(self, df: pd.DataFrame, x_num: np.ndarray, tf):
        self.df, self.x_num, self.tf = df, x_num, tf

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        r = self.df.iloc[i]
        img = self.tf(Image.open(IMAGES / r.image_file).convert("RGB"))
        road = ROAD_CLASSES.index(r.road_class)
        return (img, torch.tensor(road), torch.from_numpy(self.x_num[i]),
                torch.tensor(r.priority_score, dtype=torch.float32), torch.tensor(r.severity, dtype=torch.float32))


class Hybrid(nn.Module):
    def __init__(self, n_numeric: int = len(NUMERIC), pretrained: bool = True):
        super().__init__()
        cnn = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None)
        cnn.fc = nn.Identity()
        for name, p in cnn.named_parameters():  # small data + CPU: train only the last block
            p.requires_grad = name.startswith("layer4")
        self.cnn = cnn
        self.road = nn.Embedding(len(ROAD_CLASSES), 4)
        self.mlp = nn.Sequential(nn.Linear(n_numeric + 4, 64), nn.ReLU(), nn.Dropout(0.1), nn.Linear(64, 64), nn.ReLU())
        self.priority_head = nn.Sequential(nn.Linear(512 + 64, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid())
        self.severity_head = nn.Sequential(nn.Linear(512, 1), nn.Sigmoid())  # image branch only

    def tabular(self, road, x_num):
        return self.mlp(torch.cat([self.road(road), x_num], dim=1))

    def forward(self, img, road, x_num):
        z_img = self.cnn(img)
        prio = self.priority_head(torch.cat([z_img, self.tabular(road, x_num)], dim=1)).squeeze(1)
        return prio, self.severity_head(z_img).squeeze(1)


def loss_fn(p_hat, s_hat, p, s, rank_w: float = RANK_W):
    loss = nn.functional.mse_loss(p_hat, p) + 0.5 * nn.functional.mse_loss(s_hat, s)
    if rank_w:
        i, j = torch.triu_indices(len(p), len(p), 1)
        keep = (p[i] - p[j]).abs() > MARGIN  # only pairs whose order is clear in the labels
        if keep.any():
            target = torch.sign(p[i] - p[j])[keep]
            loss = loss + rank_w * nn.functional.margin_ranking_loss(p_hat[i][keep], p_hat[j][keep], target, margin=MARGIN)
    return loss


def predict(model: Hybrid, loader) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    ps, ss = [], []
    with torch.no_grad():
        for img, road, x, *_ in loader:
            p, s = model(img, road, x)
            ps.append(p.numpy())
            ss.append(s.numpy())
    return np.concatenate(ps), np.concatenate(ss)


def run_epoch(model, loader, opt=None) -> float:
    model.train(opt is not None)
    total, n = 0.0, 0
    with torch.set_grad_enabled(opt is not None):
        for img, road, x, p, s in loader:
            p_hat, s_hat = model(img, road, x)
            loss = loss_fn(p_hat, s_hat, p, s)
            if opt:
                opt.zero_grad()
                loss.backward()
                opt.step()
            total += loss.item() * len(p)
            n += len(p)
    return total / n


def main() -> None:
    seed_everything()
    df = load_table()
    parts = {k: df[df.split == k].reset_index(drop=True) for k in ("train", "val", "test")}
    print({k: len(v) for k, v in parts.items()})
    scaler = Scaler(features(parts["train"]))
    loaders = {}
    for k, part in parts.items():
        ds = Rows(part, scaler(features(part)), TRAIN_TF if k == "train" else EVAL_TF)
        g = torch.Generator().manual_seed(SEED)
        loaders[k] = torch.utils.data.DataLoader(ds, batch_size=BATCH, shuffle=k == "train", generator=g)

    model = Hybrid()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=1e-4)
    (HERE / "models").mkdir(exist_ok=True)
    (HERE / "outputs").mkdir(exist_ok=True)
    best, wait, curve = float("inf"), 0, []
    for epoch in range(1, EPOCHS + 1):
        t = time.time()
        tr, va = run_epoch(model, loaders["train"], opt), run_epoch(model, loaders["val"])
        curve.append({"epoch": epoch, "train_loss": tr, "val_loss": va})
        print(f"epoch {epoch:2d}  train {tr:.4f}  val {va:.4f}  ({time.time() - t:.0f}s)")
        if va < best - 1e-5:
            best, wait = va, 0
            torch.save({"state_dict": model.state_dict(), "scaler": scaler.to_json(), "numeric": NUMERIC,
                        "road_classes": ROAD_CLASSES}, HERE / "models" / "hybrid_best.pt")
        else:
            wait += 1
            if wait >= PATIENCE:
                print("early stop")
                break
    pd.DataFrame(curve).to_csv(HERE / "outputs" / "train_curve.csv", index=False)
    plot_curve(curve)
    print(f"best val loss {best:.4f} -> models/hybrid_best.pt")
    (HERE / "outputs" / "train_info.json").write_text(json.dumps(
        {"rows": {k: len(v) for k, v in parts.items()}, "best_val_loss": best, "epochs_run": len(curve)}, indent=1))


def plot_curve(curve: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    c = pd.DataFrame(curve)
    plt.figure(figsize=(5, 3))
    plt.plot(c.epoch, c.train_loss, label="train")
    plt.plot(c.epoch, c.val_loss, label="val")
    plt.xlabel("epoch")
    plt.ylabel("loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(HERE / "outputs" / "train_curve.png", dpi=120)


def load_model(path: Path = HERE / "models" / "hybrid_best.pt") -> tuple[Hybrid, Scaler]:
    ck = torch.load(path, weights_only=False)
    model = Hybrid(pretrained=False)
    model.load_state_dict(ck["state_dict"])
    model.eval()
    scaler = Scaler.__new__(Scaler)
    scaler.mean, scaler.std = pd.Series(ck["scaler"]["mean"]), pd.Series(ck["scaler"]["std"])
    return model, scaler


def score(model: Hybrid, scaler: Scaler, image_file: str, context: dict) -> tuple[float, float]:
    """(priority, severity) for one image + one row of raw context columns (as in the dataset CSV)."""
    row = pd.DataFrame([context])
    img = EVAL_TF(Image.open(IMAGES / image_file).convert("RGB")).unsqueeze(0)
    x = torch.from_numpy(scaler(features(row)))
    with torch.no_grad():
        p, s = model(img, torch.tensor([ROAD_CLASSES.index(context["road_class"])]), x)
    return float(p), float(s)


if __name__ == "__main__":
    main()
