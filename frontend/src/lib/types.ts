// Mirrors supabase/migrations/0001_init_schema.sql and the API in docs/02-technical-requirements.md.
export type RoadType = "highway" | "arterial" | "collector" | "local";
export type Status = "Pending" | "Scheduled" | "In Progress" | "Repaired";
export type Band = "Low" | "Moderate" | "Critical";
export type SeverityLevel = "Low" | "Medium" | "High";

export interface Pothole {
  pothole_id: number;
  upload_id: number;
  road_id: number | null;
  zone_id: number | null;
  lat: number;
  lng: number;
  bbox_x: number | null;
  bbox_y: number | null;
  bbox_w: number | null;
  bbox_h: number | null;
  confidence: number | null;
  severity_score: number;
  severity_level: SeverityLevel;
  priority_score: number;
  priority_band: Band;
  safety_override: boolean;
  status: Status;
  detection_count: number;
  recurrence_count: number;
  first_detected_at: string;
  last_detected_at: string;
  repaired_at: string | null;
}
