from fastapi import APIRouter, Depends, Response
from redis import Redis
from sqlalchemy.orm import Session

from flowforge import __version__
from flowforge.api.deps import get_db, get_redis
from flowforge.core.config import get_settings
from flowforge.schemas.health import LivenessResponse, ReadinessResponse
from flowforge.services.health import check_database, check_redis

router = APIRouter(tags=["system"])


@router.get("/health", response_model=LivenessResponse)
def health() -> LivenessResponse:
    """Liveness: the process is up. Never touches dependencies."""
    return LivenessResponse(status="ok", service=get_settings().app_name, version=__version__)


@router.get(
    "/ready", response_model=ReadinessResponse, responses={503: {"model": ReadinessResponse}}
)
def ready(
    response: Response, db: Session = Depends(get_db), redis: Redis = Depends(get_redis)
) -> ReadinessResponse:
    """Readiness: PostgreSQL and Redis are reachable. Returns 503 if either is not."""
    components = {"database": check_database(db), "redis": check_redis(redis)}
    healthy = all(c.status == "ok" for c in components.values())
    if not healthy:
        response.status_code = 503
    return ReadinessResponse(status="ok" if healthy else "degraded", components=components)
