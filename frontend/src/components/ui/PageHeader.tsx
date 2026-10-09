import type { LucideIcon } from "lucide-react";
import { VentSlots } from "./parts";

/** Page title as a module bolted onto the chassis: screws, vent slots, and the page icon in a raised housing. */
export default function PageHeader({ title, subtitle, icon: Icon }: {
  title: string;
  subtitle?: string;
  icon: LucideIcon;
}) {
  return (
    <header className="screws relative rounded-xl bg-background px-6 py-7 shadow-card sm:px-10">
      <VentSlots className="absolute right-6 top-5" />
      <div className="flex flex-wrap items-center gap-5">
        <span className="group flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-background shadow-floating">
          <Icon aria-hidden size={28} strokeWidth={1.75}
            className="text-primary transition-transform duration-200 ease-mechanical group-hover:rotate-12 group-hover:scale-110 motion-reduce:transition-none" />
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="emboss text-3xl font-extrabold sm:text-4xl">{title}</h1>
          {subtitle && <p className="mt-1 max-w-[65ch] text-base text-muted">{subtitle}</p>}
        </div>
      </div>
    </header>
  );
}
