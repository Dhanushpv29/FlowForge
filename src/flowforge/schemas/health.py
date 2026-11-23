from typing import Literal

from pydantic import BaseModel


class ComponentStatus(BaseModel):
    status: Literal["ok", "error"]
    detail: str | None = None


class LivenessResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    components: dict[str, ComponentStatus]
