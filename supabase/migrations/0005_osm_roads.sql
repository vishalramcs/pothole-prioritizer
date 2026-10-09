-- Real roads and more important buildings, both from OpenStreetMap.
-- Roads: found at upload time from the pothole's location (backend/app/services/osm_roads.py).
--   importance comes from the OSM road class; traffic is ESTIMATED from road class and lane count
--   (no free source of real traffic counts), so data_source = 'osm_estimate'.
-- Facilities: colleges, universities, police, bus and railway stations join hospitals, clinics, schools, fire stations.

ALTER TABLE public.roads DROP CONSTRAINT IF EXISTS roads_name_road_type_key;  -- many OSM roads share a name
ALTER TABLE public.roads DROP CONSTRAINT IF EXISTS roads_data_source_check;
ALTER TABLE public.roads ADD CONSTRAINT roads_data_source_check CHECK (data_source IN ('mock', 'real', 'osm_estimate'));
ALTER TABLE public.roads
  ADD COLUMN osm_way_id  TEXT UNIQUE,     -- e.g. way/123456
  ADD COLUMN osm_highway TEXT,            -- the OSM highway tag (primary, residential, ...)
  ADD COLUMN lanes       INTEGER;

ALTER TABLE public.facilities DROP CONSTRAINT IF EXISTS facilities_kind_check;
ALTER TABLE public.facilities ADD CONSTRAINT facilities_kind_check CHECK (kind IN
  ('hospital', 'clinic', 'fire_station', 'school', 'college', 'university', 'police', 'bus_station', 'railway_station'));
