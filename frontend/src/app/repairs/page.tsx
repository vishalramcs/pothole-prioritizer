"use client";

import { useEffect, useState } from "react";
import StatusButtons from "@/components/repairs/StatusButtons";
import { BandChip } from "@/components/ui/chips";
import { apiFetch } from "@/lib/api";
import { STATUSES, type RepairRow, type Status } from "@/lib/types";

export default function RepairsPage() {
  const [tab, setTab] = useState<Status>("Pending");
  const [rows, setRows] = useState<RepairRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let alive = true;
    apiFetch<RepairRow[]>(`/repairs?status=${encodeURIComponent(tab)}`)
      .then((d) => alive && (setRows(d), setError(null)))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [tab, version]);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-[28px] font-semibold">Repairs</h1>
      <div role="tablist" aria-label="Repair status" className="flex flex-wrap gap-2">
        {STATUSES.map((s) => (
          <button key={s} role="tab" type="button" aria-selected={tab === s} onClick={() => { setTab(s); setRows(null); }}
            className={`rounded px-3 py-2 font-medium focus-visible:outline-2 focus-visible:outline-brand ${tab === s ? "bg-brand text-white" : "bg-surface text-foreground shadow"}`}>
            {s}
          </button>
        ))}
      </div>

      <div role="tabpanel" className="overflow-x-auto rounded-lg bg-surface p-4 shadow">
        {error && <p role="alert" className="text-critical">{error}</p>}
        {!rows && !error && <p className="text-muted">Loading…</p>}
        {rows?.length === 0 && <p className="text-muted">No potholes are {tab.toLowerCase()}.</p>}
        {rows && rows.length > 0 && (
          <table className="w-full text-left">
            <thead className="text-xs text-muted">
              <tr>
                <th className="py-2">Pothole</th><th>Road</th><th>Priority</th><th>Zone</th><th>Crew</th>
                <th>{tab === "Repaired" ? "Repaired" : "Planned date"}</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.pothole_id} className="border-t border-background align-top">
                  <td className="py-2">#{r.pothole_id}{r.sequence_no ? ` (stop ${r.sequence_no})` : ""}</td>
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
