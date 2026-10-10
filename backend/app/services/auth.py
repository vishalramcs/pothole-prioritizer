"""Passwords and sessions. Standard library only: scrypt for passwords, random tokens for sessions."""
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection
from sqlalchemy.exc import IntegrityError

from app.repositories import users

SESSION_DAYS = 7
_N, _R, _P = 2**14, 8, 1  # scrypt cost: tens of milliseconds per check on a laptop


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p))
    except ValueError:
        return False
    return hmac.compare_digest(got.hex(), digest)


_DUMMY = hash_password(secrets.token_hex(8))  # an unknown email costs as much time as a wrong password


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user(conn: Connection, email: str, name: str, password: str, role: str) -> dict:
    try:
        with conn.begin_nested():  # a duplicate email must not abort the caller's transaction
            return users.insert(conn, email.strip().lower(), name.strip(), hash_password(password), role)
    except IntegrityError:
        raise AuthError("An account with this email already exists", 409)


def login(conn: Connection, email: str, password: str, role: str) -> tuple[dict, str]:
    """The user and a new session token. One message for a wrong email or password, so it doesn't reveal
    which emails have accounts."""
    user = users.get_by_email(conn, email.strip().lower())
    if not check_password(password, user["password_hash"] if user else _DUMMY) or user is None:
        raise AuthError("Wrong email or password", 401)
    if user["role"] != role:
        raise AuthError("This is an official account: choose Official" if user["role"] == "official"
                        else "This is a citizen account: choose Citizen", 403)
    token = secrets.token_urlsafe(32)
    users.add_session(conn, token_hash(token), user["user_id"], datetime.now(UTC) + timedelta(days=SESSION_DAYS))
    return {k: user[k] for k in ("user_id", "email", "name", "role")}, token


def user_for_token(conn: Connection, token: str | None) -> dict | None:
    return users.user_for_session(conn, token_hash(token)) if token else None


def logout(conn: Connection, token: str | None) -> None:
    if token:
        users.delete_session(conn, token_hash(token))
