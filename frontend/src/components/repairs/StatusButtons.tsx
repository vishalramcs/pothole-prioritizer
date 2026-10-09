"use client";

import { useRef, useState } from "react";
import Button from "@/components/ui/Button";
import { focusRing } from "@/components/ui/styles";
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
  const confirmRef = useRef<HTMLDialogElement>(null);

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
  // the first action is the main one for this status; "Mark repaired" is final, so it asks first
  const run = (to: Status) => (to === "Repaired" ? confirmRef.current?.showModal() : change(to));
  const [main, ...rest] = ACTIONS[status];
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" disabled={busy} onClick={() => run(main.to)}>{main.label}</Button>
        {rest.map(({ label, to }) => (
          <button key={to} type="button" disabled={busy} onClick={() => run(to)}
            className={`text-sm font-semibold text-primary underline decoration-2 underline-offset-4 disabled:opacity-50 ${focusRing}`}>
            {label}
          </button>
        ))}
      </div>
      {error && <p role="alert" className="mt-1 text-xs text-critical">{error}</p>}
      <dialog ref={confirmRef} aria-labelledby={`confirm-${potholeId}`}
        className="m-auto rounded-lg bg-surface p-6 text-foreground backdrop:bg-foreground/50">
        <h2 id={`confirm-${potholeId}`} className="text-xl font-bold">Mark pothole #{potholeId} as repaired?</h2>
        <p className="mt-1 text-sm text-muted">Repaired is final. If the pothole comes back, a new upload records it as a recurrence.</p>
        <form method="dialog" className="mt-4 flex justify-end gap-3">
          <Button type="submit" variant="secondary">Cancel</Button>
          <Button onClick={() => { confirmRef.current?.close(); change("Repaired"); }}>Confirm</Button>
        </form>
      </dialog>
    </div>
  );
}
