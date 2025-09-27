from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session as BotoSession
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text

from app.config import get_settings
from app.core.database import database

router = APIRouter(tags=["health"])


@dataclass(slots=True)
class QueueStatus:
    available: bool
    length: int | None
    length_acceptable: bool


async def _check_database() -> bool:
    try:
        async with database.engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_queue() -> tuple[bool, QueueStatus]:
    settings = get_settings()
    if not settings.sqs_queue_url:
        return False, QueueStatus(available=False, length=None, length_acceptable=False)

    session = boto3.session.Session()
    region = session.region_name or "eu-west-1"
    client = session.client("sqs", region_name=region)

    try:
        response = await run_in_threadpool(
            client.get_queue_attributes,
            QueueUrl=settings.sqs_queue_url,
            AttributeNames=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
            ],
        )
        attributes = response.get("Attributes", {})
        visible = int(attributes.get("ApproximateNumberOfMessages", 0))
        not_visible = int(attributes.get("ApproximateNumberOfMessagesNotVisible", 0))
        total = visible + not_visible
        acceptable = total < settings.pdf_queue_warn_threshold
        return acceptable, QueueStatus(True, total, acceptable)
    except Exception:
        return False, QueueStatus(False, None, False)


async def _check_gateway() -> bool:
    settings = get_settings()
    endpoint = settings.track_my_lpa_endpoint
    if not endpoint:
        return False

    boto_session = BotoSession()
    credentials = boto_session.get_credentials()
    region = boto_session.region_name or "eu-west-1"

    if credentials is None:
        return False

    url = endpoint.rstrip("/") + "/healthcheck"

    request = AWSRequest(method="GET", url=url, headers={"Accept": "application/json"})
    SigV4Auth(credentials, "execute-api", region).add_auth(request)

    headers = dict(request.headers.items())

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
        return response.status_code == 200
    except Exception:
        return False


def _overall_status(database_ok: bool, queue_ok: bool, gateway_ok: bool) -> str:
    if database_ok and queue_ok and gateway_ok:
        return "PASS"
    if database_ok and queue_ok:
        return "WARN"
    return "FAIL"


@router.get("/ping")
async def ping() -> dict[str, Any]:
    db_ok, (queue_ok, queue_status), gateway_ok = await asyncio.gather(
        _check_database(),
        _check_queue(),
        _check_gateway(),
    )

    ok = db_ok and queue_ok
    status = _overall_status(db_ok, queue_ok, gateway_ok)

    return {
        "database": {"ok": db_ok},
        "gateway": {"ok": gateway_ok},
        "queue": {
            "ok": queue_ok,
            "details": {
                "available": queue_status.available,
                "length": queue_status.length,
                "lengthAcceptable": queue_status.length_acceptable,
            },
        },
        "ok": ok,
        "status": status,
    }


@router.get("/ping/elb")
async def ping_elb() -> dict[str, bool]:
    return {"ok": True}


__all__ = ["router"]
