"""Second image source with REAL GPS: Outerview Global Potholes Dataset (CC BY 4.0), Mumbai subset.

huggingface.co/datasets/Outerview/global-potholes-dataset: 29k street-level photos (imagery from Mapillary)
that Outerview's own AI model labelled as showing a pothole, each with latitude/longitude. No boxes.
This script reads only the zip's index and the Mumbai members (~32 MB) over HTTP range requests instead of
downloading the 1.3 GB archive, and writes:
  pothole_images_mumbai/       the photos
  locations_mumbai.csv         image_file, lat, lon   (for build_real_dataset.py --locations)
"""
import zipfile
from pathlib import Path

import pandas as pd
from huggingface_hub import HfFileSystem, hf_hub_download

HERE = Path(__file__).resolve().parent
REPO = "Outerview/global-potholes-dataset"
MUMBAI = (18.9, 72.75, 19.3, 73.0)  # lat_min, lon_min, lat_max, lon_max


def main() -> None:
    csv = hf_hub_download(REPO, "Global_Potholes_Dataset.csv", repo_type="dataset", local_dir=HERE / "raw" / "outerview")
    df = pd.read_csv(csv)
    la0, lo0, la1, lo1 = MUMBAI
    sub = df[df.latitude.between(la0, la1) & df.longitude.between(lo0, lo1)]
    out = HERE / "pothole_images_mumbai"
    out.mkdir(exist_ok=True)
    with HfFileSystem().open(f"datasets/{REPO}/Global_Potholes_Dataset-image.zip", "rb", block_size=1 << 20) as f:
        z = zipfile.ZipFile(f)
        members = {n.rsplit("/", 1)[-1]: n for n in z.namelist()}
        kept = []
        for r in sub.itertuples():
            if r.filename in members and not (out / r.filename).exists():
                (out / r.filename).write_bytes(z.read(members[r.filename]))
            if (out / r.filename).exists():
                kept.append({"image_file": r.filename, "lat": r.latitude, "lon": r.longitude})
    pd.DataFrame(kept).to_csv(HERE / "locations_mumbai.csv", index=False)
    print(f"{len(kept)} Mumbai photos with GPS -> {out}")


if __name__ == "__main__":
    main()
