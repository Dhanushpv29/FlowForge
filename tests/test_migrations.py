import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from alembic import command
from tests.conftest import TEST_DATABASE_URL, alembic_config

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {"workflows", "task_definitions", "workflow_runs", "task_runs", "workers"}


@pytest.fixture
def scratch_url(engine):
    """An empty throwaway database so migration tests never touch the shared test DB."""
    name = f"ff_mig_{uuid.uuid4().hex[:10]}"
    admin = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(TEST_DATABASE_URL).set(database=name).render_as_string(hide_password=False)
    yield url
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def table_names(url):
    eng = create_engine(url)
    try:
        return set(inspect(eng).get_table_names()) - {"alembic_version"}
    finally:
        eng.dispose()


def test_upgrade_creates_all_tables_and_downgrade_removes_them(scratch_url):
    cfg = alembic_config(scratch_url)
    command.upgrade(cfg, "head")
    assert table_names(scratch_url) == EXPECTED_TABLES
    command.downgrade(cfg, "base")
    assert table_names(scratch_url) == set()
    command.upgrade(cfg, "head")  # re-applies cleanly after a downgrade
    assert table_names(scratch_url) == EXPECTED_TABLES


def test_models_and_migrations_are_in_sync(scratch_url):
    """Fails if someone changes a model without writing a migration."""
    cfg = alembic_config(scratch_url)
    command.upgrade(cfg, "head")
    command.check(cfg)  # raises CommandError when autogenerate detects drift


def test_scheduler_indexes_exist_and_are_partial(scratch_url):
    command.upgrade(alembic_config(scratch_url), "head")
    eng = create_engine(scratch_url)
    try:
        with eng.connect() as conn:
            rows = conn.execute(
                text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'task_runs'")
            ).all()
    finally:
        eng.dispose()
    defs = {name: definition for name, definition in rows}
    assert "WHERE" in defs["ix_task_runs_claimable"]
    assert "WHERE" in defs["ix_task_runs_lease_expiry"]
    assert "ix_task_runs_workflow_run_id_status" in defs
