"use client";

// Leaflet touches `window`, so the maps load in the browser only (design brief 12).
import dynamic from "next/dynamic";

const loading = () => <p className="p-4 text-muted">Loading map…</p>;

export const PotholeMap = dynamic(() => import("./PotholeMap"), { ssr: false, loading });
export const LocationPicker = dynamic(() => import("./LocationPicker"), { ssr: false, loading });
