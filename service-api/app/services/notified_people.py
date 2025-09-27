from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.applications import ApplicationsService, default_document
from app.services.repositories import ApplicationRepository


class NotifiedPeopleService:
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        self.applications = applications
        self.repository = repository

    def _normalise_id(self, value: Any | None, existing: list[dict[str, Any]]) -> int:
        if value is None:
            current_ids = [int(item.get("id", 0)) for item in existing if str(item.get("id"))]
            return (max(current_ids) if current_ids else 0) + 1
        if isinstance(value, bool):
            raise HTTPException(status_code=400, detail="Invalid notified person id")
        if isinstance(value, (int, float)):
            if isinstance(value, float) and not value.is_integer():
                raise HTTPException(status_code=400, detail="Invalid notified person id")
            candidate = int(value)
        elif isinstance(value, str):
            if not value.strip().isdigit():
                raise HTTPException(status_code=400, detail="Invalid notified person id")
            candidate = int(value)
        else:
            raise HTTPException(status_code=400, detail="Invalid notified person id")
        if candidate <= 0:
            raise HTTPException(status_code=400, detail="Invalid notified person id")
        return candidate

    async def create(
        self,
        user_id: str,
        application_id: int,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if payload is None or not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid notified person payload")

        record = await self.applications.get_record(user_id, application_id)
        base_document = record.document or {}
        document = {**default_document(), **base_document}
        people = list(document.get("peopleToNotify") or [])

        person = dict(payload)
        person_id = self._normalise_id(person.get("id"), people)
        person["id"] = person_id

        people.append(person)
        document["peopleToNotify"] = people

        await self._persist(application_id, user_id, document)
        return person

    async def update(
        self,
        user_id: str,
        application_id: int,
        person_id: int,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if payload is None or not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid notified person payload")

        record = await self.applications.get_record(user_id, application_id)
        base_document = record.document or {}
        document = {**default_document(), **base_document}
        people = list(document.get("peopleToNotify") or [])

        target_id = self._normalise_id(person_id, people)

        for index, existing in enumerate(people):
            if int(existing.get("id", 0)) == target_id:
                updated = dict(payload)
                updated["id"] = target_id
                people[index] = updated
                document["peopleToNotify"] = people
                await self._persist(application_id, user_id, document)
                return updated

        raise HTTPException(status_code=404, detail="Notified person not found")

    async def delete(self, user_id: str, application_id: int, person_id: int) -> None:
        record = await self.applications.get_record(user_id, application_id)
        base_document = record.document or {}
        document = {**default_document(), **base_document}
        people = list(document.get("peopleToNotify") or [])

        target_id = self._normalise_id(person_id, people)
        filtered = [item for item in people if int(item.get("id", 0)) != target_id]
        if len(filtered) == len(people):
            raise HTTPException(status_code=404, detail="Notified person not found")

        document["peopleToNotify"] = filtered
        await self._persist(application_id, user_id, document)

    async def _persist(self, application_id: int, user_id: str, document: dict[str, Any]) -> None:
        updated = await self.repository.update_application(
            application_id,
            user_id,
            document=document,
            updated_at=datetime.now(timezone.utc),
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Unable to persist notified people")


__all__ = ["NotifiedPeopleService"]
