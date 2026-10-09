import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

// Poster-style colour blocks for page headers only (tables and maps below stay calm for planners).
// Text colours are chosen per block for WCAG AA: white on blue 600 (5.2:1) and on gray 900, dark on emerald (7.0:1).
const TONE = {
  primary: { block: "bg-primary text-white", icon: "bg-white text-primary", shape: "bg-white" },
  ink: { block: "bg-foreground text-white", icon: "bg-primary-bright text-white", shape: "bg-primary-bright" },
  emerald: { block: "bg-secondary text-foreground", icon: "bg-foreground text-secondary", shape: "bg-white" },
} as const;

export default function PageHeader({ title, subtitle, icon: Icon, tone = "primary", children }: {
  title: string;
  subtitle?: string;
  icon: LucideIcon;
  tone?: keyof typeof TONE;
  children?: ReactNode;
}) {
  const t = TONE[tone];
  return (
    <header className={`relative overflow-hidden rounded-lg px-6 py-8 sm:px-10 ${t.block}`}>
      {/* decoration: large flat shapes at low opacity, hidden from screen readers */}
      <div aria-hidden className={`absolute -right-16 -top-24 h-72 w-72 rounded-full opacity-10 ${t.shape}`} />
      <div aria-hidden className={`absolute -bottom-20 right-40 h-40 w-40 rotate-12 rounded-lg opacity-10 ${t.shape}`} />
      <div className="relative flex flex-wrap items-center gap-5">
        <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full ${t.icon}`}>
          <Icon aria-hidden size={28} strokeWidth={2.5} />
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="text-3xl font-extrabold leading-tight sm:text-4xl">{title}</h1>
          {subtitle && <p className="mt-1 max-w-3xl text-base">{subtitle}</p>}
        </div>
        {children}
      </div>
    </header>
  );
}
