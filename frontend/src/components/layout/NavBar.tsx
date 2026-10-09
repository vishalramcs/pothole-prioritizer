"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_LINKS } from "@/lib/constants";

export default function NavBar() {
  const pathname = usePathname();
  return (
    <header className="bg-foreground text-white">
      <nav aria-label="Main" className="mx-auto flex max-w-7xl items-center gap-6 overflow-x-auto px-4 py-3 sm:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2 rounded-md text-xl font-extrabold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-bright">
          <span aria-hidden className="h-5 w-5 rounded-sm bg-primary-bright" />
          SRPPS
        </Link>
        <ul className="flex gap-1">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-semibold transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-bright ${
                    active ? "bg-primary text-white" : "text-white hover:bg-white/10"
                  }`}
                >
                  <Icon aria-hidden size={18} strokeWidth={2.25} />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
