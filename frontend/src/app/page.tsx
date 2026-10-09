"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PotholeMap } from "@/components/map";
import PotholeDetail from "@/components/panels/PotholeDetail";
import { BandChip } from "@/components/ui/chips";
import { apiFetch } from "@/lib/api";
import { BANDS, STATUSES, type Pothole } from "@/lib/types";

const OPEN = "open";

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

  const select = "mt-1 w-full rounded border border-muted bg-surface px-2 py-1.5";
  return (
    <div className="flex flex-col gap-4 lg:h-[calc(100vh-7.5rem)] lg:flex-row">
      <aside aria-label="Filters" className="flex shrink-0 flex-col gap-3 rounded-lg bg-surface p-4 shadow lg:w-56">
        <h1 className="text-xl font-semibold">Repair priority map</h1>
        <label className="text-xs text-muted">Status
          <select className={select} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value={OPEN}>Open (not repaired)</option>
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label className="text-xs text-muted">Priority band
          <select className={select} value={bandFilter} onChange={(e) => setBandFilter(e.target.value)}>
            <option value="">All</option>
            {BANDS.map((b) => <option key={b}>{b}</option>)}
          </select>
        </label>
        <label className="text-xs text-muted">Zone
          <select className={select} value={zoneFilter} onChange={(e) => setZoneFilter(e.target.value)}>
            <option value="">All</option>
            {zones.map((z) => <option key={z} value={String(z)}>Zone {z}</option>)}
          </select>
        </label>
        <div className="text-xs">
          <p className="font-semibold text-muted">Legend</p>
          <ul className="mt-1 space-y-1">
            {BANDS.map((b) => <li key={b}><BandChip band={b} /></li>)}
            <li className="text-muted">Bigger marker = higher score · hollow = repaired</li>
          </ul>
        </div>
        <p className="mt-auto text-xs text-muted">{shown.length} of {all?.length ?? 0} potholes shown</p>
      </aside>

      <section aria-label="Map" className="relative h-[60vh] flex-1 lg:h-auto">
        {error && <p role="alert" className="rounded bg-surface p-4 text-critical">{error}</p>}
        {all && all.length === 0 && (
          <p className="absolute left-1/2 top-4 z-[1000] -translate-x-1/2 rounded bg-surface px-4 py-2 shadow">
            No potholes yet. <Link className="text-brand underline" href="/upload">Upload an image</Link> or load demo data.
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
