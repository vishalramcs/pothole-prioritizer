import type { ButtonHTMLAttributes } from "react";
import { focusRing } from "./styles";

type Variant = "primary" | "secondary" | "outline";
type Size = "sm" | "md" | "lg";

const VARIANT: Record<Variant, string> = {
  primary: "bg-primary text-white hover:bg-primary-hover",
  secondary: "bg-background text-foreground hover:bg-border",
  outline: "border-2 border-primary text-primary hover:bg-primary hover:text-white",
};

// Dashboard-tuned sizes: sm for table rows, md for forms, lg (h-14) for a page's main action.
const SIZE: Record<Size, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-5 text-sm",
  lg: "h-14 px-8 text-base",
};

/** Class string for anything that should look like a button (also used on <Link>). */
export function buttonClass(variant: Variant = "primary", size: Size = "md", extra = ""): string {
  return [
    "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-all duration-200",
    "hover:scale-105 active:scale-100 motion-reduce:transition-none motion-reduce:hover:scale-100",
    "disabled:pointer-events-none disabled:opacity-50",
    focusRing, VARIANT[variant], SIZE[size], extra,
  ].join(" ");
}

export default function Button({ variant = "primary", size = "md", className = "", type = "button", ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return <button type={type} className={buttonClass(variant, size, className)} {...props} />;
}
