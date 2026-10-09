"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PotholeMap } from "@/components/map";
import { RefreshCw, Route } from "lucide-react";
import CrewsPanel from "@/components/plan/CrewsPanel";
import Button, { buttonClass } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { cardClass, fieldClass, focusRing, labelClass } from "@/components/ui/styles";
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
  const [highlight, setHighlight] = useState<number | null>(null);

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
  const field = `${fieldClass} mt-1`;

  return (
    <div className="flex flex-col gap-6">
    <PageHeader icon={Route} title="Zones and repair plan"
      subtitle="Each day the most urgent potholes are repaired; nearby ones are grouped into zones so crews drive less." />
    <div className="flex flex-col gap-4 lg:h-[75vh] lg:flex-row">
      <section aria-label="Zones map" className="h-[50vh] flex-1 rounded-xl p-2 shadow-recessed lg:h-auto">
        <PotholeMap potholes={potholes} zones={zones} selectedId={null} highlightZone={highlight} />
      </section>

      <div className={`flex flex-col gap-6 overflow-y-auto ${cardClass} lg:w-[28rem]`}>
        {error && <p role="alert" className="font-semibold text-critical-text">{error}</p>}

        <section aria-label="Zones" className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Zones</h2>
            <Button variant="outline" size="sm" disabled={busy}
              onClick={() => act(async () => { await apiFetch("/zones/recompute", { method: "POST" }); })}>
              <RefreshCw aria-hidden size={16} strokeWidth={2.5} /> Recompute
            </Button>
          </div>
          <p className="text-sm text-muted">
            {lastRecompute ? `Last recomputed ${lastRecompute.toLocaleString()}.` : "Not computed yet."}<br />Open potholes
            close to each other (ZONE_EPS_M in config, straight-line distance) share a zone.
          </p>
          {zones.length > 0 && (
            <table className="w-full text-left text-sm">
              <thead className={labelClass}><tr><th className="py-1">Zone</th><th>Potholes</th><th>Avg priority</th></tr></thead>
              <tbody>
                {zones.map((z) => (
                  <tr key={z.zone_id}
                    className={`cursor-pointer border-t border-border hover:bg-background ${highlight === z.zone_id ? "bg-primary/10 font-bold" : ""}`}
                    onClick={() => setHighlight(highlight === z.zone_id ? null : z.zone_id)}>
                    <td className="py-1">
                      <button type="button" className={`font-[inherit] ${focusRing}`} aria-pressed={highlight === z.zone_id}
                        onClick={(e) => { e.stopPropagation(); setHighlight(highlight === z.zone_id ? null : z.zone_id); }}>
                        Zone {z.zone_id}
                      </button>
                    </td><td>{z.pothole_count}</td><td>{z.avg_priority.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section aria-label="Repair plan" className="flex flex-col gap-2">
          <h2 className="text-xl font-bold">Repair plan</h2>
          <div className="flex flex-wrap items-end gap-3">
            <label className={labelClass}>Days
              <input type="number" min={1} max={60} value={days} onChange={(e) => setDays(e.target.value)}
                className={`${field} w-20`} />
            </label>
            <label className={labelClass}>Start date (optional)
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                className={field} />
            </label>
            <Button disabled={busy}
              onClick={() => act(async () => {
                setPlan(await apiFetch<PlanResult>("/plan", json("POST", { days: Number(days), start_date: startDate || null })));
              })}>
              {busy ? "Working…" : "Generate plan"}
            </Button>
          </div>
          <p className="text-sm text-muted">Replanning is safe: scheduled potholes are reset and planned again; In Progress ones are left alone.</p>

          {plan && (
            <>
              <p role="status" className="text-lg font-bold">{plan.message}</p>
              {plan.unscheduled_count > 0 && (
                <p role="alert" className="rounded-md bg-moderate px-4 py-3 font-semibold text-foreground">
                  {plan.unscheduled_count} pothole(s) didn&apos;t fit in the plan: {plan.unscheduled_ids.map((i) => `#${i}`).join(", ")}
                </p>
              )}
              {[...byCrew.entries()].map(([crew, stops]) => (
                <div key={crew} className="rounded-lg bg-background p-4 shadow-recessed">
                  <h3 className="text-lg font-bold">{crew}</h3>
                  <ol className="mt-1 space-y-1 text-sm">
                    {stops.map((s, i) => (
                      <li key={s.pothole_id}>
                        {(i === 0 || stops[i - 1].planned_date !== s.planned_date) && (
                          <p className={`mt-3 ${labelClass}`}>{new Date(s.planned_date + "T00:00").toDateString()}</p>
                        )}
                        <span className="inline-block w-6 font-semibold">{s.sequence_no}.</span>
                        Pothole #{s.pothole_id} · {s.road_name ?? "unknown road"} · zone {s.zone_id} · <BandChip band={s.priority_band} />
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
              {plan.scheduled.length > 0 && <Link href="/repairs" className={buttonClass("outline", "md", "self-start")}>Open Repairs</Link>}
            </>
          )}
        </section>

        <CrewsPanel crews={crews} onChanged={() => setVersion((v) => v + 1)} />
      </div>
    </div>
    </div>
  );
}
