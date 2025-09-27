from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.applications import ApplicationsService
from app.services.repositories import ApplicationRepository


class WhoAreYouService:
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
            raise HTTPException(status_code=400, detail="Invalid who-are-you payload")

        record = await self.applications.get_record(user_id, application_id)

        if record.metadata and record.metadata.get("whoAreYouAnswered"):
            raise HTTPException(status_code=403, detail="Question already answered")

        answer = dict(payload)

        metadata = dict(record.metadata or {})
        metadata["whoAreYouAnswered"] = True
        metadata["whoAreYouAnswer"] = answer

        updated = await self.repository.update_application(
            application_id,
            user_id,
            metadata=metadata,
            who_are_you_answered=True,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to persist who-are-you answer")

        return {"whoAreYouAnswered": True}


__all__ = ["WhoAreYouService"]
