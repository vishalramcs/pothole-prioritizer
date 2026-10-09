import type { Band, SeverityLevel } from "@/lib/types";

// Design brief section 5: orange is a fill only, with dark text on it (6.8:1).
const BAND_CLASS: Record<Band, string> = {
  Critical: "bg-critical text-white",
  Moderate: "bg-moderate text-foreground",
  Low: "bg-low text-white",
};

const SEVERITY_CLASS: Record<SeverityLevel, string> = {
  High: "bg-critical text-white",
  Medium: "bg-moderate text-foreground",
  Low: "bg-low text-white",
};

export function BandChip({ band }: { band: Band }) {
  return (
    <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-bold uppercase tracking-wider ${BAND_CLASS[band]}`}>
      {band === "Critical" ? "! " : ""}
      {band}
    </span>
  );
}

export function SeverityChip({ level }: { level: SeverityLevel }) {
  return <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-bold uppercase tracking-wider ${SEVERITY_CLASS[level]}`}>{level}</span>;
}

/** Where a value comes from, shown next to it (e.g. "OSM road class", "estimated from road type"). */
export function SourceBadge({ text, title }: { text: string; title: string }) {
  return (
    <span className="ml-1 rounded-sm bg-background px-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted" title={title}>
      {text}
    </span>
  );
}

// For roads from OpenStreetMap: importance is the real road class, traffic is an estimate from it.
export const ROAD_SOURCE: Record<string, Record<"traffic" | "importance", { text: string; title: string }>> = {
  osm_estimate: {
    importance: { text: "OSM road class", title: "From the road's class on OpenStreetMap" },
    traffic: { text: "estimated from road type", title: "Estimated from the OpenStreetMap road class and lane count; no live traffic counts" },
  },
  mock: {
    importance: { text: "demo data", title: "Mock value" },
    traffic: { text: "demo data", title: "Mock value, not real traffic data" },
  },
};

export const THRESHOLD_NOTE =
  "Demo thresholds and weights, not validated standards. Severity is a relative estimate from the image, not measured depth.";
