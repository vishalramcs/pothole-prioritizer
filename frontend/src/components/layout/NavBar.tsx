"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Led } from "@/components/ui/parts";
import { focusRing } from "@/components/ui/styles";
import { NAV_LINKS } from "@/lib/constants";

export default function NavBar() {
  const pathname = usePathname();
  return (
    <header className="relative z-[1100] bg-background shadow-[0_4px_12px_#babecc,0_-1px_0_#ffffff_inset]">
      <nav aria-label="Main" className="mx-auto flex max-w-7xl items-center gap-4 overflow-x-auto px-4 py-3 sm:px-6">
        <Link href="/" className={`flex shrink-0 items-center gap-3 rounded-md ${focusRing}`}>
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
          {NAV_LINKS.map(({ href, label, icon: Icon }) => {
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
        <span className="ml-auto hidden shrink-0 items-center gap-2 font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-muted xl:flex">
          <Led color="green" pulse /> PWR
        </span>
      </nav>
    </header>
  );
}
