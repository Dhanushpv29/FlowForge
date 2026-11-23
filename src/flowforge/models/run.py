import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge.db.base import Base
from flowforge.models.enums import RunStatus, TaskStatus
from flowforge.models.types import status_enum
from flowforge.models.workflow import UUID_PK_DEFAULT


class WorkflowRun(Base):
    """One execution of a workflow."""

    __tablename__ = "workflow_runs"
    __table_args__ = (Index("ix_workflow_runs_workflow_id_status", "workflow_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=UUID_PK_DEFAULT
    )
    # RESTRICT: a workflow with execution history cannot be deleted by accident.
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="RESTRICT"))
    status: Mapped[RunStatus] = mapped_column(
        status_enum(RunStatus, "status", 16), default=RunStatus.QUEUED, server_default="queued"
    )
    input_payload: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tasks: Mapped[list["TaskRun"]] = relationship(
        back_populates="workflow_run", cascade="all, delete-orphan", passive_deletes=True
    )


class TaskRun(Base):
    """The execution state of one task inside one workflow run.

    This table is the scheduler's work queue: claiming, leases, retries and
    dead-lettering are all expressed as state transitions on these rows.
    """

    __tablename__ = "task_runs"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "task_key", name="uq_task_runs_workflow_run_task_key"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        CheckConstraint("max_retries >= 0", name="max_retries_non_negative"),
        CheckConstraint("retry_backoff_seconds >= 1", name="retry_backoff_positive"),
        # Dependency resolution: "which tasks of this run are in state X?"
        Index("ix_task_runs_workflow_run_id_status", "workflow_run_id", "status"),
        # The claim query (SKIP LOCKED) scans only rows that can be claimed.
        Index(
            "ix_task_runs_claimable",
            "available_at",
            "created_at",
            postgresql_where=text("status IN ('queued', 'retry_wait')"),
        ),
        # Crash recovery scans only running rows, ordered by lease expiry.
        Index(
            "ix_task_runs_lease_expiry",
            "lease_expires_at",
            postgresql_where=text("status = 'running'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=UUID_PK_DEFAULT
    )
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE")
    )
    task_key: Mapped[str] = mapped_column(String(120))
    task_type: Mapped[str] = mapped_column(String(120))
    status: Mapped[TaskStatus] = mapped_column(
        status_enum(TaskStatus, "status", 20), default=TaskStatus.BLOCKED, server_default="blocked"
    )
    dependencies: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_retries: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[str | None] = mapped_column(String(120))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workflow_run: Mapped[WorkflowRun] = relationship(back_populates="tasks")
