import type { ButtonHTMLAttributes } from "react";
import { focusRing } from "./styles";

type Variant = "primary" | "secondary" | "outline";
type Size = "sm" | "md" | "lg";

// Physical keys: raised by their shadow, pressed in on click (moves down 2px, the shadow turns inward).
const VARIANT: Record<Variant, string> = {
  primary: "border border-white/20 bg-primary text-white shadow-key hover:brightness-110",
  secondary: "bg-background text-foreground shadow-card hover:text-primary",
  outline: "bg-background text-primary shadow-card hover:text-primary-hover",
};

// Dashboard-tuned sizes; at least 48px tall on touch screens: sm for table rows, md for forms, lg for a page's main action.
const SIZE: Record<Size, string> = {
  sm: "h-12 rounded-md px-4 text-xs sm:h-10",
  md: "h-12 rounded-lg px-6 text-sm",
  lg: "h-14 rounded-xl px-8 text-base",
};

/** Class string for anything that should look like a button (also used on <Link>). */
export function buttonClass(variant: Variant = "primary", size: Size = "md", extra = ""): string {
  return [
    "inline-flex items-center justify-center gap-2 font-bold uppercase tracking-[0.05em]",
    "transition-all duration-150 ease-mechanical active:translate-y-[2px] active:shadow-pressed",
    "motion-reduce:transition-none motion-reduce:active:translate-y-0",
    "disabled:pointer-events-none disabled:opacity-50",
    focusRing, VARIANT[variant], SIZE[size], extra,
  ].join(" ");
}

export default function Button({ variant = "primary", size = "md", className = "", type = "button", ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return <button type={type} className={buttonClass(variant, size, className)} {...props} />;
}
