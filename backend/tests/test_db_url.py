import os

import pytest
from sqlalchemy import text

from app.core.db import normalize_database_url


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("postgres://u:p@h:5432/postgres", "postgresql+psycopg://u:p@h:5432/postgres"),
        ("postgresql://u:p@h:6543/postgres", "postgresql+psycopg://u:p@h:6543/postgres"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ],
)
def test_normalize_database_url(raw, expected):
    assert normalize_database_url(raw) == expected


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="set TEST_DATABASE_URL to run")
def test_can_connect_and_foreign_keys_exist():
    from sqlalchemy import create_engine

    engine = create_engine(normalize_database_url(os.environ["TEST_DATABASE_URL"]))
    with engine.connect() as conn:
        assert conn.execute(text("select 1")).scalar() == 1
        n = conn.execute(text("select count(*) from information_schema.table_constraints "
                              "where constraint_type='FOREIGN KEY' and table_schema='public'")).scalar()
        assert n >= 1
