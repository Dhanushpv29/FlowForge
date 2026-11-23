from contextlib import asynccontextmanager

from fastapi import FastAPI

from flowforge import __version__
from flowforge.api.routes import health
from flowforge.core.config import get_settings
from flowforge.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(get_settings().log_level)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Distributed workflow orchestration engine.",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    return app


app = create_app()
