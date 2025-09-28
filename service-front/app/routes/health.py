"""Health check endpoints."""
from datetime import UTC, datetime

from fastapi import APIRouter, status
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", status_code=status.HTTP_200_OK)
def health_check() -> dict[str, str]:
    """Return a simple health payload used by probes."""

    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/ping", status_code=status.HTTP_200_OK)
def ping() -> dict[str, str]:
    """Compatibility endpoint mirroring the legacy ping route."""

    return {"ping": "pong", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/ping/json", status_code=status.HTTP_200_OK)
def ping_json() -> dict[str, str]:
    """Return a JSON payload expected by older monitoring checks."""

    return {"ping": "pong", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/ping/pingdom", status_code=status.HTTP_200_OK, response_class=PlainTextResponse)
def ping_pingdom() -> PlainTextResponse:
    """Serve the plain text response used by the legacy Pingdom checks."""

    return PlainTextResponse("OK")
