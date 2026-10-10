import os

import pytest

# Tests must not depend on a developer's real .env
os.environ.setdefault("DATABASE_URL", "")
os.environ["DEMO_LOGIN"] = "false"  # tests check real passwords; demo mode is tested by switching it on

TEST_DB = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def conn():
    """A connection to TEST_DATABASE_URL (migrated + seeded) inside a transaction that is always rolled back."""
    if not TEST_DB:
        pytest.skip("set TEST_DATABASE_URL to run")
    from sqlalchemy import create_engine, text

    from app.core.db import normalize_database_url

    engine = create_engine(normalize_database_url(TEST_DB))
    with engine.connect() as c:
        tx = c.begin()
        # the app's own roads come from OpenStreetMap; tests use four fixed roads (same values as the old seed)
        c.execute(text("""INSERT INTO roads (name, road_type, importance_score, traffic_score, data_source) VALUES
            ('Test Highway', 'highway', 1.0, 0.90, 'mock'), ('Test Main Road', 'arterial', 0.8, 0.70, 'mock'),
            ('Test Market Street', 'collector', 0.5, 0.60, 'mock'), ('Test Lane', 'local', 0.3, 0.20, 'mock')"""))
        yield c
        tx.rollback()
    engine.dispose()


@pytest.fixture
def api(conn, tmp_path, monkeypatch):
    """Makes API clients whose requests all run inside the rolled-back test transaction, storing files in
    tmp_path. api() is logged out; api("citizen") / api("official") is logged in as a new user of that role."""
    from fastapi.testclient import TestClient

    from app.core.db import get_conn
    from app.main import app
    from app.services import auth, storage

    monkeypatch.setattr(storage, "LOCAL_DIR", tmp_path)
    app.dependency_overrides[get_conn] = lambda: conn
    made = 0

    def make(role: str | None = None) -> TestClient:
        nonlocal made
        c = TestClient(app)
        if role:
            made += 1
            email = f"{role}{made}@test.example"
            auth.create_user(conn, email, f"Test {role}", "test-password", role)
            assert c.post("/api/auth/login", json={"email": email, "password": "test-password", "role": role}).status_code == 200
        return c

    yield make
    app.dependency_overrides.clear()


@pytest.fixture
def client(api):
    """Logged in as an official: can use every endpoint."""
    return api("official")
