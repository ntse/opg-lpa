from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.applications import ApplicationsService, default_document
from app.services.repositories import ApplicationRepository


class WhoIsRegisteringService:
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        self.applications = applications
        self.repository = repository

    async def update(
        self,
        user_id: str,
        application_id: int,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        value = None
        if payload is not None:
            value = payload.get("whoIsRegistering")

        record = await self.applications.get_record(user_id, application_id)
        document = {**default_document(), **(record.document or {})}
        document["whoIsRegistering"] = value

        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to update who-is-registering")

        if value is None:
            return {}
        return {"whoIsRegistering": value}


__all__ = ["WhoIsRegisteringService"]
