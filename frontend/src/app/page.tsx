"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PotholeMap } from "@/components/map";
import PotholeDetail from "@/components/panels/PotholeDetail";
import { BandChip } from "@/components/ui/chips";
import { VentSlots } from "@/components/ui/parts";
import { fieldClass, focusRing } from "@/components/ui/styles";
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
      .then((d) => {
        if (!alive) return;
        setAll(d);
        setError(null);
        if (version === 0) { // "View on map" links from Repairs open that pothole's panel: /?pothole=12
          const id = Number(new URLSearchParams(window.location.search).get("pothole"));
          if (id) setSelected(id);
        }
      })
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [version]);

  const shown = (all ?? []).filter((p) =>
    (statusFilter === OPEN ? p.status !== "Repaired" : !statusFilter || p.status === statusFilter)
    && (!bandFilter || p.priority_band === bandFilter)
    && (!zoneFilter || String(p.zone_id) === zoneFilter));
  const zones = [...new Set((all ?? []).map((p) => p.zone_id).filter((z) => z !== null))].sort((a, b) => a! - b!);

  const select = `${fieldClass} mt-1 w-full`;
  const label = "font-mono text-xs font-bold uppercase tracking-[0.08em] text-white/80";
  const count = (b: string) => shown.filter((p) => p.priority_band === b).length;
  const open = (all ?? []).filter((p) => p.status !== "Repaired");
  const fixFirst = [...open].sort((a, b) => b.priority_score - a.priority_score).slice(0, 3);
  return (
    <div className="flex flex-col gap-4 lg:h-[calc(100vh-8.5rem)] lg:flex-row">
      <aside aria-label="Filters" className="relative flex shrink-0 flex-col gap-4 overflow-x-hidden overflow-y-auto carbon rounded-xl bg-foreground p-5 text-white shadow-card lg:w-64">
        <VentSlots dark className="absolute right-5 top-5" />
        <h1 className="relative pr-8 text-3xl font-extrabold leading-tight drop-shadow-[0_2px_4px_rgba(0,0,0,0.3)]">Repair priority map</h1>
        <dl className="relative grid grid-cols-3 gap-2 text-center">
          {BANDS.map((b) => (
            <div key={b} className="rounded-md bg-black/30 px-1 py-2 shadow-[inset_2px_2px_4px_rgba(0,0,0,0.5)]">
              <dt className="font-mono text-[11px] font-bold uppercase tracking-[0.05em] text-white/80">{b}</dt>
              <dd className={`font-mono text-3xl font-bold ${BAND_NUMBER[b]}`}>{count(b)}</dd>
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
            {BANDS.map((b) => (
              <li key={b}>
                <button type="button" aria-pressed={bandFilter === b} title={`Show only ${b}`}
                  onClick={() => setBandFilter(bandFilter === b ? "" : b)}
                  className={`rounded-md ${focusRing} ${bandFilter && bandFilter !== b ? "opacity-40" : ""}`}>
                  <BandChip band={b} />
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-white/80">Click a band to filter · bigger marker = higher score · hollow = repaired</p>
        </div>
        {fixFirst.length > 0 && (
          <div className="text-sm">
            <p className={label}>Fix first</p>
            <p className="mt-1 text-white/80">{open.length} open · {open.filter((p) => p.priority_band === "Critical").length} Critical</p>
            <ol className="mt-2 flex flex-col gap-1">
              {fixFirst.map((p, i) => (
                <li key={p.pothole_id}>
                  <button type="button" onClick={() => setSelected(p.pothole_id)}
                    className={`w-full rounded-md bg-white/10 px-2 py-1.5 text-left transition-colors duration-150 hover:bg-white/20 ${focusRing}`}>
                    <span className="font-bold">{i + 1}. #{p.pothole_id}</span> <span className="font-mono">{p.priority_score.toFixed(2)}</span>
                    <span className="block truncate text-white/80">{p.road_name ?? "unknown road"}</span>
                  </button>
                </li>
              ))}
            </ol>
          </div>
        )}
        <p className="mt-auto text-sm text-white/80">
          {shown.length} of {all?.length ?? 0} potholes shown
          {shown.some((p) => p.is_demo) && <> · includes {shown.filter((p) => p.is_demo).length} <b className="text-white">demo data</b> potholes</>}
        </p>
      </aside>

      <section aria-label="Map" className="relative h-[60vh] flex-1 rounded-xl p-2 shadow-recessed lg:h-auto">
        {error && <p role="alert" className="rounded-lg bg-background p-4 font-semibold text-critical-text shadow-card">{error}</p>}
        {all && all.length === 0 && (
          <p className="absolute left-1/2 top-4 z-[1000] -translate-x-1/2 rounded-md bg-foreground px-4 py-3 font-semibold text-white shadow-sharp">
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
