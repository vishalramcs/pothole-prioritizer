"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_LINKS } from "@/lib/constants";

export default function NavBar() {
  const pathname = usePathname();
  return (
    <header className="bg-brand text-white">
      <nav className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-3">
        <span className="text-base font-semibold">SRPPS</span>
        <ul className="flex gap-4">
          {NAV_LINKS.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded px-2 py-1 focus-visible:outline-2 focus-visible:outline-white ${
                    active ? "bg-white/20 font-medium" : "hover:bg-white/10"
                  }`}
                >
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
