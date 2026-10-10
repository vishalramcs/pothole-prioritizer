import { BarChart3, Gauge, Map, Route, Upload, Wrench } from "lucide-react";

// Which links each role sees comes from canOpen() in lib/auth.tsx.
export const NAV_LINKS = [
  { href: "/", label: "Map", icon: Map },
  { href: "/upload", label: "Report a pothole", icon: Upload },
  { href: "/zones-plan", label: "Zones and Plan", icon: Route },
  { href: "/repairs", label: "Repairs", icon: Wrench },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/evaluation", label: "Evaluation", icon: Gauge },
] as const;
