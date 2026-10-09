export interface Zone {
  zone_id: number;
  centroid_lat: number;
  centroid_lng: number;
  pothole_count: number;
  avg_priority: number;
  radius_m: number;
  created_at: string;
}
