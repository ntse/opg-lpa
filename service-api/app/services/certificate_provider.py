from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.applications import ApplicationsService, default_document
from app.services.repositories import ApplicationRepository


class CertificateProviderService:
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
            raise HTTPException(status_code=400, detail="Invalid certificate provider payload")

        record = await self.applications.get_record(user_id, application_id)
        document = {**default_document(), **(record.document or {})}
        document["certificateProvider"] = payload

        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to update certificate provider")

        return payload

    async def delete(self, user_id: str, application_id: int) -> None:
        record = await self.applications.get_record(user_id, application_id)
        document = {**default_document(), **(record.document or {})}

        if document.get("certificateProvider") is None:
            return

        document["certificateProvider"] = None
        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to delete certificate provider")


__all__ = ["CertificateProviderService"]
