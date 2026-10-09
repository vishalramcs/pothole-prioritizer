-- Seed: tunable config and two crews. Roads come from OpenStreetMap at upload time.
-- All config values are assumptions to tune, not standards.

INSERT INTO public.config (key, value) VALUES
  ('W_SEVERITY',             '0.40'),
  ('W_TRAFFIC',              '0.20'),
  ('W_IMPORTANCE',           '0.15'),
  ('W_REPEAT',               '0.10'),
  ('W_FACILITY',             '0.15'),
  ('FACILITY_DECAY_M',       '500'),
  ('MIN_CONFIDENCE',         '0.40'),
  ('AREA_RATIO_MAX',         '0.10'),
  ('SEV_MEDIUM_MIN',         '0.30'),
  ('SEV_HIGH_MIN',           '0.60'),
  ('BAND_CRITICAL',          '0.70'),
  ('BAND_MODERATE',          '0.40'),
  ('DEDUP_RADIUS_M',         '15'),
  ('REPEAT_CAP',             '3'),
  ('ZONE_EPS_M',             '200'),
  ('FRAME_INTERVAL_S',       '1'),
  ('VIDEO_IOU_MIN',          '0.30'),
  ('SAFETY_FLOOR_SEVERITY',  '0');

-- No roads here: each pothole's road is looked up on OpenStreetMap at upload time (migration 0005).

INSERT INTO public.crews (name, capacity_per_day) VALUES
  ('Crew A', 5),
  ('Crew B', 5);
