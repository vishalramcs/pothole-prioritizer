"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Wrench } from "lucide-react";
import StatusButtons from "@/components/repairs/StatusButtons";
import PageHeader from "@/components/ui/PageHeader";
import { cardClass, focusRing, labelClass, linkClass } from "@/components/ui/styles";
import { BandChip } from "@/components/ui/chips";
import { apiFetch } from "@/lib/api";
import { STATUSES, type RepairRow, type Status } from "@/lib/types";

export default function RepairsPage() {
  const [tab, setTab] = useState<Status>("Pending");
  const [rows, setRows] = useState<RepairRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [counts, setCounts] = useState<Record<string, number> | null>(null);

  useEffect(() => {
    apiFetch<{ by_status: { status: string; n: number }[] }>("/analytics/summary")
      .then((s) => setCounts(Object.fromEntries(s.by_status.map((r) => [r.status, r.n]))))
      .catch(() => setCounts(null)); // counts are a nicety; the tabs still work without them
  }, [version]);

  useEffect(() => {
    let alive = true;
    apiFetch<RepairRow[]>(`/repairs?status=${encodeURIComponent(tab)}`)
      .then((d) => alive && (setRows(d), setError(null)))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [tab, version]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader icon={Wrench} title="Repairs"
        subtitle="Track every pothole from reported to repaired. Buttons only offer the changes the status rules allow." />
      <div role="tablist" aria-label="Repair status" className="flex flex-wrap gap-2">
        {STATUSES.map((s) => (
          <button key={s} role="tab" type="button" aria-selected={tab === s} onClick={() => { setTab(s); setRows(null); }}
            className={`min-h-12 rounded-lg bg-background px-5 font-bold transition-all duration-150 ease-mechanical ${focusRing} ${tab === s ? "text-primary shadow-pressed" : "text-foreground shadow-card hover:text-primary active:translate-y-[2px]"}`}>
            {s}{counts && <span className="font-mono">{` (${counts[s] ?? 0})`}</span>}
          </button>
        ))}
      </div>

      <div role="tabpanel" className={`overflow-x-auto ${cardClass}`}>
        {error && <p role="alert" className="text-critical-text">{error}</p>}
        {!rows && !error && <p className="text-muted">Loading…</p>}
        {rows?.length === 0 && <p className="text-muted">No potholes are {tab.toLowerCase()}.</p>}
        {rows && rows.length > 0 && (
          <table className="w-full text-left">
            <thead className={labelClass}>
              <tr>
                <th className="py-2">Pothole</th><th>Road</th><th>Priority</th><th>Zone</th><th>Crew</th>
                <th>{tab === "Repaired" ? "Repaired" : "Planned date"}</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.pothole_id} className="border-t border-border align-middle">
                  <td className="py-2">
                    #{r.pothole_id}{r.sequence_no ? ` (stop ${r.sequence_no})` : ""}
                    <Link href={`/?pothole=${r.pothole_id}`} className={`block text-sm ${linkClass}`}>
                      View on map
                    </Link>
                  </td>
                  <td>{r.road_name ?? "unknown"}</td>
                  <td><BandChip band={r.priority_band} /> {r.priority_score.toFixed(2)}</td>
                  <td>{r.zone_id ?? "–"}</td>
                  <td>{r.crew_name ?? "–"}</td>
                  <td>{tab === "Repaired" ? (r.repaired_at ? new Date(r.repaired_at).toLocaleDateString() : "–") : (r.planned_date ?? "–")}</td>
                  <td><StatusButtons potholeId={r.pothole_id} status={r.status} onChanged={() => setVersion((v) => v + 1)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
