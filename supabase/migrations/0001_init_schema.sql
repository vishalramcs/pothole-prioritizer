-- SRPPS initial schema for Supabase Postgres.
-- Coordinates are WGS84 decimal degrees. Timestamps are timestamptz (UTC).
-- Distances are computed in Python (haversine); PostGIS is not required.

CREATE TABLE public.roads (
  road_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name             TEXT NOT NULL,
  road_type        TEXT NOT NULL CHECK (road_type IN ('highway','arterial','collector','local')),
  importance_score DOUBLE PRECISION NOT NULL CHECK (importance_score BETWEEN 0 AND 1),
  traffic_score    DOUBLE PRECISION NOT NULL CHECK (traffic_score BETWEEN 0 AND 1),
  data_source      TEXT NOT NULL DEFAULT 'mock' CHECK (data_source IN ('mock','real')),
  UNIQUE (name, road_type)
);

CREATE TABLE public.uploads (
  upload_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  storage_path TEXT NOT NULL,                 -- object path in the private Storage bucket
  media_type   TEXT NOT NULL CHECK (media_type IN ('image','video')),
  lat          DOUBLE PRECISION NOT NULL CHECK (lat BETWEEN -90 AND 90),
  lng          DOUBLE PRECISION NOT NULL CHECK (lng BETWEEN -180 AND 180),
  gps_source   TEXT NOT NULL CHECK (gps_source IN ('exif','manual','map_click')),
  road_id      BIGINT REFERENCES public.roads(road_id),
  image_width  INTEGER,
  image_height INTEGER,
  captured_at  TIMESTAMPTZ,
  uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.zones (
  zone_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  centroid_lat  DOUBLE PRECISION NOT NULL,
  centroid_lng  DOUBLE PRECISION NOT NULL,
  pothole_count INTEGER NOT NULL DEFAULT 0,
  avg_priority  DOUBLE PRECISION NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.potholes (
  pothole_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  upload_id          BIGINT NOT NULL REFERENCES public.uploads(upload_id),
  road_id            BIGINT REFERENCES public.roads(road_id),
  zone_id            BIGINT REFERENCES public.zones(zone_id) ON DELETE SET NULL,
  frame_index        INTEGER,
  frame_time_s       DOUBLE PRECISION,
  frame_storage_path TEXT,
  lat                DOUBLE PRECISION NOT NULL CHECK (lat BETWEEN -90 AND 90),
  lng                DOUBLE PRECISION NOT NULL CHECK (lng BETWEEN -180 AND 180),
  bbox_x             DOUBLE PRECISION,
  bbox_y             DOUBLE PRECISION,
  bbox_w             DOUBLE PRECISION,
  bbox_h             DOUBLE PRECISION,
  confidence         DOUBLE PRECISION CHECK (confidence BETWEEN 0 AND 1),
  area_ratio         DOUBLE PRECISION CHECK (area_ratio BETWEEN 0 AND 1),
  severity_score     DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (severity_score BETWEEN 0 AND 1),
  severity_level     TEXT NOT NULL DEFAULT 'Low' CHECK (severity_level IN ('Low','Medium','High')),
  detection_count    INTEGER NOT NULL DEFAULT 1,
  recurrence_count   INTEGER NOT NULL DEFAULT 0,
  priority_score     DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (priority_score BETWEEN 0 AND 1),
  priority_band      TEXT NOT NULL DEFAULT 'Low' CHECK (priority_band IN ('Low','Moderate','Critical')),
  safety_override    BOOLEAN NOT NULL DEFAULT false,
  status             TEXT NOT NULL DEFAULT 'Pending'
                     CHECK (status IN ('Pending','Scheduled','In Progress','Repaired')),
  first_detected_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_detected_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  repaired_at        TIMESTAMPTZ
);

CREATE TABLE public.crews (
  crew_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name             TEXT NOT NULL UNIQUE,
  capacity_per_day INTEGER NOT NULL CHECK (capacity_per_day > 0)
);

CREATE TABLE public.repair_orders (
  order_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  pothole_id   BIGINT NOT NULL UNIQUE REFERENCES public.potholes(pothole_id),
  crew_id      BIGINT NOT NULL REFERENCES public.crews(crew_id),
  sequence_no  INTEGER NOT NULL CHECK (sequence_no > 0),
  planned_date DATE NOT NULL,
  completed_at TIMESTAMPTZ,
  notes        TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.config (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE INDEX idx_potholes_status ON public.potholes(status);
CREATE INDEX idx_potholes_zone   ON public.potholes(zone_id);
CREATE INDEX idx_potholes_geo    ON public.potholes(lat, lng);
CREATE INDEX idx_potholes_road   ON public.potholes(road_id);
CREATE INDEX idx_orders_crew_seq ON public.repair_orders(crew_id, sequence_no);
