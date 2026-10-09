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
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${BAND_CLASS[band]}`}>
      {band === "Critical" ? "! " : ""}
      {band}
    </span>
  );
}

export function SeverityChip({ level }: { level: SeverityLevel }) {
  return <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${SEVERITY_CLASS[level]}`}>{level}</span>;
}

export function DemoBadge() {
  return (
    <span className="ml-1 rounded border border-muted px-1 text-[11px] text-muted" title="Mock values, not real traffic data">
      demo data
    </span>
  );
}

export const THRESHOLD_NOTE =
  "Demo thresholds and weights, not validated standards. Severity is a relative estimate from the image, not measured depth.";
