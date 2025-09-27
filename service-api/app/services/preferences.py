from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.applications import ApplicationsService, default_document
from app.services.repositories import ApplicationRepository


class PreferenceService:
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        self.applications = applications
        self.repository = repository

    async def update(
        self,
        user_id: str,
        application_id: int,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        preference = None
        if payload is not None:
            preference = payload.get("preference")

        if preference not in (None, False) and not isinstance(preference, str):
            raise HTTPException(status_code=400, detail="Invalid preference")

        record = await self.applications.get_record(user_id, application_id)
        base_document = record.document or {}
        document = {**default_document(), **base_document}
        document["preference"] = preference

        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to update preference")

        if isinstance(preference, str) or preference is False:
            return {"preference": preference}
        return {}


__all__ = ["PreferenceService"]
