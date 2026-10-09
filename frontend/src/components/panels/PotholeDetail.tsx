"use client";

import { useEffect, useState } from "react";
import { apiFetch, potholeImageUrl } from "@/lib/api";
import { COLORS } from "@/lib/colors";
import type { PotholeDetail as Detail } from "@/lib/types";
import StatusButtons from "@/components/repairs/StatusButtons";
import { X } from "lucide-react";
import { BandChip, ROAD_SOURCE, SeverityChip, SourceBadge, THRESHOLD_NOTE } from "@/components/ui/chips";
import { focusRing, labelClass } from "@/components/ui/styles";

const PARTS = [
  { key: "severity", label: "Severity" },
  { key: "traffic", label: "Traffic" },
  { key: "importance", label: "Road importance" },
  { key: "repeat", label: "Repeat damage" },
  { key: "facility", label: "Near an important building" },
] as const;

/** Photo with the detected box drawn over it (box is in stored-image pixels, so use percentages). */
export function BoxedImage({ src, width, height, boxes, alt }: {
  src: string;
  width: number;
  height: number;
  boxes: { x: number; y: number; w: number; h: number; label?: string; color: string }[];
  alt: string;
}) {
  return (
    <div className="relative w-full">
      {/* eslint-disable-next-line @next/next/no-img-element -- served by our API, not a static asset */}
      <img src={src} alt={alt} className="block w-full rounded" />
      {boxes.map((b, i) => (
        <div
          key={i}
          className="absolute border-[3px]"
          style={{
            left: `${(b.x / width) * 100}%`, top: `${(b.y / height) * 100}%`,
            width: `${(b.w / width) * 100}%`, height: `${(b.h / height) * 100}%`, borderColor: b.color,
          }}
        >
          {b.label && (
            <span className="absolute -top-5 left-0 rounded px-1 text-xs font-bold text-white" style={{ background: b.color }}>
              {b.label}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function PotholeDetail({ id, onClose, onChanged }: {
  id: number;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [p, setP] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let alive = true;
    apiFetch<Detail>(`/potholes/${id}`)
      .then((d) => alive && (setP(d), setError(null)))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [id, version]);

  const shown = p?.pothole_id === id ? p : null; // never show the previous pothole while the next loads

  return (
    <aside aria-label="Pothole detail" className="flex h-full flex-col gap-4 overflow-y-auto rounded-lg bg-surface p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-extrabold">Pothole #{id}</h2>
        <button type="button" onClick={onClose} aria-label="Close detail panel"
          className={`flex h-9 w-9 items-center justify-center rounded-md bg-background transition-colors duration-200 hover:bg-border ${focusRing}`}>
          <X aria-hidden size={18} strokeWidth={2.5} />
        </button>
      </div>
      {error && <p role="alert" className="text-critical">{error}</p>}
      {!shown && !error && <p className="text-muted">Loading…</p>}
      {shown && (
        <>
          <BoxedImage
            src={potholeImageUrl(shown.pothole_id)}
            width={shown.image_width}
            height={shown.image_height}
            alt={`Photo of pothole ${shown.pothole_id} with the detected area outlined`}
            boxes={shown.bbox_x === null ? [] : [{
              x: shown.bbox_x, y: shown.bbox_y!, w: shown.bbox_w!, h: shown.bbox_h!, color: COLORS.primary,
            }]}
          />
          {shown.is_demo && (
            <p className="rounded-md bg-background px-3 py-2 text-xs font-medium text-muted">
              Demo data: the location and road are made up; the detection is the model&apos;s real result on a sample photo.
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <BandChip band={shown.priority_band} />
            <span className="text-lg font-extrabold">Priority {shown.priority_score.toFixed(2)}</span>
            {shown.safety_override && <span className="text-xs font-semibold text-critical">safety override</span>}
            <span className="text-muted">· {shown.status}</span>
          </div>

          <section>
            <h3 className={labelClass}>Relative severity (image-based)</h3>
            <p className="mt-1 flex items-center gap-2">
              <SeverityChip level={shown.severity_level} />
              covers {((shown.area_ratio ?? 0) * 100).toFixed(1)}% of the photo · confidence {(shown.confidence ?? 0).toFixed(2)}
            </p>
          </section>

          <section>
            <h3 className={labelClass}>Score breakdown</h3>
            <ul className="mt-1 space-y-2">
              {PARTS.map(({ key, label }) => {
                const b = shown.breakdown[key];
                return (
                  <li key={key}>
                    <div className="flex justify-between text-xs">
                      <span>
                        {label}{" "}
                        {(key === "traffic" || key === "importance") && shown.road_data_source && ROAD_SOURCE[shown.road_data_source] &&
                          <SourceBadge {...ROAD_SOURCE[shown.road_data_source][key]} />}
                      </span>
                      <span>{b.value.toFixed(2)} × {b.weight.toFixed(2)} = <b>{b.contribution.toFixed(3)}</b></span>
                    </div>
                    <div className="mt-1 h-2.5 rounded-sm bg-background" aria-hidden>
                      <div className="h-2.5 rounded-sm bg-primary" style={{ width: `${b.value * 100}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
            <p className="mt-2 text-xs text-muted">{THRESHOLD_NOTE}</p>
          </section>

          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <dt className="text-muted">Road</dt><dd>{shown.road_name ?? "unknown"} ({shown.road_type})</dd>
            <dt className="text-muted">Seen</dt><dd>{shown.detection_count}× · returned after repair {shown.recurrence_count}×</dd>
            <dt className="text-muted">First detected</dt><dd>{new Date(shown.first_detected_at).toLocaleString()}</dd>
            <dt className="text-muted">Last detected</dt><dd>{new Date(shown.last_detected_at).toLocaleString()}</dd>
            <dt className="text-muted">Nearest facility</dt>
            <dd>{shown.nearest_facility ? `${shown.nearest_facility}, ${Math.round(shown.nearest_facility_m!)} m (OpenStreetMap)` : "none within 2.5 km"}</dd>
            <dt className="text-muted">Zone</dt><dd>{shown.zone_id ?? "none yet"}</dd>
          </dl>

          <StatusButtons potholeId={shown.pothole_id} status={shown.status} onChanged={() => { setVersion((v) => v + 1); onChanged(); }} />
        </>
      )}
    </aside>
  );
}
