from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.services.repositories import ApplicationRecord, ApplicationRepository
from app.utils import format_lpa_datetime

_ALLOWED_PATCH_FIELDS = {"document", "metadata", "payment", "repeatCaseNumber"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def default_document() -> dict[str, Any]:
    return {
        "donor": None,
        "primaryAttorneys": [],
        "replacementAttorneys": [],
        "instruction": None,
        "preference": None,
        "correspondent": None,
        "payment": {},
        "peopleToNotify": [],
        "certificateProvider": None,
        "type": None,
        "whoIsRegistering": None,
        "whoAreYouAnswered": False,
    }


class ApplicationsService:
    def __init__(self, repository: ApplicationRepository) -> None:
        self.repository = repository

    async def create(self, user_id: str, payload: dict | None) -> dict[str, Any]:
        data = payload or {}
        document = data.get("document") or default_document()
        metadata = data.get("metadata") or {}
        payment = data.get("payment") or {}
        repeat_case_number = data.get("repeatCaseNumber")

        application_id = await self.repository.generate_id()
        started_at = _now()

        record = await self.repository.create_application(
            application_id=application_id,
            user_id=user_id,
            document=document,
            metadata=metadata,
            payment=payment,
            repeat_case_number=repeat_case_number,
            started_at=started_at,
            updated_at=started_at,
        )

        if record is None:  # pragma: no cover - defensive safety
            raise HTTPException(status_code=500, detail="Unable to create application")

        return self._serialise(record)

    async def fetch(self, user_id: str, application_id: int) -> dict[str, Any]:
        record = await self.repository.get_by_id(application_id, user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Application not found")
        return self._serialise(record)

    async def fetch_all(
        self,
        user_id: str,
        *,
        page: int = 1,
        per_page: int = 25,
        search: str | None = None,
    ) -> dict[str, Any]:
        if page < 1:
            page = 1
        if per_page <= 0:
            per_page = 25
        offset = (page - 1) * per_page

        records, total = await self.repository.list_by_user(
            user_id,
            search=search,
            offset=offset,
            limit=per_page,
        )

        return {
            "applications": [self._serialise(record) for record in records],
            "total": total,
        }

    async def patch(self, user_id: str, application_id: int, payload: dict | None) -> dict[str, Any]:
        record = await self.repository.get_by_id(application_id, user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Application not found")

        updates = self._filter_payload(payload)

        if "document" in updates and record.document:
            merged = record.document.copy()
            merged.update(updates["document"] or {})
            updates["document"] = merged
        elif "document" in updates and not updates["document"]:
            updates["document"] = record.document or {}

        updates["updated_at"] = _now()

        await self.repository.update_application(application_id, user_id, **updates)
        refreshed = await self.repository.get_by_id(application_id, user_id)
        if refreshed is None:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail="Unable to load application")
        return self._serialise(refreshed)

    async def delete(self, user_id: str, application_id: int) -> None:
        deleted = await self.repository.delete_application(application_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Application not found")

    async def get_record(self, user_id: str, application_id: int) -> ApplicationRecord:
        record = await self.repository.get_by_id(application_id, user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Application not found")
        if record.document is None:
            record.document = default_document()
        return record

    @staticmethod
    def _filter_payload(payload: dict | None) -> dict[str, Any]:
        if not payload:
            return {}
        filtered: dict[str, Any] = {}
        for key, value in payload.items():
            if key in _ALLOWED_PATCH_FIELDS:
                filtered[key if key != "repeatCaseNumber" else "repeat_case_number"] = value
        return filtered

    @staticmethod
    def _serialise(record: ApplicationRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "user": record.user_id,
            "updatedAt": format_lpa_datetime(record.updated_at),
            "startedAt": format_lpa_datetime(record.started_at),
            "createdAt": format_lpa_datetime(record.created_at),
            "completedAt": format_lpa_datetime(record.completed_at),
            "lockedAt": format_lpa_datetime(record.locked_at),
            "locked": record.locked,
            "whoAreYouAnswered": record.who_are_you_answered,
            "seed": record.seed,
            "repeatCaseNumber": record.repeat_case_number,
            "document": record.document or default_document(),
            "payment": record.payment or {},
            "metadata": record.metadata or {},
        }


__all__ = ["ApplicationsService", "default_document"]
