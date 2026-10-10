-- Accounts for the two kinds of stakeholders.
--   citizen:  signs up on the website; can report potholes (photo or video + a description).
--   official: created by an administrator (backend/scripts/create_user.py); can use everything.
-- Passwords are stored as scrypt hashes. Sessions store only a SHA-256 of the random cookie token,
-- so a leaked table does not let anyone log in.

CREATE TABLE public.users (
  user_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE CHECK (email = lower(email) AND length(email) <= 254),
  name          TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('citizen', 'official')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.sessions (
  token_hash TEXT PRIMARY KEY,
  user_id    BIGINT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
  expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX sessions_user_id_idx ON public.sessions (user_id);

-- Who reported it and what they said. Existing uploads have no reporter.
ALTER TABLE public.uploads
  ADD COLUMN user_id     BIGINT REFERENCES public.users(user_id) ON DELETE SET NULL,
  ADD COLUMN description TEXT CHECK (length(description) <= 1000);

-- Same lock-down as 0002: only the Python backend (postgres role) reads these.
ALTER TABLE public.users    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
