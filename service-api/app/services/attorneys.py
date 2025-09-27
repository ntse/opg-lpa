from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List

from fastapi import HTTPException

from app.services.applications import ApplicationsService, default_document
from app.services.repositories import ApplicationRepository


class _AttorneyServiceBase:
    def __init__(self, key: str, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        self.key = key
        self.applications = applications
        self.repository = repository

    async def create(self, user_id: str, application_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        record = await self.applications.get_record(user_id, application_id)
        document = record.document or default_document()
        attorneys = list(document.get(self.key) or [])

        new_attorney = dict(payload)
        new_id = int(new_attorney.get("id", 0))
        if new_id <= 0:
            new_id = self._next_id(attorneys)
        new_attorney["id"] = new_id

        attorneys.append(new_attorney)
        document[self.key] = attorneys

        await self._persist(user_id, application_id, document)
        return new_attorney

    async def update(
        self,
        user_id: str,
        application_id: int,
        attorney_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        record = await self.applications.get_record(user_id, application_id)
        document = record.document or default_document()
        attorneys = list(document.get(self.key) or [])

        for idx, existing in enumerate(attorneys):
            if int(existing.get("id", 0)) == attorney_id:
                updated = dict(payload)
                updated["id"] = attorney_id
                attorneys[idx] = updated
                document[self.key] = attorneys
                await self._persist(user_id, application_id, document)
                return updated

        raise HTTPException(status_code=404, detail="Attorney not found")

    async def delete(self, user_id: str, application_id: int, attorney_id: int) -> None:
        record = await self.applications.get_record(user_id, application_id)
        document = record.document or default_document()
        attorneys = list(document.get(self.key) or [])

        filtered = [item for item in attorneys if int(item.get("id", 0)) != attorney_id]
        if len(filtered) == len(attorneys):
            raise HTTPException(status_code=404, detail="Attorney not found")

        document[self.key] = filtered
        await self._persist(user_id, application_id, document)

    async def _persist(self, user_id: str, application_id: int, document: dict[str, Any]) -> None:
        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to update application")

    @staticmethod
    def _next_id(attorneys: List[dict[str, Any]]) -> int:
        existing = [int(item.get("id", 0)) for item in attorneys if str(item.get("id"))]
        return (max(existing) if existing else 0) + 1


class PrimaryAttorneyService(_AttorneyServiceBase):
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        super().__init__("primaryAttorneys", applications, repository)


class ReplacementAttorneyService(_AttorneyServiceBase):
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        super().__init__("replacementAttorneys", applications, repository)


__all__ = ["PrimaryAttorneyService", "ReplacementAttorneyService"]
