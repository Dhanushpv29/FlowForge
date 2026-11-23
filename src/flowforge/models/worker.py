import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from flowforge.db.base import Base
from flowforge.models.enums import WorkerStatus
from flowforge.models.types import status_enum
from flowforge.models.workflow import UUID_PK_DEFAULT


class Worker(Base):
    """A registered worker process. Heartbeats keep `last_heartbeat_at` fresh."""

    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=UUID_PK_DEFAULT
    )
    worker_name: Mapped[str] = mapped_column(String(120), unique=True)
    capabilities: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    status: Mapped[WorkerStatus] = mapped_column(
        status_enum(WorkerStatus, "status", 20),
        default=WorkerStatus.ACTIVE,
        server_default="active",
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
