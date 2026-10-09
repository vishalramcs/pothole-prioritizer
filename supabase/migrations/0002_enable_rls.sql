-- Supabase exposes the public schema through its Data API. The browser never talks
-- to the database directly in SRPPS (it calls the Python API), so lock every table:
-- RLS on, no policies = the anon and authenticated roles can read and write nothing.
-- The Python backend connects with the database role (postgres), which bypasses RLS.

ALTER TABLE public.roads         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploads       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.zones         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.potholes      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crews         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.repair_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.config        ENABLE ROW LEVEL SECURITY;
