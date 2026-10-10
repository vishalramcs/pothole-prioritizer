"""Create an account. This is the only way to make an OFFICIAL account (citizens can also sign up on the website).

Run from backend/:  python scripts/create_user.py --role official --email officer@city.gov.in --name "Ward Officer"
The password is asked for without showing it (or pass --password for scripts).
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_engine  # noqa: E402
from app.services import auth  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--role", choices=["official", "citizen"], required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--password", help="omit to be asked (recommended: keeps it out of shell history)")
    args = ap.parse_args()
    password = args.password or getpass.getpass("Password (8+ characters): ")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters")
    with get_engine().begin() as conn:
        try:
            user = auth.create_user(conn, args.email, args.name, password, args.role)
        except auth.AuthError as exc:
            sys.exit(str(exc))
    print(f"Created {user['role']} account #{user['user_id']} for {user['email']}")


if __name__ == "__main__":
    main()
