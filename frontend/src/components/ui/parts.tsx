// Small hardware details of the industrial design: purely decorative, hidden from screen readers.

/** Three recessed ventilation slots, for the top-right corner of a panel. */
export function VentSlots({ className = "", dark = false }: { className?: string; dark?: boolean }) {
  return (
    <div aria-hidden className={`flex gap-1 ${className}`}>
      {[0, 1, 2].map((i) => (
        <span key={i} className={`h-6 w-1 rounded-full ${dark ? "bg-black/40 shadow-[inset_1px_1px_2px_rgba(0,0,0,0.5)]" : "bg-recessed shadow-[inset_1px_1px_2px_rgba(0,0,0,0.15)]"}`} />
      ))}
    </div>
  );
}

/** A small status LED with its glow. */
export function Led({ color = "red", pulse = false }: { color?: "red" | "green"; pulse?: boolean }) {
  const look = color === "green" ? "bg-[#22c55e] shadow-glow-green" : "bg-accent shadow-glow";
  return <span aria-hidden className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${look} ${pulse ? "animate-pulse motion-reduce:animate-none" : ""}`} />;
}
