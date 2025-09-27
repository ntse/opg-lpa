from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.applications import ApplicationsService
from app.services.repositories import ApplicationRepository


class RepeatCaseNumberService:
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        self.applications = applications
        self.repository = repository

    @staticmethod
    def _normalise(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise HTTPException(status_code=400, detail="Invalid repeatCaseNumber")
        if isinstance(value, (int, float)):
            if isinstance(value, float) and not value.is_integer():
                raise HTTPException(status_code=400, detail="Invalid repeatCaseNumber")
            num = int(value)
            if num < 0:
                raise HTTPException(status_code=400, detail="Invalid repeatCaseNumber")
            return num
        if isinstance(value, str):
            if not value.strip():
                return None
            if not value.isdigit():
                raise HTTPException(status_code=400, detail="Invalid repeatCaseNumber")
            return int(value)
        raise HTTPException(status_code=400, detail="Invalid repeatCaseNumber")

    async def update(
        self,
        user_id: str,
        application_id: int,
        payload: dict[str, Any] | None,
    ) -> dict[str, int]:
        if payload is None:
            raise HTTPException(status_code=400, detail="Invalid repeatCaseNumber payload")

        repeat_case_number = self._normalise(payload.get("repeatCaseNumber"))

        record = await self.applications.get_record(user_id, application_id)

        updated = await self.repository.update_application(
            application_id,
            user_id,
            repeat_case_number=repeat_case_number,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to update repeat case number")

        if repeat_case_number is None:
            return {}
        return {"repeatCaseNumber": repeat_case_number}

    async def delete(self, user_id: str, application_id: int) -> None:
        await self.update(user_id, application_id, {"repeatCaseNumber": None})


__all__ = ["RepeatCaseNumberService"]
