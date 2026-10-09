-- Demo seed. Roads and traffic values are MOCK data; every road is labelled data_source = 'mock'.
-- All config values are assumptions to tune, not standards.

INSERT INTO public.config (key, value) VALUES
  ('W_SEVERITY',             '0.40'),
  ('W_TRAFFIC',              '0.25'),
  ('W_IMPORTANCE',           '0.20'),
  ('W_REPEAT',               '0.15'),
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

INSERT INTO public.roads (name, road_type, importance_score, traffic_score, data_source) VALUES
  ('Demo Highway',       'highway',   1.0, 0.90, 'mock'),
  ('Demo Main Road',     'arterial',  0.8, 0.70, 'mock'),
  ('Demo Market Street', 'collector', 0.5, 0.60, 'mock'),
  ('Demo Lane',          'local',     0.3, 0.20, 'mock');

INSERT INTO public.crews (name, capacity_per_day) VALUES
  ('Crew A', 5),
  ('Crew B', 5);
