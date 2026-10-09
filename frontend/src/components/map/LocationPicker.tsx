"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { DEFAULT_CENTER } from "./PotholeMap";

/** The map can be created before its box has its final size; re-measure whenever the box changes. */
function TrackSize() {
  const map = useMap();
  useEffect(() => {
    const ro = new ResizeObserver(() => map.invalidateSize());
    ro.observe(map.getContainer());
    return () => ro.disconnect();
  }, [map]);
  return null;
}

function ClickToPick({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e: L.LeafletMouseEvent) => onPick(e.latlng.lat, e.latlng.lng) });
  return null;
}

/** Small map on the Upload page: click to set the photo's location. */
export default function LocationPicker({ value, onPick }: {
  value: [number, number] | null;
  onPick: (lat: number, lng: number) => void;
}) {
  return (
    // scrollWheelZoom off: on a form, scrolling the page over the map should scroll the page
    <MapContainer center={value ?? DEFAULT_CENTER} zoom={14} scrollWheelZoom={false} className="h-56 w-full rounded-lg">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <TrackSize />
      <ClickToPick onPick={onPick} />
      {value && <CircleMarker center={value} radius={8} pathOptions={{ color: "#1f3864", fillOpacity: 0.8 }} />}
    </MapContainer>
  );
}
