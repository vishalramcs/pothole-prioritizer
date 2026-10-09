"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useEffect, useRef } from "react";
import { Circle, MapContainer, Marker, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import type { Band, Pothole, Zone } from "@/lib/types";

const COLOR: Record<Band, string> = { Critical: "#c62828", Moderate: "#ef8f00", Low: "#2e7d32" };
export const DEFAULT_CENTER: [number, number] = [12.9716, 77.5946];

/** Circle marker: colour = band, size = score, hollow = repaired, "!" = Critical, white outline (design brief 6). */
function markerIcon(p: Pothole, selected: boolean): L.DivIcon {
  const size = Math.round(16 + p.priority_score * 20);
  const repaired = p.status === "Repaired";
  const style = [
    `width:${size}px`, `height:${size}px`, "border-radius:50%",
    `background:${repaired ? "rgba(255,255,255,.6)" : COLOR[p.priority_band]}`,
    `border:${repaired ? "3px solid #6b7785" : "2px solid #fff"}`,
    selected ? "box-shadow:0 0 0 3px #1f3864" : "box-shadow:0 1px 3px rgba(0,0,0,.45)",
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

export default function PotholeMap({ potholes, selectedId, onSelect, zones = [] }: {
  potholes: Pothole[];
  selectedId: number | null;
  onSelect: (id: number | null) => void;
  zones?: Zone[];
}) {
  const positions = spread(potholes);
  return (
    <MapContainer center={DEFAULT_CENTER} zoom={13} className="h-full w-full rounded-lg">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitOnce points={[...positions.values()]} />
      <KeepInView target={selectedId === null ? null : positions.get(selectedId) ?? null} />
      <ClickAway onClick={() => onSelect(null)} />
      {zones.map((z) => (
        <Circle
          key={z.zone_id}
          center={[z.centroid_lat, z.centroid_lng]}
          radius={Math.max(40, z.radius_m + 25)}
          pathOptions={{ color: "#1f3864", weight: 1, fillOpacity: 0.08 }}
        >
          <Tooltip>{`Zone ${z.zone_id}: ${z.pothole_count} potholes, avg priority ${z.avg_priority.toFixed(2)}`}</Tooltip>
        </Circle>
      ))}
      {potholes.map((p) => (
        <Marker
          key={p.pothole_id}
          position={positions.get(p.pothole_id)!}
          icon={markerIcon(p, p.pothole_id === selectedId)}
          title={`Pothole ${p.pothole_id}: ${p.priority_band} priority ${p.priority_score.toFixed(2)}, ${p.status}`}
          alt={`Pothole ${p.pothole_id}, ${p.priority_band}`}
          eventHandlers={{ click: () => onSelect(p.pothole_id) }}
        />
      ))}
    </MapContainer>
  );
}
