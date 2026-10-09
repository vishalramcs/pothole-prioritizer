// The design tokens from app/globals.css, for places that need a colour string in JavaScript
// (Leaflet markers, Chart.js bars, boxes drawn over photos). Keep the two in sync.
import type { Band, SeverityLevel } from "./types";

export const COLORS = {
  primary: "#2563eb",
  ink: "#111827",
  white: "#ffffff",
  repaired: "#6b7785",
  critical: "#c62828",
  moderate: "#ef8f00",
  moderateText: "#9a4a00",
  low: "#2e7d32",
} as const;

export const BAND_COLOR: Record<Band, string> = { Critical: COLORS.critical, Moderate: COLORS.moderate, Low: COLORS.low };

// Box outlines on photos: the darker orange so a thin line stays visible
export const SEVERITY_COLOR: Record<SeverityLevel, string> = {
  High: COLORS.critical, Medium: COLORS.moderateText, Low: COLORS.low,
};
