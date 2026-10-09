"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PotholeMap } from "@/components/map";
import CrewsPanel from "@/components/plan/CrewsPanel";
import { BandChip } from "@/components/ui/chips";
import { apiFetch, json } from "@/lib/api";
import type { Crew, PlannedStop, PlanResult, Pothole, Zone } from "@/lib/types";

export default function ZonesPlanPage() {
  const [potholes, setPotholes] = useState<Pothole[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [crews, setCrews] = useState<Crew[]>([]);
  const [days, setDays] = useState("3");
  const [startDate, setStartDate] = useState("");
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let alive = true;
    Promise.all([apiFetch<Pothole[]>("/potholes"), apiFetch<Zone[]>("/zones"), apiFetch<Crew[]>("/crews")])
      .then(([p, z, c]) => alive && (setPotholes(p.filter((x) => x.status !== "Repaired")), setZones(z), setCrews(c)))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [version]);

  async function act(run: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await run();
      setVersion((v) => v + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const lastRecompute = zones.length ? new Date(Math.max(...zones.map((z) => Date.parse(z.created_at)))) : null;
  const byCrew = new Map<string, PlannedStop[]>();
  for (const s of plan?.scheduled ?? []) byCrew.set(s.crew_name, [...(byCrew.get(s.crew_name) ?? []), s]);
  const button = "min-h-10 rounded bg-brand px-4 py-2 font-semibold text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:opacity-50";

  return (
    <div className="flex flex-col gap-4 lg:h-[calc(100vh-7.5rem)] lg:flex-row">
      <section aria-label="Zones map" className="h-[50vh] flex-1 lg:h-auto">
        <PotholeMap potholes={potholes} zones={zones} selectedId={null} onSelect={() => {}} />
      </section>

      <div className="flex flex-col gap-5 overflow-y-auto rounded-lg bg-surface p-4 shadow lg:w-[28rem]">
        <h1 className="text-[28px] font-semibold">Zones and plan</h1>
        {error && <p role="alert" className="text-critical">{error}</p>}

        <section aria-label="Zones" className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Zones</h2>
            <button type="button" className={button} disabled={busy}
              onClick={() => act(async () => { await apiFetch("/zones/recompute", { method: "POST" }); })}>
              Recompute zones
            </button>
          </div>
          <p className="text-xs text-muted">
            {lastRecompute ? `Last recomputed ${lastRecompute.toLocaleString()}` : "Not computed yet."} Open potholes
            close to each other (ZONE_EPS_M in config, straight-line distance) share a zone.
          </p>
          {zones.length > 0 && (
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-muted"><tr><th>Zone</th><th>Potholes</th><th>Avg priority</th></tr></thead>
              <tbody>
                {zones.map((z) => (
                  <tr key={z.zone_id} className="border-t border-background">
                    <td className="py-1">Zone {z.zone_id}</td><td>{z.pothole_count}</td><td>{z.avg_priority.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <CrewsPanel crews={crews} onChanged={() => setVersion((v) => v + 1)} />

        <section aria-label="Repair plan" className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">Repair plan</h2>
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-muted">Days
              <input type="number" min={1} max={60} value={days} onChange={(e) => setDays(e.target.value)}
                className="mt-1 block w-20 rounded border border-muted bg-surface px-2 py-1 text-foreground" />
            </label>
            <label className="text-xs text-muted">Start date (optional)
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                className="mt-1 block rounded border border-muted bg-surface px-2 py-1 text-foreground" />
            </label>
            <button type="button" className={button} disabled={busy}
              onClick={() => act(async () => {
                setPlan(await apiFetch<PlanResult>("/plan", json("POST", { days: Number(days), start_date: startDate || null })));
              })}>
              {busy ? "Working…" : "Generate plan"}
            </button>
          </div>
          <p className="text-xs text-muted">Replanning is safe: scheduled potholes are reset and planned again; In Progress ones are left alone.</p>

          {plan && (
            <>
              <p role="status" className="font-medium">{plan.message}</p>
              {plan.unscheduled_count > 0 && (
                <p role="alert" className="rounded bg-moderate px-3 py-2 text-foreground">
                  {plan.unscheduled_count} pothole(s) didn&apos;t fit in the plan: {plan.unscheduled_ids.map((i) => `#${i}`).join(", ")}
                </p>
              )}
              {[...byCrew.entries()].map(([crew, stops]) => (
                <div key={crew} className="rounded border border-background p-3">
                  <h3 className="font-semibold">{crew}</h3>
                  <ol className="mt-1 space-y-1 text-sm">
                    {stops.map((s, i) => (
                      <li key={s.pothole_id}>
                        {(i === 0 || stops[i - 1].planned_date !== s.planned_date) && (
                          <p className="mt-2 text-xs font-semibold text-muted">{new Date(s.planned_date + "T00:00").toDateString()}</p>
                        )}
                        <span className="inline-block w-6 font-semibold">{s.sequence_no}.</span>
                        Pothole #{s.pothole_id} · {s.road_name ?? "unknown road"} · zone {s.zone_id} · <BandChip band={s.priority_band} />
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
              {plan.scheduled.length > 0 && <Link href="/repairs" className="text-brand underline">Open Repairs</Link>}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
