"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Camera, LocateFixed, ScanSearch, UploadCloud } from "lucide-react";
import { LocationPicker } from "@/components/map";
import Button, { buttonClass } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { cardClass, fieldClass, labelClass, linkClass } from "@/components/ui/styles";
import { BoxedImage } from "@/components/panels/PotholeDetail";
import { BandChip, SeverityChip, THRESHOLD_NOTE } from "@/components/ui/chips";
import { apiFetch, BASE_URL } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { SEVERITY_COLOR } from "@/lib/colors";
import type { Road, UploadResult } from "@/lib/types";

const MAX_MB = 10;
const MAX_VIDEO_MB = 50;
const MAX_DESCRIPTION = 1000; // same limit as the API
const IMAGE_TYPES = ["image/jpeg", "image/png"];
const VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/webm"];

function fileError(f: File): string | null {
  if (IMAGE_TYPES.includes(f.type)) return f.size > MAX_MB * 1024 * 1024 ? `Use a JPG or PNG under ${MAX_MB} MB` : null;
  if (VIDEO_TYPES.includes(f.type)) return f.size > MAX_VIDEO_MB * 1024 * 1024 ? `Use a video under ${MAX_VIDEO_MB} MB` : null;
  return `Use a JPG or PNG under ${MAX_MB} MB, or an MP4, MOV or WebM video under ${MAX_VIDEO_MB} MB`;
}
const MATCH_TEXT = { new: "New", repeat: "Yes, same pothole (seen again)", recurrence: "Yes, came back after repair" };

