"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import { Led } from "@/components/ui/parts";
import { focusRing } from "@/components/ui/styles";
import { apiFetch } from "@/lib/api";
import { canOpen, HOME, useAuth } from "@/lib/auth";
import { NAV_LINKS } from "@/lib/constants";

export default function NavBar() {
  const pathname = usePathname();
  const { user, setUser } = useAuth();
  const links = user ? NAV_LINKS.filter((l) => canOpen(user.role, l.href)) : [];

  async function logout() {
    await apiFetch("/auth/logout", { method: "POST" }).catch(() => {}); // logged out locally even if the API is down
    setUser(null);
  }
  return (
    <header className="relative z-[1100] bg-background shadow-[0_4px_12px_#babecc,0_-1px_0_#ffffff_inset]">
      <nav aria-label="Main" className="mx-auto flex max-w-7xl items-center gap-4 overflow-x-auto px-4 py-3 sm:px-6">
        <Link href={user ? HOME[user.role] : "/login"} className={`flex shrink-0 items-center gap-3 rounded-md ${focusRing}`}>
          <span aria-hidden className="h-6 w-6 rounded-md border border-white/20 bg-primary shadow-key" />
          {/* the long name wraps to two short lines, so the bar stays narrow enough for every link on a laptop */}
          <span className="flex flex-col leading-none">
            <span className="emboss text-xl font-extrabold tracking-tight">SRPPS</span>
            <span className="mt-0.5 max-w-[13rem] font-mono text-[10px] font-bold uppercase leading-tight tracking-[0.02em] text-muted">
              Smart Road Pothole Prioritization System
            </span>
          </span>
        </Link>
        <ul className="flex gap-2">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`flex min-h-10 items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-bold transition-all duration-150 ease-mechanical ${focusRing} ${
                    active ? "bg-background text-primary shadow-pressed" : "text-muted hover:bg-recessed hover:text-foreground hover:shadow-recessed"
                  }`}
                >
                  <Icon aria-hidden size={18} strokeWidth={1.75} />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
        {user && (
          <div className="ml-auto flex shrink-0 items-center gap-3">
            <span className="hidden items-center gap-2 text-right xl:flex">
              <Led color="green" pulse />
              <span className="leading-tight">
                <span className="block text-sm font-bold">{user.name}</span>
                <span className="block font-mono text-[10px] font-bold uppercase tracking-[0.08em] text-muted">{user.role}</span>
              </span>
            </span>
            <button type="button" onClick={logout} title={`Log out ${user.email}`}
              className={`flex min-h-10 items-center gap-2 rounded-md px-3 text-sm font-bold text-muted transition-all duration-150 ease-mechanical hover:bg-recessed hover:text-foreground hover:shadow-recessed ${focusRing}`}>
              <LogOut aria-hidden size={18} strokeWidth={1.75} /> Log out
            </button>
          </div>
        )}
      </nav>
    </header>
  );
}
