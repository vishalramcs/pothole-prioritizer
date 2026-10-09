"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PotholeMap } from "@/components/map";
import PotholeDetail from "@/components/panels/PotholeDetail";
import { BandChip } from "@/components/ui/chips";
import { fieldClass } from "@/components/ui/styles";
import { apiFetch } from "@/lib/api";
import { BANDS, STATUSES, type Pothole } from "@/lib/types";

const OPEN = "open";
// Big stat numbers on the dark panel (orange is readable on dark, 7.3:1; the "fill only" rule is for white)
const BAND_NUMBER: Record<string, string> = { Critical: "text-critical-on-dark", Moderate: "text-moderate", Low: "text-low-on-dark" };

export default function MapDashboardPage() {
  const [statusFilter, setStatusFilter] = useState<string>(OPEN);
  const [bandFilter, setBandFilter] = useState<string>("");
  const [zoneFilter, setZoneFilter] = useState<string>("");
  const [all, setAll] = useState<Pothole[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let alive = true;
    apiFetch<Pothole[]>("/potholes")
      .then((d) => alive && (setAll(d), setError(null)))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [version]);

  const shown = (all ?? []).filter((p) =>
    (statusFilter === OPEN ? p.status !== "Repaired" : !statusFilter || p.status === statusFilter)
    && (!bandFilter || p.priority_band === bandFilter)
    && (!zoneFilter || String(p.zone_id) === zoneFilter));
  const zones = [...new Set((all ?? []).map((p) => p.zone_id).filter((z) => z !== null))].sort((a, b) => a! - b!);

  const select = `${fieldClass} mt-1 w-full`;
  const label = "text-xs font-semibold uppercase tracking-wider text-white/80";
  const count = (b: string) => shown.filter((p) => p.priority_band === b).length;
  return (
    <div className="flex flex-col gap-4 lg:h-[calc(100vh-7.5rem)] lg:flex-row">
      <aside aria-label="Filters" className="relative flex shrink-0 flex-col gap-4 overflow-hidden rounded-lg bg-foreground p-5 text-white lg:w-64">
        <div aria-hidden className="absolute -right-12 -top-12 h-40 w-40 rounded-full bg-primary-bright opacity-20" />
        <h1 className="relative text-3xl font-extrabold leading-tight">Repair priority map</h1>
        <dl className="relative grid grid-cols-3 gap-2 text-center">
          {BANDS.map((b) => (
            <div key={b} className="rounded-md bg-white/10 px-1 py-2">
              <dt className="text-[11px] font-semibold uppercase tracking-wider text-white/80">{b}</dt>
              <dd className={`text-3xl font-extrabold ${BAND_NUMBER[b]}`}>{count(b)}</dd>
            </div>
          ))}
        </dl>
        <label className={label}>Status
          <select className={select} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value={OPEN}>Open (not repaired)</option>
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label className={label}>Priority band
          <select className={select} value={bandFilter} onChange={(e) => setBandFilter(e.target.value)}>
            <option value="">All</option>
            {BANDS.map((b) => <option key={b}>{b}</option>)}
          </select>
        </label>
        <label className={label}>Zone
          <select className={select} value={zoneFilter} onChange={(e) => setZoneFilter(e.target.value)}>
            <option value="">All</option>
            {zones.map((z) => <option key={z} value={String(z)}>Zone {z}</option>)}
          </select>
        </label>
        <div className="text-sm">
          <p className={label}>Legend</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {BANDS.map((b) => <li key={b}><BandChip band={b} /></li>)}
          </ul>
          <p className="mt-2 text-white/80">Bigger marker = higher score · hollow = repaired</p>
        </div>
        <p className="mt-auto text-sm text-white/80">
          {shown.length} of {all?.length ?? 0} potholes shown
          {shown.some((p) => p.is_demo) && <> · includes {shown.filter((p) => p.is_demo).length} <b className="text-white">demo data</b> potholes</>}
        </p>
      </aside>

      <section aria-label="Map" className="relative h-[60vh] flex-1 lg:h-auto">
        {error && <p role="alert" className="rounded-lg bg-surface p-4 font-semibold text-critical">{error}</p>}
        {all && all.length === 0 && (
          <p className="absolute left-1/2 top-4 z-[1000] -translate-x-1/2 rounded-md bg-foreground px-4 py-3 font-semibold text-white">
            No potholes yet. <Link className="underline decoration-2 underline-offset-4" href="/upload">Upload an image</Link> or load demo data.
          </p>
        )}
        {!error && <PotholeMap potholes={shown} selectedId={selected} onSelect={setSelected} />}
      </section>

      {selected !== null && (
        <div className="lg:w-96">
          <PotholeDetail id={selected} onClose={() => setSelected(null)} onChanged={() => setVersion((v) => v + 1)} />
        </div>
      )}
    </div>
  );
}
