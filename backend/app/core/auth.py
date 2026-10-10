"""Who is calling: FastAPI dependencies for the two roles (citizen, official).

The session token travels in an HttpOnly cookie, so page scripts cannot read it, and the browser also
sends it with <img> requests for upload photos.
"""
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException

from app.core.db import Conn
from app.services import auth

COOKIE = "srpps_session"


def current_user(conn: Conn, srpps_session: Annotated[str | None, Cookie()] = None) -> dict:
    user = auth.user_for_token(conn, srpps_session)
    if user is None:
        raise HTTPException(401, "Please log in")
    return user


def require_official(user: Annotated[dict, Depends(current_user)]) -> dict:
    if user["role"] != "official":
        raise HTTPException(403, "Only officials can do this")
    return user


User = Annotated[dict, Depends(current_user)]
Official = Annotated[dict, Depends(require_official)]
