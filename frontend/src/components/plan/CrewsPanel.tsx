"use client";

import { useState } from "react";
import { apiFetch, json } from "@/lib/api";
import type { Crew } from "@/lib/types";

const input = "rounded border border-muted bg-surface px-2 py-1";
const button = "rounded border border-brand px-2 py-1 text-xs font-medium text-brand hover:bg-brand hover:text-white focus-visible:outline-2 focus-visible:outline-brand";

function CrewRow({ crew, onChanged, onError }: { crew: Crew; onChanged: () => void; onError: (m: string) => void }) {
  const [name, setName] = useState(crew.name);
  const [cap, setCap] = useState(String(crew.capacity_per_day));
  const dirty = name !== crew.name || cap !== String(crew.capacity_per_day);

  async function run(init: RequestInit) {
    try {
      await apiFetch(`/crews/${crew.crew_id}`, init);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  return (
    <li className="flex flex-wrap items-center gap-2">
      <input aria-label="Crew name" className={`${input} w-28`} value={name} onChange={(e) => setName(e.target.value)} />
      <label className="flex items-center gap-1 text-xs text-muted">
        <input aria-label={`Repairs per day for ${crew.name}`} type="number" min={1} max={100}
          className={`${input} w-16`} value={cap} onChange={(e) => setCap(e.target.value)} />
        per day
      </label>
      {dirty && <button type="button" className={button} onClick={() => run(json("PUT", { name, capacity_per_day: Number(cap) }))}>Save</button>}
      <button type="button" className={button} onClick={() => run({ method: "DELETE" })} aria-label={`Delete ${crew.name}`}>Delete</button>
    </li>
  );
}

export default function CrewsPanel({ crews, onChanged }: { crews: Crew[]; onChanged: () => void }) {
  const [name, setName] = useState("");
  const [cap, setCap] = useState("5");
  const [error, setError] = useState<string | null>(null);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiFetch("/crews", json("POST", { name, capacity_per_day: Number(cap) }));
      setName("");
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <section aria-label="Crews" className="flex flex-col gap-2">
      <h2 className="text-xl font-semibold">Crews</h2>
      {crews.length === 0 && <p className="text-muted">Add at least one crew first.</p>}
      <ul className="flex flex-col gap-2">
        {crews.map((c) => (
          // key includes the saved values so the row's inputs reset after a save
          <CrewRow key={`${c.crew_id}-${c.name}-${c.capacity_per_day}`} crew={c} onError={setError}
            onChanged={() => { setError(null); onChanged(); }} />
        ))}
      </ul>
      <form onSubmit={add} className="flex flex-wrap items-center gap-2">
        <input aria-label="New crew name" placeholder="New crew name" className={`${input} w-28`} value={name} onChange={(e) => setName(e.target.value)} />
        <input aria-label="New crew repairs per day" type="number" min={1} max={100} className={`${input} w-16`} value={cap} onChange={(e) => setCap(e.target.value)} />
        <button type="submit" disabled={!name.trim()} className={`${button} disabled:opacity-50`}>Add crew</button>
      </form>
      {error && <p role="alert" className="text-xs text-critical">{error}</p>}
    </section>
  );
}
