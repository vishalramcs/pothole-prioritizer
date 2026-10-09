"""Database access: one SQLAlchemy engine, one transaction per request."""
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

_engine: Engine | None = None


def normalize_database_url(url: str) -> str:
    """Supabase gives postgres:// or postgresql:// URLs; SQLAlchemy needs the psycopg (v3) driver name."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not set")
        kwargs = {"poolclass": NullPool} if settings.db_use_nullpool else {"pool_pre_ping": True}
        _engine = create_engine(normalize_database_url(settings.database_url), **kwargs)
    return _engine


def get_conn() -> Iterator[Connection]:
    """FastAPI dependency. Commits when the request succeeds, rolls back if it raises.

    Plan generation and zone recompute (TRD 4.6, 4.7) rely on this being ONE transaction.
    """
    with get_engine().begin() as conn:
        yield conn


# Use this in routes, not Depends(get_conn) directly. scope="function" commits BEFORE the response
# is sent; FastAPI's default runs it after, so a failed commit would still reach the client as 200.
Conn = Annotated[Connection, Depends(get_conn, scope="function")]
