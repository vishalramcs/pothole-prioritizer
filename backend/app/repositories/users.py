"""SQL for the users and sessions tables."""
from datetime import datetime

from sqlalchemy import Connection, text


def insert(conn: Connection, email: str, name: str, password_hash: str, role: str) -> dict:
    row = conn.execute(text("""INSERT INTO users (email, name, password_hash, role)
        VALUES (:email, :name, :password_hash, :role) RETURNING user_id, email, name, role"""),
        {"email": email, "name": name, "password_hash": password_hash, "role": role}).mappings().one()
    return dict(row)


def get_by_email(conn: Connection, email: str) -> dict | None:
    """Includes password_hash: for checking a login only, never sent to a client."""
    row = conn.execute(text("SELECT * FROM users WHERE email = :e"), {"e": email}).mappings().first()
    return dict(row) if row else None


def add_session(conn: Connection, token_hash: str, user_id: int, expires_at: datetime) -> None:
    conn.execute(text("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (:t, :u, :x)"),
                 {"t": token_hash, "u": user_id, "x": expires_at})


def user_for_session(conn: Connection, token_hash: str) -> dict | None:
    row = conn.execute(text("""SELECT u.user_id, u.email, u.name, u.role
        FROM sessions s JOIN users u ON u.user_id = s.user_id
        WHERE s.token_hash = :t AND s.expires_at > now()"""), {"t": token_hash}).mappings().first()
    return dict(row) if row else None


def delete_session(conn: Connection, token_hash: str) -> None:
    """Logs this session out and clears expired ones while at it."""
    conn.execute(text("DELETE FROM sessions WHERE token_hash = :t OR expires_at <= now()"), {"t": token_hash})
