import os

# Tests must not depend on a developer's real .env
os.environ.setdefault("DATABASE_URL", "")
