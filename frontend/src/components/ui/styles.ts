// Shared class strings for the industrial design system, so pages don't repeat them.

// Inputs are recessed wells: inset shadow instead of a border, monospace data entry; on focus the accent
// lights up behind them like an LED backlight.
export const fieldClass =
  "block min-h-12 rounded-md border-none bg-background px-3 py-2 font-mono text-sm text-foreground shadow-recessed outline-none transition-shadow duration-200 placeholder:text-muted/50 focus-visible:shadow-[var(--shadow-recessed),0_0_0_2px_var(--accent)] disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:shadow-[var(--shadow-recessed),0_0_0_2px_var(--critical)]";

// Small stamped labels: monospace, bold, uppercase, wide tracking.
export const labelClass = "font-mono text-xs font-bold uppercase tracking-[0.08em] text-muted";

// A panel bolted onto the chassis: lifted by the card shadow, with four screw heads.
export const cardClass = "screws rounded-lg bg-background p-6 shadow-card";

// A small stat tile on the chassis; it lifts when pointed at.
export const tileClass =
  "rounded-lg bg-background px-6 py-4 shadow-card transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-floating motion-reduce:transition-none motion-reduce:hover:translate-y-0";

// Keyboard focus: an accent ring, offset from the part.
export const focusRing = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background";

// Text links: accent-coloured, underlined.
export const linkClass = `font-semibold text-primary underline decoration-2 underline-offset-4 hover:text-primary-hover ${focusRing}`;
