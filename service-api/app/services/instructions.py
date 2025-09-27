from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.applications import ApplicationsService, default_document
from app.services.repositories import ApplicationRepository


class InstructionService:
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        self.applications = applications
        self.repository = repository

    async def update(
        self,
        user_id: str,
        application_id: int,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        instruction = None
        if payload is not None:
            instruction = payload.get("instruction")

        if instruction not in (None, False) and not isinstance(instruction, str):
            raise HTTPException(status_code=400, detail="Invalid instruction")

        record = await self.applications.get_record(user_id, application_id)
        base_document = record.document or {}
        document = {**default_document(), **base_document}
        document["instruction"] = instruction

        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to update instruction")

        if isinstance(instruction, str) or instruction is False:
            return {"instruction": instruction}
        return {}


__all__ = ["InstructionService"]
