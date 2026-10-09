import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app as real_app

needs_db = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="set TEST_DATABASE_URL to run")


def test_errors_use_error_key():
    r = TestClient(real_app).get("/api/no-such-route")
    assert r.status_code == 404
    assert r.json() == {"error": "Not Found"}


@needs_db
def test_failed_commit_is_reported_to_client(monkeypatch):
    """A commit that fails must turn into an error response, not a 200 sent before the commit."""
    import app.core.db as db
    from app.core.config import get_settings

    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    get_settings.cache_clear()
    db._engine = None

    probe = FastAPI()

    @probe.post("/write")
    def write(conn: db.Conn) -> dict:
        # duplicate rows under a DEFERRED unique constraint only fail at COMMIT
        conn.execute(text("INSERT INTO tx_probe VALUES (1), (1)"))
        return {"saved": True}

    with db.get_engine().begin() as c:
        c.execute(text("CREATE TABLE tx_probe (id int, CONSTRAINT tx_probe_u UNIQUE (id) DEFERRABLE INITIALLY DEFERRED)"))
    try:
        r = TestClient(probe, raise_server_exceptions=False).post("/write")
        assert r.status_code == 500
    finally:
        with db.get_engine().begin() as c:
            c.execute(text("DROP TABLE tx_probe"))
        get_settings.cache_clear()
        db._engine = None
