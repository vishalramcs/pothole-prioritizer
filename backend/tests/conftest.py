import os

import pytest

# Tests must not depend on a developer's real .env
os.environ.setdefault("DATABASE_URL", "")

TEST_DB = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def conn():
    """A connection to TEST_DATABASE_URL (migrated + seeded) inside a transaction that is always rolled back."""
    if not TEST_DB:
        pytest.skip("set TEST_DATABASE_URL to run")
    from sqlalchemy import create_engine

    from app.core.db import normalize_database_url

    engine = create_engine(normalize_database_url(TEST_DB))
    with engine.connect() as c:
        tx = c.begin()
        yield c
        tx.rollback()
    engine.dispose()


@pytest.fixture
def client(conn, tmp_path, monkeypatch):
    """API client whose requests all run inside the rolled-back test transaction, storing files in tmp_path."""
    from fastapi.testclient import TestClient

    from app.core.db import get_conn
    from app.main import app
    from app.services import storage

    monkeypatch.setattr(storage, "LOCAL_DIR", tmp_path)
    app.dependency_overrides[get_conn] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()
