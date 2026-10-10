-- Reward points for citizens who report potholes. One row per citizen upload, including 0-point decisions
-- (so the reason is on record). A user's total is the sum of their rows; nothing else stores a balance.
-- user_email is the account email at the time (not verified: sign-up has no email check).

CREATE TABLE public.points_ledger (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
  user_email  TEXT NOT NULL,
  upload_id   BIGINT REFERENCES public.uploads(upload_id) ON DELETE SET NULL,
  pothole_id  BIGINT REFERENCES public.potholes(pothole_id) ON DELETE SET NULL,
  points      INTEGER NOT NULL CHECK (points >= 0),
  reason      TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX points_ledger_user_idx ON public.points_ledger (user_id, created_at);
-- the same pothole earns a given user points only once
CREATE UNIQUE INDEX points_ledger_once_per_pothole ON public.points_ledger (user_id, pothole_id) WHERE points > 0;

ALTER TABLE public.points_ledger ENABLE ROW LEVEL SECURITY;  -- same lock-down as 0002
