"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LocationPicker } from "@/components/map";
import { BoxedImage } from "@/components/panels/PotholeDetail";
import { BandChip, SeverityChip, THRESHOLD_NOTE } from "@/components/ui/chips";
import { apiFetch, BASE_URL } from "@/lib/api";
import type { Road, SeverityLevel, UploadResult } from "@/lib/types";

const MAX_MB = 10;
const BAD_FILE = `Use a JPG or PNG under ${MAX_MB} MB`;
const SEVERITY_COLOR: Record<SeverityLevel, string> = { High: "#c62828", Medium: "#9a4a00", Low: "#2e7d32" };

export default function UploadPage() {
  const [roads, setRoads] = useState<Road[]>([]);
  const [roadId, setRoadId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [gpsSource, setGpsSource] = useState<"manual" | "map_click">("manual");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  useEffect(() => {
    apiFetch<Road[]>("/roads").then(setRoads).catch((e) => setError(e.message));
  }, []);

  function pickFile(f: File | null) {
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
    setResult(null);
    setError(f && (!["image/jpeg", "image/png"].includes(f.type) || f.size > MAX_MB * 1024 * 1024) ? BAD_FILE : null);
  }

  const latNum = Number(lat), lngNum = Number(lng);
  const coordError =
    (lat === "") !== (lng === "") ? "Give both latitude and longitude, or leave both blank"
    : lat !== "" && !(Math.abs(latNum) <= 90 && Math.abs(lngNum) <= 180) ? "Latitude must be -90 to 90, longitude -180 to 180"
    : null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || coordError || !roadId) return;
    const form = new FormData();
    form.append("file", file);
    form.append("road_id", roadId);
    if (lat !== "") {
      form.append("lat", lat);
      form.append("lng", lng);
      form.append("gps_source", gpsSource);
    }
    setBusy(true);
    setError(null);
    try {
      setResult(await apiFetch<UploadResult>("/uploads", { method: "POST", body: form }));
    } catch (err) {
      setError((err as Error).message); // form values are kept, so the user can fix and resend
    } finally {
      setBusy(false);
    }
  }

  const field = "mt-1 block min-h-11 w-full rounded border border-muted bg-surface px-3 py-2";
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <h1 className="text-[28px] font-semibold">Upload a road photo</h1>

      <form onSubmit={submit} className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow" noValidate>
        <label className="font-medium">Photo (JPG or PNG, up to {MAX_MB} MB)
          <input type="file" accept="image/jpeg,image/png" className={field} onChange={(e) => pickFile(e.target.files?.[0] ?? null)} />
        </label>
        {/* eslint-disable-next-line @next/next/no-img-element -- local preview from an object URL */}
        {preview && !result && <img src={preview} alt="Selected photo preview" className="max-h-72 rounded object-contain" />}

        <label className="font-medium">Road
          <select required className={field} value={roadId} onChange={(e) => setRoadId(e.target.value)}>
            <option value="">Choose the road…</option>
            {roads.map((r) => <option key={r.road_id} value={r.road_id}>{r.name} ({r.road_type})</option>)}
          </select>
        </label>

        <fieldset className="flex flex-col gap-2">
          <legend className="font-medium">Location</legend>
          <p className="text-xs text-muted">Leave blank to use the GPS stored in the photo, or type it, or click the map.</p>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs text-muted">Latitude
              <input inputMode="decimal" className={field} value={lat} aria-invalid={!!coordError}
                onChange={(e) => { setLat(e.target.value); setGpsSource("manual"); }} />
            </label>
            <label className="text-xs text-muted">Longitude
              <input inputMode="decimal" className={field} value={lng} aria-invalid={!!coordError}
                onChange={(e) => { setLng(e.target.value); setGpsSource("manual"); }} />
            </label>
          </div>
          {coordError && <p role="alert" className="text-xs text-critical">{coordError}</p>}
          <LocationPicker
            value={lat !== "" && lng !== "" && !coordError ? [latNum, lngNum] : null}
            onPick={(a, b) => { setLat(a.toFixed(6)); setLng(b.toFixed(6)); setGpsSource("map_click"); }}
          />
        </fieldset>

        <button type="submit" disabled={busy || !file || !roadId || !!coordError}
          className="min-h-11 rounded bg-brand px-4 py-2 font-semibold text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:opacity-50">
          {busy ? "Analyzing image…" : "Detect potholes"}
        </button>
        {busy && <p role="status" className="text-muted">Analyzing image… this takes a few seconds on a laptop.</p>}
        {error && <p role="alert" className="text-critical">{error}</p>}
      </form>

      {result && (
        <section aria-label="Detection results" className="flex flex-col gap-3 rounded-lg bg-surface p-4 shadow">
          <h2 className="text-xl font-semibold">
            {result.potholes.length === 0 ? "No potholes detected" : `${result.potholes.length} pothole(s) found`}
          </h2>
          <BoxedImage
            src={`${BASE_URL}/uploads/${result.upload_id}/image`}
            width={result.image_width}
            height={result.image_height}
            alt="Uploaded photo with each detected pothole outlined and numbered"
            boxes={result.potholes.map((p, i) => ({
              x: p.bbox_x!, y: p.bbox_y!, w: p.bbox_w!, h: p.bbox_h!, label: String(i + 1), color: SEVERITY_COLOR[p.severity_level],
            }))}
          />
          {result.potholes.length > 0 && (
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-muted">
                <tr><th className="py-1">#</th><th>Relative severity</th><th>Priority</th><th>Confidence</th></tr>
              </thead>
              <tbody>
                {result.potholes.map((p, i) => (
                  <tr key={p.pothole_id} className="border-t border-background">
                    <td className="py-1">{i + 1}</td>
                    <td><SeverityChip level={p.severity_level} /></td>
                    <td><BandChip band={p.priority_band} /> {p.priority_score.toFixed(2)}</td>
                    <td>{(p.confidence ?? 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="text-xs text-muted">
            Location {result.lat.toFixed(5)}, {result.lng.toFixed(5)} ({result.gps_source === "exif" ? "from photo GPS" : result.gps_source === "map_click" ? "map click" : "typed"}).
            All potholes in one photo share this point. {THRESHOLD_NOTE}
          </p>
          <div className="flex gap-3">
            <Link href="/" className="min-h-11 rounded bg-brand px-4 py-2 font-semibold text-white">View on map</Link>
            <button type="button" onClick={() => pickFile(null)} className="min-h-11 rounded border border-brand px-4 py-2 font-semibold text-brand">
              Upload another
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
