-- Location factor: proximity to critical facilities (hospital, clinic, school, fire station) from OpenStreetMap.
-- Filled by backend/scripts/import_facilities.py. Each pothole stores its nearest facility and
-- facility_score = exp(-distance_m / FACILITY_DECAY_M), which is a fifth weighted factor in the priority.

CREATE TABLE public.facilities (
  facility_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  osm_id      TEXT NOT NULL UNIQUE,            -- e.g. node/123, way/456
  name        TEXT,
  kind        TEXT NOT NULL CHECK (kind IN ('hospital','clinic','school','fire_station')),
  lat         DOUBLE PRECISION NOT NULL CHECK (lat BETWEEN -90 AND 90),
  lng         DOUBLE PRECISION NOT NULL CHECK (lng BETWEEN -180 AND 180),
  data_source TEXT NOT NULL DEFAULT 'osm'
);
CREATE INDEX idx_facilities_geo ON public.facilities(lat, lng);
ALTER TABLE public.facilities ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.potholes
  ADD COLUMN facility_score     DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (facility_score BETWEEN 0 AND 1),
  ADD COLUMN nearest_facility   TEXT,
  ADD COLUMN nearest_facility_m DOUBLE PRECISION;

-- New weights (must still sum to 1). Only touches databases that were already seeded: on a fresh database
-- the config table is empty here and seed.sql inserts these values instead.
UPDATE public.config SET value = '0.40' WHERE key = 'W_SEVERITY';
UPDATE public.config SET value = '0.20' WHERE key = 'W_TRAFFIC';
UPDATE public.config SET value = '0.15' WHERE key = 'W_IMPORTANCE';
UPDATE public.config SET value = '0.10' WHERE key = 'W_REPEAT';
INSERT INTO public.config (key, value)
  SELECT k, v FROM (VALUES ('W_FACILITY', '0.15'), ('FACILITY_DECAY_M', '500')) AS t(k, v)
  WHERE EXISTS (SELECT 1 FROM public.config);
