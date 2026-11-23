import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
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

UUID_PK_DEFAULT = text("gen_random_uuid()")


class Workflow(Base):
    """A registered workflow: a named DAG of task definitions."""

    __tablename__ = "workflows"
    __table_args__ = (
        CheckConstraint("max_concurrent_runs >= 1", name="max_concurrent_runs_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=UUID_PK_DEFAULT
    )
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    max_concurrent_runs: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    schedule_cron: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tasks: Mapped[list["TaskDefinition"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", passive_deletes=True
    )


class TaskDefinition(Base):
    """One node of a workflow DAG. `dependencies` holds the task_keys it waits for."""

    __tablename__ = "task_definitions"
    __table_args__ = (
        UniqueConstraint("workflow_id", "task_key", name="uq_task_definitions_workflow_task_key"),
        CheckConstraint("max_retries >= 0", name="max_retries_non_negative"),
        CheckConstraint("retry_backoff_seconds >= 1", name="retry_backoff_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=UUID_PK_DEFAULT
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    task_key: Mapped[str] = mapped_column(String(120))
    task_type: Mapped[str] = mapped_column(String(120))
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    dependencies: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    max_retries: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, default=5, server_default="5")

    workflow: Mapped[Workflow] = relationship(back_populates="tasks")
