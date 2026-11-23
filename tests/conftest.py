"""Shared fixtures.

Integration tests run against real PostgreSQL and Redis. Locally they are skipped
with a clear reason if the services are unreachable; CI sets REQUIRE_INTEGRATION=1
so an unreachable service fails the build instead of silently skipping.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import redis as redis_lib
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from alembic import command

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://flowforge:flowforge@localhost:5432/flowforge_test"
)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")

# Must be set before flowforge settings are first read.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL
os.environ["APP_ENV"] = "test"

ROOT = Path(__file__).resolve().parents[1]
REQUIRE_INTEGRATION = os.environ.get("REQUIRE_INTEGRATION") == "1"


def alembic_config(url: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.attributes["sqlalchemy_url"] = url
    return cfg


def _unavailable(reason: str) -> None:
    if REQUIRE_INTEGRATION:
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    eng = create_engine(TEST_DATABASE_URL)
    try:
        with eng.begin() as conn:
            # Start every test session from an empty schema, then apply real migrations.
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    except Exception as exc:  # pragma: no cover - depends on environment
        _unavailable(f"PostgreSQL not reachable at {TEST_DATABASE_URL}: {type(exc).__name__}")
    command.upgrade(alembic_config(TEST_DATABASE_URL), "head")
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back after each test (savepoint-aware)."""
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture(scope="session")
def redis_client() -> redis_lib.Redis:
    client = redis_lib.Redis.from_url(TEST_REDIS_URL, socket_connect_timeout=1)
    try:
        client.ping()
    except Exception as exc:  # pragma: no cover - depends on environment
        _unavailable(f"Redis not reachable at {TEST_REDIS_URL}: {type(exc).__name__}")
    return client


@pytest.fixture
def client(engine: Engine):
    """FastAPI test client wired to the migrated test database."""
    from fastapi.testclient import TestClient

    from flowforge.main import app

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
