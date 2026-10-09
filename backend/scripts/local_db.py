"""Start a local Postgres for development or an offline demo (docs/06, risks: "Supabase unreachable").

Run from backend/:  python scripts/local_db.py
Prints the DATABASE_URL to put in backend/.env. Postgres keeps running after this script exits;
stop it with:  python scripts/local_db.py --stop
On first start it applies supabase/migrations/*.sql and supabase/seed.sql.
Needs: pip install pgserver (a dev tool, not in requirements.txt).
"""
import sys
from pathlib import Path

import pgserver
import psycopg

# Postgres tools break on paths with spaces, so keep the data outside the repo folder.
PGDATA = Path.home() / ".srpps-pgdata"
SQL_DIR = Path(__file__).resolve().parents[2] / "supabase"


def main() -> None:
    if "--stop" in sys.argv:
        pgserver.get_server(PGDATA, cleanup_mode="stop").cleanup()  # "stop" keeps the data
        print("Stopped")
        return
    fresh = not (PGDATA / "PG_VERSION").exists()
    server = pgserver.get_server(PGDATA, cleanup_mode=None)  # None = leave it running after exit
    if fresh:
        # psycopg, not server.psql(): pgserver's psql call breaks when the venv path has a space
        with psycopg.connect(server.get_uri(), autocommit=True) as conn:
            for f in sorted((SQL_DIR / "migrations").glob("*.sql")) + [SQL_DIR / "seed.sql"]:
                conn.execute(f.read_text(encoding="utf-8"))
                print("applied", f.name)
    print("DATABASE_URL=" + server.get_uri())


if __name__ == "__main__":
    main()
