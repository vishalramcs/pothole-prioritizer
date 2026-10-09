import { BarChart3, Gauge, Map, Route, Upload, Wrench } from "lucide-react";

export const NAV_LINKS = [
  { href: "/", label: "Map", icon: Map },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/zones-plan", label: "Zones and Plan", icon: Route },
  { href: "/repairs", label: "Repairs", icon: Wrench },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/evaluation", label: "Evaluation", icon: Gauge },
] as const;
