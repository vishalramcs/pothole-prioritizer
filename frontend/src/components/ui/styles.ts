// Shared class strings for the flat design system, so pages don't repeat them.

// Inputs: grey block, no border; on focus a hard 2px primary border on white (no glow).
export const fieldClass =
  "block rounded-md border-2 border-transparent bg-background px-3 py-2 text-foreground outline-none transition-colors duration-200 focus:border-primary focus:bg-surface aria-[invalid=true]:border-critical";

// Small uppercase labels above fields and in panels.
export const labelClass = "text-xs font-semibold uppercase tracking-wider text-muted";

// Keyboard focus: solid ring, never a shadow.
export const focusRing = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2";
