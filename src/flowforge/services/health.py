import logging

from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from flowforge.schemas.health import ComponentStatus

logger = logging.getLogger(__name__)


def check_database(db: Session) -> ComponentStatus:
    try:
        db.execute(text("SELECT 1"))
        return ComponentStatus(status="ok")
    except Exception as exc:
        logger.warning("database readiness check failed: %s", type(exc).__name__)
        return ComponentStatus(status="error", detail=type(exc).__name__)


def check_redis(client: Redis) -> ComponentStatus:
    try:
        client.ping()
        return ComponentStatus(status="ok")
    except Exception as exc:
        logger.warning("redis readiness check failed: %s", type(exc).__name__)
        return ComponentStatus(status="error", detail=type(exc).__name__)
