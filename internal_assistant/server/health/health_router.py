from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, ConfigDict

# Not authentication or authorization required to get the health status.
health_router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(default="ok")
    model_config = ConfigDict(arbitrary_types_allowed=True)


@health_router.get("/health", tags=["Health"])
def health() -> HealthResponse:
    """Return ok if the system is up."""
    return HealthResponse(status="ok")
