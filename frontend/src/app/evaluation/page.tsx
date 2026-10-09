"use client";

import { useEffect, useState } from "react";
import { Gauge } from "lucide-react";
import Button from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { fieldClass, labelClass } from "@/components/ui/styles";
import { apiFetch } from "@/lib/api";

interface StrategyResult {
  strategy: string;
  repaired: number;
  priority_addressed_pct: number;
  critical_fixed_pct: number | null;
  avg_days_critical: number | null;
  exposure: number;
  exposure_reduction_vs_fcfs_pct: number | null;
  travel_km: number;
}

interface Evaluation {
  open_potholes: number;
  critical_potholes: number;
  capacity_per_day: number;
  days: number;
  critical_within: number;
  top_n: number;
  strategies: StrategyResult[];
  sensitivity: { weight: string; change: string; top_n_overlap_pct: number | null; spearman: number }[];
}

const show = (v: number | null, unit = "") => (v === null ? "–" : `${v}${unit}`);

export default function EvaluationPage() {
  const [days, setDays] = useState("5");
  const [within, setWithin] = useState("2");
  const [query, setQuery] = useState({ days: "5", within: "2" });
  const [ev, setEv] = useState<Evaluation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    apiFetch<Evaluation>(`/evaluation?days=${query.days}&critical_within=${query.within}`)
      .then((d) => alive && (setEv(d), setError(null)))
      .catch((e) => alive && (setEv(null), setError(e.message)));
    return () => { alive = false; };
  }, [query]);

  const field = `${fieldClass} mt-1 w-24`;
  const stats: [string, number, string][] = ev ? [
    ["Open potholes", ev.open_potholes, "text-foreground"], ["Critical", ev.critical_potholes, "text-critical"],
    ["Repairs per day", ev.capacity_per_day, "text-primary"], ["Days planned", ev.days, "text-foreground"],
  ] : [];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader icon={Gauge} tone="ink" title="Is the prioritization working?"
        subtitle="SRPPS against simpler ways of ordering the same repairs, with the same crews and days." />
      <p className="max-w-3xl text-muted">
        Every strategy repairs the same open potholes with the same crews and the same number of repairs per day.
        Only the order differs. Nothing is saved: this is a simulation on the current data.
      </p>

      <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); setQuery({ days, within }); }}>
        <label className={labelClass}>Days to plan
          <input type="number" min={1} max={60} className={field} value={days} onChange={(e) => setDays(e.target.value)} />
        </label>
        <label className={labelClass}>Critical fixed within (days)
          <input type="number" min={1} max={60} className={field} value={within} onChange={(e) => setWithin(e.target.value)} />
        </label>
        <Button type="submit">Run evaluation</Button>
      </form>

      {error && <p role="alert" className="font-semibold text-critical">{error}</p>}
      {ev && (
        <>
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {stats.map(([k, v, c]) => (
              <div key={k} className="rounded-lg bg-surface px-6 py-4">
                <dt className={labelClass}>{k}</dt>
                <dd className={`text-4xl font-extrabold ${c}`}>{v}</dd>
              </div>
            ))}
          </dl>
          <div className="overflow-x-auto rounded-lg bg-surface p-6">
            <table className="w-full text-left text-sm">
              <caption className="mb-3 text-left text-xl font-bold">Strategies compared</caption>
              <thead className={labelClass}>
                <tr>
                  <th className="py-2">Strategy</th><th>Repaired</th><th>Priority addressed</th>
                  <th>Critical fixed within {ev.critical_within} d</th><th>Avg days to repair Critical</th>
                  <th>Road-user exposure</th><th>Exposure vs FCFS</th><th>Crew travel</th>
                </tr>
              </thead>
              <tbody>
                {ev.strategies.map((s) => (
                  <tr key={s.strategy} className={`border-t border-background ${s.strategy.startsWith("SRPPS") ? "bg-primary/10 font-bold" : ""}`}>
                    <td className="py-2">{s.strategy}</td>
                    <td>{s.repaired}</td>
                    <td>{s.priority_addressed_pct}%</td>
                    <td>{show(s.critical_fixed_pct, "%")}</td>
                    <td>{show(s.avg_days_critical)}</td>
                    <td>{s.exposure}</td>
                    <td>{s.exposure_reduction_vs_fcfs_pct === null ? "–" : `${s.exposure_reduction_vs_fcfs_pct > 0 ? "−" : "+"}${Math.abs(s.exposure_reduction_vs_fcfs_pct)}%`}</td>
                    <td>{s.travel_km} km</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-muted">
              <li>Priority addressed: share of the total priority score repaired within the plan.</li>
              <li>Average days to repair Critical: a Critical pothole not repaired in the plan counts as days + 1.</li>
              <li>Road-user exposure: sum of traffic × severity × days the pothole stays open (lower is better). It uses two
                of the priority&apos;s own inputs, so priority-based strategies are expected to do well on it.</li>
              <li>Crew travel: straight-line distance between consecutive repairs each day. &quot;Priority only&quot; uses the
                same ranking without zones, so the difference to SRPPS is what clustering saves.</li>
            </ul>
          </div>

          <div className="overflow-x-auto rounded-lg bg-surface p-6">
            <table className="w-full max-w-2xl text-left text-sm">
              <caption className="mb-3 text-left text-xl font-bold">How sensitive is the ranking to the weights?</caption>
              <thead className={labelClass}>
                <tr><th className="py-2">Weight</th><th>Change</th><th>Same top {ev.top_n}</th><th>Rank correlation (Spearman)</th></tr>
              </thead>
              <tbody>
                {ev.sensitivity.map((r) => (
                  <tr key={r.weight + r.change} className="border-t border-background">
                    <td className="py-1">{r.weight}</td><td>{r.change}</td><td>{show(r.top_n_overlap_pct, "%")}</td><td>{r.spearman}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-sm text-muted">
              One weight changed by ±20%, then all weights rescaled to sum to 1. High overlap and correlation mean the
              ranking does not hinge on the exact (assumed) weights.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
