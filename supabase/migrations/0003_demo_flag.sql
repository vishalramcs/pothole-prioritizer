-- Mark uploads created by backend/scripts/load_demo_data.py, so the UI can label them as demo data
-- (docs/05, section 8: never present seeded rows as real reports).
ALTER TABLE public.uploads ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT false;
