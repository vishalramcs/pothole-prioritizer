"use client";

import { useState } from "react";
import { Landmark, LogIn, UserRound } from "lucide-react";
import Button from "@/components/ui/Button";
import { VentSlots } from "@/components/ui/parts";
import { fieldClass, focusRing, labelClass, linkClass } from "@/components/ui/styles";
import { apiFetch, json } from "@/lib/api";
import { useAuth, type Role, type User } from "@/lib/auth";

const ROLES: { role: Role; label: string; icon: typeof UserRound; text: string }[] = [
  { role: "citizen", label: "Citizen", icon: UserRound, text: "Report potholes with a photo or video and a short description." },
  { role: "official", label: "Official", icon: Landmark, text: "Priority map, repair plans, crews, analytics and evaluation." },
];

export default function LoginPage() {
  const { setUser } = useAuth();
  const [role, setRole] = useState<Role>("citizen");
  const [signUp, setSignUp] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const creating = signUp && role === "citizen"; // officials get accounts from an administrator

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      // the AuthGate sends the new user to their home page
      setUser(await apiFetch<User>(creating ? "/auth/register" : "/auth/login",
        json("POST", creating ? { name, email, password } : { email, password, role })));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const field = `${fieldClass} mt-1 w-full`;
  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-6 py-4">
      <div className="screws relative flex flex-col gap-6 rounded-xl bg-background p-8 shadow-card">
        <VentSlots className="absolute right-6 top-5" />
        <div>
          <h1 className="emboss text-3xl font-extrabold">{creating ? "Create a citizen account" : "Log in"}</h1>
          <p className="mt-1 text-muted">Smart Road Pothole Prioritization System</p>
        </div>

        <div role="radiogroup" aria-label="I am a" className="grid grid-cols-2 gap-3">
          {ROLES.map(({ role: r, label, icon: Icon }) => (
            <button key={r} type="button" role="radio" aria-checked={role === r} onClick={() => { setRole(r); setError(null); }}
              className={`flex min-h-14 items-center justify-center gap-2 rounded-lg bg-background font-bold transition-all duration-150 ease-mechanical ${focusRing} ${
                role === r ? "text-primary shadow-pressed" : "text-foreground shadow-card hover:text-primary active:translate-y-[2px]"}`}>
              <Icon aria-hidden size={20} strokeWidth={1.75} /> {label}
            </button>
          ))}
        </div>
        <p className="-mt-3 text-sm text-muted">{ROLES.find((r) => r.role === role)!.text}</p>

        <form onSubmit={submit} className="flex flex-col gap-4">
          {creating && (
            <label className={labelClass}>Name
              <input className={field} autoComplete="name" required maxLength={100} value={name} onChange={(e) => setName(e.target.value)} />
            </label>
          )}
          <label className={labelClass}>Email
            <input className={field} type="email" autoComplete="email" required maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className={labelClass}>Password{creating && " (at least 8 characters)"}
            <input className={field} type="password" autoComplete={creating ? "new-password" : "current-password"} required
              minLength={creating ? 8 : 1} maxLength={200} value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {error && <p role="alert" className="font-semibold text-critical-text">{error}</p>}
          <Button type="submit" size="lg" disabled={busy}>
            <LogIn aria-hidden size={20} strokeWidth={2} />
            {busy ? "Please wait…" : creating ? "Create account" : `Log in as ${role === "citizen" ? "citizen" : "official"}`}
          </Button>
        </form>

        <p className="text-sm text-muted">
          {role === "official"
            ? "Official accounts are created by your administrator."
            : creating
              ? <>Already have an account? <button type="button" className={linkClass} onClick={() => setSignUp(false)}>Log in</button></>
              : <>New here? <button type="button" className={linkClass} onClick={() => setSignUp(true)}>Create a citizen account</button></>}
        </p>
      </div>
    </div>
  );
}
