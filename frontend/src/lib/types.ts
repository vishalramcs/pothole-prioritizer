// Mirrors supabase/migrations/0001_init_schema.sql and the API in docs/02-technical-requirements.md.
export type RoadType = "highway" | "arterial" | "collector" | "local";
export type Status = "Pending" | "Scheduled" | "In Progress" | "Repaired";
export type Band = "Low" | "Moderate" | "Critical";
export type SeverityLevel = "Low" | "Medium" | "High";

export const STATUSES: Status[] = ["Pending", "Scheduled", "In Progress", "Repaired"];
export const BANDS: Band[] = ["Critical", "Moderate", "Low"];

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
  area_ratio: number | null;
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
  // joined from roads and uploads
  road_name: string | null;
  road_type: RoadType | null;
  traffic_score: number | null;
  importance_score: number | null;
  road_data_source: "mock" | "real" | null;
  image_width: number;
  image_height: number;
  is_demo: boolean;
}

export interface BreakdownPart {
  value: number;
  weight: number;
  contribution: number;
}

export interface PotholeDetail extends Pothole {
  breakdown: Record<"severity" | "traffic" | "importance" | "repeat", BreakdownPart>;
}

export interface Road {
  road_id: number;
  name: string;
  road_type: RoadType;
  importance_score: number;
  traffic_score: number;
  data_source: "mock" | "real";
}

export interface UploadedPothole extends Pothole {
  match: "new" | "repeat" | "recurrence";
  frame_index: number | null;
  frame_time_s: number | null;
}

export interface UploadResult {
  upload_id: number;
  media_type?: "video";
  frames_sampled?: number;
  lat: number;
  lng: number;
  gps_source: "exif" | "manual" | "map_click";
  image_width: number;
  image_height: number;
  potholes: UploadedPothole[];
}

export interface RepairRow {
  pothole_id: number;
  status: Status;
  priority_band: Band;
  priority_score: number;
  severity_level: SeverityLevel;
  zone_id: number | null;
  repaired_at: string | null;
  road_name: string | null;
  order_id: number | null;
  crew_id: number | null;
  crew_name: string | null;
  sequence_no: number | null;
  planned_date: string | null;
  completed_at: string | null;
}

export interface Zone {
  zone_id: number;
  centroid_lat: number;
  centroid_lng: number;
  pothole_count: number;
  avg_priority: number;
  radius_m: number;
  created_at: string;
}

export interface Crew {
  crew_id: number;
  name: string;
  capacity_per_day: number;
}

export interface PlannedStop {
  pothole_id: number;
  crew_id: number;
  crew_name: string;
  sequence_no: number;
  planned_date: string;
  zone_id: number | null;
  road_name: string | null;
  priority_score: number;
  priority_band: Band;
}

export interface PlanResult {
  message: string;
  scheduled: PlannedStop[];
  unscheduled_count: number;
  unscheduled_ids: number[];
}
