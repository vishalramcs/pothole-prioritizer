"""POST /api/auth/register (citizens only), /login, /logout; GET /api/auth/me"""
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response

from app.core.auth import COOKIE, User
from app.core.config import get_settings
from app.core.db import Conn
from app.schemas import LoginIn, RegisterIn
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE, token, max_age=auth.SESSION_DAYS * 86400, httponly=True, samesite="lax",
                        secure=get_settings().cookie_secure, path="/")


@router.post("/register")
def register(conn: Conn, body: RegisterIn, response: Response) -> dict:
    """Citizens sign up here. Officials are created by an administrator (scripts/create_user.py)."""
    try:
        auth.create_user(conn, body.email, body.name, body.password, "citizen")
        user, token = auth.login(conn, body.email, body.password, "citizen")
    except auth.AuthError as exc:
        raise HTTPException(exc.status_code, str(exc))
    _set_cookie(response, token)
    return user


@router.post("/login")
def login(conn: Conn, body: LoginIn, response: Response) -> dict:
    try:
        user, token = auth.login(conn, body.email, body.password, body.role)
    except auth.AuthError as exc:
        raise HTTPException(exc.status_code, str(exc))
    _set_cookie(response, token)
    return user


@router.post("/logout")
def logout(conn: Conn, response: Response, srpps_session: Annotated[str | None, Cookie()] = None) -> dict:
    auth.logout(conn, srpps_session)
    response.delete_cookie(COOKIE, path="/")
    return {"status": "logged out"}


@router.get("/me")
def me(user: User) -> dict:
    return user
