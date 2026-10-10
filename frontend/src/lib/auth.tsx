"use client";

// Who is logged in, and which pages they may open. The API enforces the same rules (backend app/api/router.py);
// this only keeps people away from pages that would just show "Only officials can do this".
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiFetch, LOGGED_OUT_EVENT } from "@/lib/api";

export type Role = "citizen" | "official";
export interface User {
  user_id: number;
  email: string;
  name: string;
  role: Role;
}

// Citizens report potholes; officials use everything.
const CITIZEN_PAGES = ["/upload"];
export const HOME: Record<Role, string> = { official: "/", citizen: "/upload" };
export const canOpen = (role: Role, path: string) => role === "official" || CITIZEN_PAGES.includes(path);

const AuthContext = createContext<{ user: User | null | undefined; setUser: (u: User | null) => void }>({
  user: undefined,
  setUser: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

/** undefined while checking the session, null when logged out. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  useEffect(() => {
    apiFetch<User>("/auth/me").then(setUser).catch(() => setUser(null));
    const out = () => setUser(null); // any 401 from the API: the session expired
    window.addEventListener(LOGGED_OUT_EVENT, out);
    return () => window.removeEventListener(LOGGED_OUT_EVENT, out);
  }, []);
  return <AuthContext value={{ user, setUser }}>{children}</AuthContext>;
}

/** Sends logged-out visitors to /login and keeps each role on its own pages. */
export function AuthGate({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const path = usePathname();
  const router = useRouter();
  const onLogin = path === "/login";
  const target = user === undefined ? null
    : user === null ? (onLogin ? null : "/login")
    : onLogin || !canOpen(user.role, path) ? HOME[user.role]
    : null;

  useEffect(() => {
    if (target) router.replace(target);
  }, [target, router]);

  if (user === undefined) return <p className="text-muted">Checking your session…</p>;
  if (target) return null;
  return children;
}
