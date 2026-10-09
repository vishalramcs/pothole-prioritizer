"use client";

import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import L from "leaflet";
import "leaflet.markercluster";
import { createLayerComponent } from "@react-leaflet/core";
import { useEffect, useRef } from "react";
import { Circle, Marker, Popup, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import { BandChip } from "@/components/ui/chips";
import { linkClass } from "@/components/ui/styles";
import { BAND_COLOR, COLORS } from "@/lib/colors";
import type { Pothole, Zone } from "@/lib/types";
import LiveMap from "./LiveMap";

export const DEFAULT_CENTER: [number, number] = [12.9716, 77.5946];

/** Circle marker: colour = band, size = score, hollow = repaired, "!" = Critical, white outline (design brief 6). */
function markerIcon(p: Pothole, selected: boolean): L.DivIcon {
  const size = Math.round(16 + p.priority_score * 20);
  const repaired = p.status === "Repaired";
  const style = [
    `width:${size}px`, `height:${size}px`, "border-radius:50%",
    `background:${repaired ? "rgba(255,255,255,.6)" : BAND_COLOR[p.priority_band]}`,
    `border:${repaired ? `3px solid ${COLORS.repaired}` : `2px solid ${COLORS.white}`}`,
    selected ? `outline:3px solid ${COLORS.ink};outline-offset:2px` : "", // flat: no shadow, a solid ring when selected
    "display:flex", "align-items:center", "justify-content:center",
    `color:#fff;font:700 ${Math.round(size * 0.6)}px system-ui`,
  ].join(";");
  const label = p.priority_band === "Critical" && !repaired ? "!" : "";
  return L.divIcon({ className: "", iconSize: [size, size], html: `<div style="${style}">${label}</div>` });
}

/** Potholes from one photo share a point; nudge duplicates ~1.5 m apart so each stays clickable (display only). */
function spread(potholes: Pothole[]): Map<number, [number, number]> {
  const seen = new Map<string, number>();
  const out = new Map<number, [number, number]>();
  for (const p of potholes) {
    const key = `${p.lat},${p.lng}`;
    const k = seen.get(key) ?? 0;
    seen.set(key, k + 1);
    const angle = k * 2.4; // golden-angle-ish spiral
    const r = k === 0 ? 0 : 1.5 * Math.sqrt(k) / 111_320;
    out.set(p.pothole_id, [p.lat + r * Math.cos(angle), p.lng + (r * Math.sin(angle)) / Math.cos((p.lat * Math.PI) / 180)]);
  }
  return out;
}

/** Groups nearby markers; children are only the filtered potholes, so counts follow the filters. Neutral ink
 * bubbles (not markercluster's default green/yellow) so they never read as a priority band. */
const MarkerCluster = createLayerComponent<L.MarkerClusterGroup, { children: React.ReactNode }>(
  (_props, ctx) => {
    const instance = L.markerClusterGroup({
      showCoverageOnHover: false,
      maxClusterRadius: 40,
      iconCreateFunction: (c) => {
        const n = c.getChildCount();
        const size = n < 10 ? 34 : n < 100 ? 40 : 46;
        return L.divIcon({
          className: "", iconSize: [size, size],
          html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${COLORS.ink};border:3px solid ${COLORS.white};color:#fff;display:flex;align-items:center;justify-content:center;font:700 14px system-ui" aria-label="${n} potholes">${n}</div>`,
        });
      },
    });
    return { instance, context: { ...ctx, layerContainer: instance } };
  },
);

function FitOnce({ points }: { points: [number, number][] }) {
  const map = useMap();
  const done = useRef(false);
  useEffect(() => {
    if (done.current || points.length === 0) return;
    done.current = true;
    map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 17 });
  }, [map, points]);
  return null;
}

/** Opening the side panel narrows the map; Leaflet must be told, and the selected marker kept on screen. */
function KeepInView({ target }: { target: [number, number] | null }) {
  const map = useMap();
  const targetRef = useRef(target);
  useEffect(() => {
    targetRef.current = target;
    if (target && !map.getBounds().contains(target)) map.panTo(target);
  }, [map, target]);
  useEffect(() => {
    const ro = new ResizeObserver(() => {
      map.invalidateSize();
      const t = targetRef.current;
      if (t && !map.getBounds().contains(t)) map.panTo(t);
    });
    ro.observe(map.getContainer());
    return () => ro.disconnect();
  }, [map]);
  return null;
}

function ClickAway({ onClick }: { onClick: () => void }) {
  useMapEvents({ click: onClick });
  return null;
}

/** Bring the highlighted zone into view. */
function FlyToZone({ zone }: { zone: Zone | undefined }) {
  const map = useMap();
  useEffect(() => {
    if (zone) map.flyTo([zone.centroid_lat, zone.centroid_lng], Math.max(map.getZoom(), 16));
  }, [map, zone]);
  return null;
}

export default function PotholeMap({ potholes, selectedId, onSelect, zones = [], highlightZone = null }: {
  potholes: Pothole[];
  selectedId: number | null;
  onSelect?: (id: number | null) => void; // without it, popups have no "Why?" link (zones page)
  zones?: Zone[];
  highlightZone?: number | null;
}) {
  const positions = spread(potholes);
  return (
    <LiveMap center={DEFAULT_CENTER} zoom={13} className="h-full w-full rounded-lg">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitOnce points={[...positions.values()]} />
      <KeepInView target={selectedId === null ? null : positions.get(selectedId) ?? null} />
      {onSelect && <ClickAway onClick={() => onSelect(null)} />}
      <FlyToZone zone={zones.find((z) => z.zone_id === highlightZone)} />
      {zones.map((z) => (
        <Circle
          key={z.zone_id}
          center={[z.centroid_lat, z.centroid_lng]}
          radius={Math.max(40, z.radius_m + 25)}
          pathOptions={z.zone_id === highlightZone
            ? { color: COLORS.accent, weight: 4, fillOpacity: 0.2 }
            : { color: COLORS.ink, weight: 2, fillOpacity: 0.08, dashArray: "6 4" }}
        >
          <Tooltip>{`Zone ${z.zone_id}: ${z.pothole_count} potholes, avg priority ${z.avg_priority.toFixed(2)}`}</Tooltip>
        </Circle>
      ))}
      <MarkerCluster>
        {potholes.map((p) => (
          <Marker
            key={p.pothole_id}
            position={positions.get(p.pothole_id)!}
            icon={markerIcon(p, p.pothole_id === selectedId)}
            title={`Pothole ${p.pothole_id}: ${p.priority_band} priority ${p.priority_score.toFixed(2)}, ${p.status}`}
            alt={`Pothole ${p.pothole_id}, ${p.priority_band}`}
          >
            <Popup>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-sm">
                <dt className="font-semibold">Pothole</dt><dd>#{p.pothole_id}</dd>
                <dt className="font-semibold">Road</dt><dd>{p.road_name ?? "unknown"}</dd>
                <dt className="font-semibold">Score</dt><dd>{p.priority_score.toFixed(2)}</dd>
                <dt className="font-semibold">Band</dt><dd><BandChip band={p.priority_band} /></dd>
                <dt className="font-semibold">Status</dt><dd>{p.status}</dd>
              </dl>
              {onSelect && (
                <button type="button" onClick={() => onSelect(p.pothole_id)}
                  className={`mt-2 ${linkClass}`}>
                  Why? See the score breakdown
                </button>
              )}
            </Popup>
          </Marker>
        ))}
      </MarkerCluster>
    </LiveMap>
  );
}
