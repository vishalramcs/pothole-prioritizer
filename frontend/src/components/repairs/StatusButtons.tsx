"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import { ApiError, apiFetch, json } from "@/lib/api";
import type { Status } from "@/lib/types";

// docs/03-app-flow.md, Flow D: which buttons each status shows (rules in TRD 4.9).
const ACTIONS: Record<Status, { label: string; to: Status }[]> = {
  Pending: [{ label: "Start", to: "In Progress" }, { label: "Mark repaired", to: "Repaired" }],
  Scheduled: [
    { label: "Start", to: "In Progress" },
    { label: "Mark repaired", to: "Repaired" },
    { label: "Unschedule", to: "Pending" },
  ],
  "In Progress": [{ label: "Mark repaired", to: "Repaired" }],
  Repaired: [],
};

export default function StatusButtons({ potholeId, status, onChanged }: {
  potholeId: number;
  status: Status;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function change(to: Status) {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/potholes/${potholeId}/status`, json("PATCH", { status: to }));
      onChanged();
    } catch (e) {
      setError(e instanceof ApiError && e.status === 409
        ? "That change isn't allowed from the current status"
        : (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (ACTIONS[status].length === 0) return <span className="text-xs font-semibold uppercase tracking-wider text-muted">Final</span>;
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {ACTIONS[status].map(({ label, to }) => (
          <Button key={to} variant="outline" size="sm" disabled={busy} onClick={() => change(to)}>
            {label}
          </Button>
        ))}
      </div>
      {error && <p role="alert" className="mt-1 text-xs text-critical">{error}</p>}
    </div>
  );
}
