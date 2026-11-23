import enum


class RunStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(enum.StrEnum):
    BLOCKED = "blocked"  # waiting for dependencies
    QUEUED = "queued"  # ready to be claimed
    RUNNING = "running"  # claimed by a worker, lease active
    SUCCEEDED = "succeeded"
    RETRY_WAIT = "retry_wait"  # failed, will be retried after available_at
    DEAD_LETTERED = "dead_lettered"  # retries exhausted; needs operator action
    CANCELLED = "cancelled"  # upstream dead-lettered or run cancelled


class WorkerStatus(enum.StrEnum):
    ACTIVE = "active"
    STALE = "stale"  # heartbeat overdue
    OFFLINE = "offline"
