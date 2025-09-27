from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.applications import ApplicationsService, default_document
from app.services.repositories import ApplicationRepository


class TypeService:
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        self.applications = applications
        self.repository = repository

    async def update(
        self,
        user_id: str,
        application_id: int,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if payload is None or not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid type payload")

        app_type = payload.get("type")
        if app_type is not None and not isinstance(app_type, str):
            raise HTTPException(status_code=400, detail="Invalid type value")

        record = await self.applications.get_record(user_id, application_id)
        document = {**default_document(), **(record.document or {})}
        document["type"] = app_type

        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to update type")

        if app_type is None:
            return {}
        return {"type": app_type}


__all__ = ["TypeService"]