export default function UploadPage() {
  const [roads, setRoads] = useState<Road[]>([]);
  const [roadId, setRoadId] = useState("");
  const [description, setDescription] = useState("");
  const { user } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [gpsSource, setGpsSource] = useState<"manual" | "map_click">("manual");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const [manual, setManual] = useState(false);
  const [locating, setLocating] = useState(false);
  const [locError, setLocError] = useState<string | null>(null);

  function locateMe() {
    setLocating(true);
    setLocError(null);
    navigator.geolocation.getCurrentPosition(
      // the API knows only "manual" and "map_click"; a device fix is sent as manual (no API change)
      (pos) => { setLat(pos.coords.latitude.toFixed(6)); setLng(pos.coords.longitude.toFixed(6)); setGpsSource("manual"); setLocating(false); },
      (err) => { setLocError(`Could not get your location: ${err.message}`); setLocating(false); },
      { enableHighAccuracy: true, timeout: 15000 },
    );
  }

  useEffect(() => {
    apiFetch<Road[]>("/roads").then(setRoads).catch((e) => setError(e.message));
  }, []);

  function pickFile(f: File | null) {
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
    setResult(null);
    setError(f ? fileError(f) : null);
  }

  const isVideo = !!file && VIDEO_TYPES.includes(file.type);
  const latNum = Number(lat), lngNum = Number(lng);
  const coordError =
    (lat === "") !== (lng === "") ? "Give both latitude and longitude, or leave both blank"
    : isVideo && lat === "" ? "Videos need a location: type it or click the map"
    : lat !== "" && !(Math.abs(latNum) <= 90 && Math.abs(lngNum) <= 180) ? "Latitude must be -90 to 90, longitude -180 to 180"
    : null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || fileError(file) || coordError) return;
    const form = new FormData();
    form.append("file", file);
    if (roadId) form.append("road_id", roadId); // empty: the backend finds the road on OpenStreetMap
    if (description.trim()) form.append("description", description.trim());
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

  const field = `${fieldClass} mt-1 min-h-11 w-full`;
  const fieldLabel = `${labelClass} block`;
  return (
    <div className="flex flex-col gap-6">
      <PageHeader icon={Camera} title="Report a pothole"
        subtitle="Upload a road photo or short video. The model finds the potholes and scores how urgently each needs repair." />

      <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <form onSubmit={submit} className={`flex flex-col gap-5 ${cardClass}`} noValidate>
        <label className={fieldLabel}>Photo (JPG or PNG, up to {MAX_MB} MB) or short video (up to {MAX_VIDEO_MB} MB)
          <span
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); pickFile(e.dataTransfer.files?.[0] ?? null); }}
            className={`mt-1 flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed bg-background px-4 py-8 text-center font-sans normal-case tracking-normal shadow-recessed transition-all duration-200 has-[:focus-visible]:border-accent ${dragging ? "border-accent shadow-[var(--shadow-recessed),0_0_0_2px_var(--accent)]" : "border-border-dark hover:border-primary"}`}>
            <UploadCloud aria-hidden size={32} strokeWidth={2.5} className="text-primary" />
            <span className="text-base font-semibold text-foreground">
              {file ? file.name : "Drag a photo or video here, or click to browse"}
            </span>
            {file && <span className="text-sm font-normal text-muted">Click or drop another file to replace it</span>}
            <input type="file" accept={[...IMAGE_TYPES, ...VIDEO_TYPES].join(",")} className="sr-only"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)} />
          </span>
        </label>
        {preview && !result && (isVideo
          ? <video src={preview} controls muted className="max-h-72 rounded-md" aria-label={`Selected video: ${file?.name}`} />
          // eslint-disable-next-line @next/next/no-img-element -- local preview from an object URL
          : <img src={preview} alt="Selected photo preview" className="max-h-72 rounded-md object-contain" />)}

        <label className={fieldLabel}>Description (optional, up to {MAX_DESCRIPTION} characters)
          <textarea className={`${field} min-h-24 font-sans`} maxLength={MAX_DESCRIPTION} value={description}
            placeholder="What did you see? e.g. deep pothole in the left lane near the bus stop"
            onChange={(e) => setDescription(e.target.value)} />
          <span className="mt-1 block text-right font-mono text-xs text-muted" aria-live="polite">
            {description.length}/{MAX_DESCRIPTION}
          </span>
        </label>

        <label className={fieldLabel}>Road (optional: found from the location if left empty)
          <select className={field} value={roadId} onChange={(e) => setRoadId(e.target.value)}>
            <option value="">Find automatically (OpenStreetMap)</option>
            {roads.map((r) => <option key={r.road_id} value={r.road_id}>{r.name} ({r.road_type})</option>)}
          </select>
        </label>

        <fieldset className="flex flex-col gap-2">
          <legend className={fieldLabel}>Location</legend>
          <p className="text-sm text-muted">
            {isVideo ? "Type the clip's location or click the map." : "Leave blank to use the GPS stored in the photo, or type it, or click the map."}
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" size="sm" disabled={locating} onClick={locateMe}>
              <LocateFixed aria-hidden size={16} strokeWidth={2.5} /> {locating ? "Locating…" : "Use my location"}
            </Button>
            <button type="button" aria-expanded={manual || !!coordError} aria-controls="manual-coords" onClick={() => setManual(!manual)}
              className={`text-sm ${linkClass}`}>
              {manual ? "Hide manual entry" : "Edit manually"}
            </button>
            {lat !== "" && lng !== "" && !coordError && <span className="text-sm text-muted">Set to {lat}, {lng}</span>}
          </div>
          {locError && <p role="alert" className="text-sm font-semibold text-critical-text">{locError}</p>}
          <div id="manual-coords" hidden={!manual && !coordError} className="grid grid-cols-2 gap-2">
            <label className={fieldLabel}>Latitude
              <input inputMode="decimal" className={field} value={lat} aria-invalid={!!coordError}
                onChange={(e) => { setLat(e.target.value); setGpsSource("manual"); }} />
            </label>
            <label className={fieldLabel}>Longitude
              <input inputMode="decimal" className={field} value={lng} aria-invalid={!!coordError}
                onChange={(e) => { setLng(e.target.value); setGpsSource("manual"); }} />
            </label>
          </div>
          {coordError && <p role="alert" className="text-sm font-semibold text-critical-text">{coordError}</p>}
          <LocationPicker
            value={lat !== "" && lng !== "" && !coordError ? [latNum, lngNum] : null}
            onPick={(a, b) => { setLat(a.toFixed(6)); setLng(b.toFixed(6)); setGpsSource("map_click"); }}
          />
        </fieldset>

        <div className="flex flex-wrap items-center gap-4">
          <Button type="submit" size="lg" disabled={busy || !file || !!coordError} aria-describedby="detect-missing">
            <ScanSearch aria-hidden size={20} strokeWidth={2.5} />
            {busy ? (isVideo ? "Analyzing video…" : "Analyzing image…") : "Detect potholes"}
          </Button>
          {!busy && (!file || coordError) && (
            <p id="detect-missing" className="text-sm font-semibold text-muted">
              Still needed: {[!file && "a photo or video", coordError && "a valid location"].filter(Boolean).join(" and ")}
              {" "}(the road is optional)
            </p>
          )}
        </div>
        {busy && (
          <p role="status" className="text-muted">
            {isVideo ? "Analyzing video… one frame per second, so this takes a while on a laptop." : "Analyzing image… this takes a few seconds on a laptop."}
          </p>
        )}
        {error && <p role="alert" className="font-semibold text-critical-text">{error}</p>}
      </form>

      {result && (
        <section aria-label="Detection results" className={`flex flex-col gap-4 ${cardClass}`}>
          <h2 className="text-2xl font-extrabold">
            {result.potholes.length === 0 ? "No potholes detected" : `${result.potholes.length} pothole(s) found`}
          </h2>
          {result.media_type === "video" ? (
            <>
              <p className="text-sm text-muted">{result.frames_sampled} frames checked; the same pothole in consecutive frames counts once.</p>
              <div className="grid grid-cols-2 gap-2">
                {result.potholes.map((p, i) => (
                  <figure key={p.pothole_id}>
                    <BoxedImage
                      src={`${BASE_URL}/uploads/${result.upload_id}/frames/${p.frame_index}`}
                      width={result.image_width}
                      height={result.image_height}
                      alt={`Video frame at ${p.frame_time_s?.toFixed(0)} s with pothole ${i + 1} outlined`}
                      boxes={[{ x: p.bbox_x!, y: p.bbox_y!, w: p.bbox_w!, h: p.bbox_h!, label: String(i + 1), color: SEVERITY_COLOR[p.severity_level] }]}
                    />
                    <figcaption className="text-xs text-muted">#{i + 1} at {p.frame_time_s?.toFixed(1)} s</figcaption>
                  </figure>
                ))}
              </div>
            </>
          ) : (
            <BoxedImage
              src={`${BASE_URL}/uploads/${result.upload_id}/image`}
              width={result.image_width}
              height={result.image_height}
              alt="Uploaded photo with each detected pothole outlined and numbered"
              boxes={result.potholes.map((p, i) => ({
                x: p.bbox_x!, y: p.bbox_y!, w: p.bbox_w!, h: p.bbox_h!, label: String(i + 1), color: SEVERITY_COLOR[p.severity_level],
              }))}
            />
          )}
          {result.potholes.length > 0 && (
            <table className="w-full text-left text-sm">
              <thead className={labelClass}>
                <tr><th className="py-1">#</th><th>Relative severity</th><th>Priority</th><th>Confidence</th><th>Seen before?</th></tr>
              </thead>
              <tbody>
                {result.potholes.map((p, i) => (
                  <tr key={p.pothole_id} className="border-t border-border">
                    <td className="py-1">{i + 1}</td>
                    <td><SeverityChip level={p.severity_level} /></td>
                    <td><BandChip band={p.priority_band} /> {p.priority_score.toFixed(2)}</td>
                    <td>{(p.confidence ?? 0).toFixed(2)}</td>
                    <td>{MATCH_TEXT[p.match]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="text-xs text-muted">
            Location {result.lat.toFixed(5)}, {result.lng.toFixed(5)} ({result.gps_source === "exif" ? "from photo GPS" : result.gps_source === "map_click" ? "map click" : "typed"}).
            All potholes in one {result.media_type === "video" ? "clip" : "photo"} share this point. {THRESHOLD_NOTE}
          </p>
          <div className="flex gap-3">
            {user?.role === "official" && <Link href="/" className={buttonClass("primary", "md")}>View on map</Link>}
            <Button variant="outline" onClick={() => pickFile(null)}>Upload another</Button>
          </div>
        </section>
      )}
      </div>
    </div>
  );
}
