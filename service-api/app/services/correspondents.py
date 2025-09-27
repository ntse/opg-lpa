from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.applications import ApplicationsService, default_document
from app.services.repositories import ApplicationRepository


class CorrespondentService:
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
            raise HTTPException(status_code=400, detail="Invalid correspondent payload")

        record = await self.applications.get_record(user_id, application_id)
        base_document = record.document or {}
        document = {**default_document(), **base_document}
        document["correspondent"] = payload

        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to update correspondent")

        return payload

    async def delete(self, user_id: str, application_id: int) -> None:
        record = await self.applications.get_record(user_id, application_id)
        base_document = record.document or {}
        if base_document.get("correspondent") is None:
            # deletion is idempotent; nothing to do
            return

        document = {**default_document(), **base_document}
        document["correspondent"] = None

        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to delete correspondent")


__all__ = ["CorrespondentService"]
