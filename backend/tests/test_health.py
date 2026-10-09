from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_db_returns_503_without_database(monkeypatch):
    import app.core.db as db
    from app.core.config import get_settings

    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    db._engine = None
    r = client.get("/api/health/db")
    assert r.status_code == 503
