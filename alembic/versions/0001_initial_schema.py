"""initial schema: workflows, task definitions, runs, task runs, workers

Revision ID: 0001
Revises:
Create Date: 2026-11-23 00:36:27.139208
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workers",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("worker_name", sa.String(length=120), nullable=False),
        sa.Column(
            "capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'stale', 'offline')", name=op.f("ck_workers_status")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workers")),
        sa.UniqueConstraint("worker_name", name=op.f("uq_workers_worker_name")),
    )
    op.create_table(
        "workflows",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("max_concurrent_runs", sa.Integer(), server_default="1", nullable=False),
        sa.Column("schedule_cron", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "max_concurrent_runs >= 1", name=op.f("ck_workflows_max_concurrent_runs_positive")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflows")),
    )
    op.create_table(
        "task_definitions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("task_key", sa.String(length=120), nullable=False),
        sa.Column("task_type", sa.String(length=120), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "dependencies",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("retry_backoff_seconds", sa.Integer(), server_default="5", nullable=False),
        sa.CheckConstraint(
            "max_retries >= 0", name=op.f("ck_task_definitions_max_retries_non_negative")
        ),
        sa.CheckConstraint(
            "retry_backoff_seconds >= 1", name=op.f("ck_task_definitions_retry_backoff_positive")
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            name=op.f("fk_task_definitions_workflow_id_workflows"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_definitions")),
        sa.UniqueConstraint(
            "workflow_id", "task_key", name="uq_task_definitions_workflow_task_key"
        ),
    )
    op.create_index(
        op.f("ix_task_definitions_workflow_id"), "task_definitions", ["workflow_id"], unique=False
    )
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column(
            "input_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            name=op.f("fk_workflow_runs_workflow_id_workflows"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name=op.f("ck_workflow_runs_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_runs")),
    )
    op.create_index(
        "ix_workflow_runs_workflow_id_status",
        "workflow_runs",
        ["workflow_id", "status"],
        unique=False,
    )
    op.create_table(
        "task_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workflow_run_id", sa.UUID(), nullable=False),
        sa.Column("task_key", sa.String(length=120), nullable=False),
        sa.Column("task_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="blocked", nullable=False),
        sa.Column(
            "dependencies",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("retry_backoff_seconds", sa.Integer(), server_default="5", nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.String(length=120), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("attempts >= 0", name=op.f("ck_task_runs_attempts_non_negative")),
        sa.CheckConstraint("max_retries >= 0", name=op.f("ck_task_runs_max_retries_non_negative")),
        sa.CheckConstraint(
            "retry_backoff_seconds >= 1", name=op.f("ck_task_runs_retry_backoff_positive")
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.id"],
            name=op.f("fk_task_runs_workflow_run_id_workflow_runs"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('blocked', 'queued', 'running', 'succeeded', 'retry_wait', 'dead_lettered', 'cancelled')",
            name=op.f("ck_task_runs_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_runs")),
        sa.UniqueConstraint(
            "workflow_run_id", "task_key", name="uq_task_runs_workflow_run_task_key"
        ),
    )
    op.create_index(
        "ix_task_runs_claimable",
        "task_runs",
        ["available_at", "created_at"],
        unique=False,
        postgresql_where=sa.text("status IN ('queued', 'retry_wait')"),
    )
    op.create_index(
        "ix_task_runs_lease_expiry",
        "task_runs",
        ["lease_expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'running'"),
    )
    op.create_index(
        "ix_task_runs_workflow_run_id_status",
        "task_runs",
        ["workflow_run_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_task_runs_workflow_run_id_status", table_name="task_runs")
    op.drop_index(
        "ix_task_runs_lease_expiry",
        table_name="task_runs",
        postgresql_where=sa.text("status = 'running'"),
    )
    op.drop_index(
        "ix_task_runs_claimable",
        table_name="task_runs",
        postgresql_where=sa.text("status IN ('queued', 'retry_wait')"),
    )
    op.drop_table("task_runs")
    op.drop_index("ix_workflow_runs_workflow_id_status", table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_index(op.f("ix_task_definitions_workflow_id"), table_name="task_definitions")
    op.drop_table("task_definitions")
    op.drop_table("workflows")
    op.drop_table("workers")
