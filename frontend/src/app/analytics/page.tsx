"use client";

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import BarWithTable from "@/components/charts/BarWithTable";
import PageHeader from "@/components/ui/PageHeader";
import { labelClass } from "@/components/ui/styles";
import { apiFetch } from "@/lib/api";
import { COLORS } from "@/lib/colors";

interface Summary {
  by_status: { status: string; n: number }[];
  by_severity: { severity_level: string; n: number }[];
  top_roads: { name: string; pending: number; total_priority: number }[];
  hotspots: { pothole_id: number; road_name: string | null; repeat_count: number }[];
  avg_days_to_repair: number | null;
  done_by_crew: { name: string; done: number }[];
}

export default function AnalyticsPage() {
  const [s, setS] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Summary>("/analytics/summary").then(setS).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader icon={BarChart3} tone="emerald" title="Road condition analytics"
        subtitle="What is open, how bad it is, where it keeps coming back, and how fast crews close it." />
      {error && <p role="alert" className="font-semibold text-critical">{error}</p>}
      {!s && !error && <p className="text-muted">Loading…</p>}
      {s && (
        <>
          <div className="flex flex-wrap gap-4">
            <p className="rounded-lg bg-surface px-6 py-4">
              <span className={`block ${labelClass}`}>Average days from detection to repair</span>
              <span className="text-4xl font-extrabold text-primary">{s.avg_days_to_repair ?? "–"}</span>
            </p>
            {s.done_by_crew.map((c) => (
              <p key={c.name} className="rounded-lg bg-surface px-6 py-4">
                <span className={`block ${labelClass}`}>Repairs done by {c.name}</span>
                <span className="text-4xl font-extrabold">{c.done}</span>
              </p>
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <BarWithTable title="Potholes by status" valueLabel="Potholes"
              labels={s.by_status.map((r) => r.status)} values={s.by_status.map((r) => r.n)} />
            <BarWithTable title="Open potholes by relative severity" valueLabel="Potholes"
              labels={s.by_severity.map((r) => r.severity_level)} values={s.by_severity.map((r) => r.n)}
              colors={[COLORS.critical, COLORS.moderate, COLORS.low]} />
            <BarWithTable title="Top roads by pending priority" valueLabel="Total priority" horizontal
              labels={s.top_roads.map((r) => `${r.name} (${r.pending})`)} values={s.top_roads.map((r) => r.total_priority)} />
            <BarWithTable title="Repeat-damage hotspots" valueLabel="Times seen again" horizontal
              labels={s.hotspots.map((h) => `#${h.pothole_id} ${h.road_name ?? ""}`)} values={s.hotspots.map((h) => h.repeat_count)} />
          </div>
        </>
      )}
    </div>
  );
}
