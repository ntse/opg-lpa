from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from app.services.applications import ApplicationsService
from app.services.repositories import ApplicationRepository
from app.utils import format_lpa_datetime


class LockService:
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        self.applications = applications
        self.repository = repository

    async def lock(self, user_id: str, application_id: int) -> dict[str, str | bool | None]:
        record = await self.applications.get_record(user_id, application_id)

        if record.locked:
            raise HTTPException(status_code=403, detail="LPA already locked")

        locked_at = datetime.now(timezone.utc)
        updated = await self.repository.update_application(
            application_id,
            user_id,
            locked=True,
            locked_at=locked_at,
            updated_at=locked_at,
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to lock LPA")

        return {
            "locked": True,
            "lockedAt": format_lpa_datetime(locked_at),
        }


__all__ = ["LockService"]
