"""More real images: RDD2022 India subset, potholes only (class D40), added to pothole_images/ + pothole_labels/.

RDD2022: the multi-national Road Damage Dataset (CRDDC 2022), CC BY 4.0, figshare.com/articles/dataset/21431547.
It ships as one 13 GB zip holding one zip per country, stored uncompressed. This script reads the outer zip's
index over HTTP range requests, downloads only the India.zip byte range (0.53 GB) to raw/rdd2022/, and keeps
India images with at least one D40 (pothole) box. Boxes are hand-drawn (Pascal VOC); cracks and other damage
classes are ignored. No GPS. Files are written as rdd_<name>.jpg; pothole_images_manifest.csv gets a `source`.

Run:  python prepare_rdd2022.py [--max 800]
"""
import argparse
import csv
import io
import random
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ZIP_URL = "https://ndownloader.figshare.com/files/38030910"
UA = {"User-Agent": "SRPPS hackathon ml_pipeline"}


def fetch(url: str, start: int, end: int) -> bytes:
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        if r.status != 206:
            raise OSError(f"server ignored the range request (HTTP {r.status})")
        return r.read()


class RangeFile(io.RawIOBase):
    """Read-only, seekable view of a remote file, fetched in cached blocks: enough for zipfile to read the index."""

    def __init__(self, url: str, block: int = 1 << 20):
        self.block, self.pos, self.cache = block, 0, {}
        req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            self.size = int(r.headers["Content-Range"].split("/")[1])
            self.url = r.url  # follow the redirect once, then hit the storage URL directly

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        got = 0
        while got < n:
            i, off = divmod(self.pos + got, self.block)
            if i not in self.cache:
                self.cache[i] = fetch(self.url, i * self.block, min((i + 1) * self.block, self.size) - 1)
            chunk = self.cache[i][off:off + n - got]
            b[got:got + len(chunk)] = chunk
            got += len(chunk)
        self.pos += n
        return n


def download_india(dest: Path) -> None:
    raw = RangeFile(ZIP_URL)
    info = zipfile.ZipFile(raw).getinfo("RDD2022/India.zip")
    assert info.compress_type == zipfile.ZIP_STORED, "India.zip is expected to be stored uncompressed"
    head = fetch(raw.url, info.header_offset, info.header_offset + 29)  # local header: 30 bytes + name + extra
    start = info.header_offset + 30 + int.from_bytes(head[26:28], "little") + int.from_bytes(head[28:30], "little")
    tmp = dest.with_suffix(".part")
    done = tmp.stat().st_size if tmp.exists() else 0  # resume an interrupted download
    with open(tmp, "ab") as f:
        for s in range(start + done, start + info.file_size, 64 << 20):  # 64 MB pieces
            # ZIP_URL, not raw.url: the storage link it redirects to expires within minutes (HTTP 403)
            f.write(fetch(ZIP_URL, s, min(s + (64 << 20), start + info.file_size) - 1))
            print(f"  {f.tell() / 1e6:.0f} of {info.file_size / 1e6:.0f} MB")
    tmp.replace(dest)  # only a complete download gets the final name


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=800, help="keep at most this many pothole images (seeded sample)")
    a = ap.parse_args()
    india = HERE / "raw" / "rdd2022" / "India.zip"
    india.parent.mkdir(parents=True, exist_ok=True)
    if not india.exists():
        download_india(india)
    z = zipfile.ZipFile(india)
    names = z.namelist()
    jpgs = {n.rsplit("/", 1)[-1]: n for n in names if n.endswith(".jpg")}
    xmls = sorted(n for n in names if n.endswith(".xml"))
    potholes = {}
    for n in xmls:
        root = ET.fromstring(z.read(n))
        w, h = float(root.findtext("size/width")), float(root.findtext("size/height"))
        boxes = []
        for obj in root.iter("object"):
            if obj.findtext("name") == "D40":
                bb = obj.find("bndbox")
                x0, y0, x1, y1 = (float(bb.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax"))
                boxes.append(f"0 {(x0 + x1) / 2 / w:.6f} {(y0 + y1) / 2 / h:.6f} {(x1 - x0) / w:.6f} {(y1 - y0) / h:.6f}")
        image = root.findtext("filename")
        if boxes and image in jpgs:
            potholes[image] = boxes
    print(f"India.zip: {len(xmls)} annotations, {len(jpgs)} images; {len(potholes)} images contain a pothole (D40)")

    chosen = sorted(potholes)
    if len(chosen) > a.max:
        chosen = sorted(random.Random(42).sample(chosen, a.max))
    for image in chosen:
        (HERE / "pothole_images" / f"rdd_{image}").write_bytes(z.read(jpgs[image]))
        (HERE / "pothole_labels" / f"rdd_{Path(image).stem}.txt").write_text("\n".join(potholes[image]) + "\n")

    manifest = HERE / "pothole_images_manifest.csv"
    rows = [r for r in csv.DictReader(open(manifest)) if not r["image_file"].startswith("rdd_")]
    for r in rows:
        r["source"] = r.get("source") or "roboflow_potholes_detection"
    rows += [{"image_file": f"rdd_{i}", "source": "rdd2022_india", "roboflow_split": "", "n_boxes": len(potholes[i])}
             for i in chosen]
    with open(manifest, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["image_file", "source", "roboflow_split", "n_boxes"])
        w.writeheader()
        w.writerows(rows)
    print(f"added {len(chosen)} RDD2022 India pothole images (manifest now {len(rows)} images)")


if __name__ == "__main__":
    main()
