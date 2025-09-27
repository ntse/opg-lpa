from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json

import pytest
from fastapi import HTTPException

from app.services.applications import ApplicationsService, default_document
from app.services.attorneys import PrimaryAttorneyService
from app.services.correspondents import CorrespondentService
from app.services.donors import DonorService
from app.services.instructions import InstructionService
from app.services.locks import LockService
from app.services.notified_people import NotifiedPeopleService
from app.services.payments import PaymentService
from app.services.pdfs import PdfService
from app.services.preferences import PreferenceService
from app.services.repeat_case_numbers import RepeatCaseNumberService
from app.services.who_are_you import WhoAreYouService
from app.services.who_is_registering import WhoIsRegisteringService
from app.services.repositories import ApplicationRecord


class FakeApplicationRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[str, int], ApplicationRecord] = {}
        self.last_generated = 0

    async def generate_id(self) -> int:
        self.last_generated += 1
        return self.last_generated

    async def create_application(
        self,
        *,
        application_id: int,
        user_id: str,
        document: dict | None,
        metadata: dict | None,
        payment: dict | None,
        repeat_case_number: str | None,
        started_at: datetime,
        updated_at: datetime,
    ) -> ApplicationRecord:
        record = ApplicationRecord(
            id=application_id,
            user_id=user_id,
            updated_at=updated_at,
            started_at=started_at,
            created_at=started_at,
            completed_at=None,
            locked_at=None,
            locked=False,
            who_are_you_answered=False,
            seed=None,
            repeat_case_number=repeat_case_number,
            document=document,
            payment=payment,
            metadata=metadata,
        )
        self.records[(user_id, application_id)] = record
        return record

    async def get_by_id(
        self, application_id: int, user_id: str | None = None
    ) -> ApplicationRecord | None:
        if user_id is None:
            for (uid, aid), record in self.records.items():
                if aid == application_id:
                    return record
            return None
        return self.records.get((user_id, application_id))

    async def list_by_user(
        self,
        user_id: str,
        *,
        search: str | None = None,
        offset: int = 0,
        limit: int = 25,
    ) -> tuple[list[ApplicationRecord], int]:
        items = [record for (uid, _), record in self.records.items() if uid == user_id]
        total = len(items)
        return items[offset : offset + limit], total

    async def update_application(
        self,
        application_id: int,
        user_id: str,
        *,
        document: dict | None = None,
        metadata: dict | None = None,
        payment: dict | None = None,
        repeat_case_number: str | None = None,
        locked: bool | None = None,
        locked_at: datetime | None = None,
        who_are_you_answered: bool | None = None,
        updated_at: datetime | None = None,
    ) -> bool:
        key = (user_id, application_id)
        record = self.records.get(key)
        if not record:
            return False

        if document is not None:
            record.document = document
        if metadata is not None:
            record.metadata = metadata
        if payment is not None:
            record.payment = payment
        if repeat_case_number is not None:
            record.repeat_case_number = repeat_case_number
        if locked is not None:
            record.locked = locked
        if locked_at is not None:
            record.locked_at = locked_at
        if who_are_you_answered is not None:
            record.who_are_you_answered = who_are_you_answered
        if updated_at is not None:
            record.updated_at = updated_at
        return True

    async def delete_application(self, application_id: int, user_id: str) -> bool:
        return self.records.pop((user_id, application_id), None) is not None


@pytest.mark.asyncio
async def test_create_application_sets_defaults() -> None:
    repository = FakeApplicationRepository()
    service = ApplicationsService(repository)

    result = await service.create("user-1", None)

    assert result["id"] == 1
    assert result["document"] == default_document()
    assert result["metadata"] == {}
    assert result["payment"] == {}


@pytest.mark.asyncio
async def test_patch_application_merges_document_keys() -> None:
    repository = FakeApplicationRepository()
    service = ApplicationsService(repository)

    created = await service.create("user-1", {"document": {"metadata": "value"}})
    assert created["document"]["metadata"] == "value"

    patched = await service.patch("user-1", created["id"], {"document": {"new": 1}})

    assert patched["document"]["metadata"] == "value"
    assert patched["document"]["new"] == 1


@pytest.mark.asyncio
async def test_primary_attorney_lifecycle() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    primary_service = PrimaryAttorneyService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    attorney = await primary_service.create(
        "user-1", lpa_id, {"name": "Test Attorney", "type": "human"}
    )

    assert attorney["id"] == 1

    updated = await primary_service.update(
        "user-1", lpa_id, attorney["id"], {"name": "Updated", "type": "human"}
    )
    assert updated["name"] == "Updated"

    await primary_service.delete("user-1", lpa_id, attorney["id"])

    with pytest.raises(HTTPException):  # type: ignore[name-defined]
        await primary_service.delete("user-1", lpa_id, attorney["id"])


@pytest.mark.asyncio
async def test_donor_update_overwrites_existing() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    donor_service = DonorService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    donor = await donor_service.update("user-1", lpa_id, {"firstname": "Alice"})
    assert donor["firstname"] == "Alice"

    donor = await donor_service.update("user-1", lpa_id, {"firstname": "Bob"})
    assert donor["firstname"] == "Bob"


@pytest.mark.asyncio
async def test_instruction_update() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    instruction_service = InstructionService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    instruction = await instruction_service.update("user-1", lpa_id, {"instruction": "Do X"})
    assert instruction == {"instruction": "Do X"}

    cleared = await instruction_service.update("user-1", lpa_id, {"instruction": None})
    assert cleared == {}

    with pytest.raises(HTTPException):
        await instruction_service.update("user-1", lpa_id, {"instruction": 123})


@pytest.mark.asyncio
async def test_preference_update() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    preference_service = PreferenceService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    preference = await preference_service.update("user-1", lpa_id, {"preference": "Some pref"})
    assert preference == {"preference": "Some pref"}

    cleared = await preference_service.update("user-1", lpa_id, None)
    assert cleared == {}

    with pytest.raises(HTTPException):
        await preference_service.update("user-1", lpa_id, {"preference": 5.6})


@pytest.mark.asyncio
async def test_lock_service() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    lock_service = LockService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    result = await lock_service.lock("user-1", lpa_id)
    assert result["locked"] is True
    assert isinstance(result["lockedAt"], str)

    with pytest.raises(HTTPException):
        await lock_service.lock("user-1", lpa_id)


@pytest.mark.asyncio
async def test_correspondent_update_and_delete() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    service = CorrespondentService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    correspondent = {"name": "Jane", "address": {"line1": "123 Street"}}
    result = await service.update("user-1", lpa_id, correspondent)
    assert result == correspondent

    # delete should succeed and be idempotent
    await service.delete("user-1", lpa_id)
    await service.delete("user-1", lpa_id)

    with pytest.raises(HTTPException):
        await service.update("user-1", lpa_id, None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_repeat_case_number_update_and_delete() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    service = RepeatCaseNumberService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    result = await service.update("user-1", lpa_id, {"repeatCaseNumber": "1234"})
    assert result == {"repeatCaseNumber": 1234}

    await service.delete("user-1", lpa_id)

    with pytest.raises(HTTPException):
        await service.update("user-1", lpa_id, {"repeatCaseNumber": "abc"})


@pytest.mark.asyncio
async def test_notified_people_flow() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    service = NotifiedPeopleService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    person = await service.create("user-1", lpa_id, {"name": "Alex"})
    assert person["id"] == 1
    assert person["name"] == "Alex"

    updated = await service.update("user-1", lpa_id, person["id"], {"name": "Alex Updated"})
    assert updated["name"] == "Alex Updated"

    await service.delete("user-1", lpa_id, person["id"])

    with pytest.raises(HTTPException):
        await service.delete("user-1", lpa_id, person["id"])


@pytest.mark.asyncio
async def test_payment_update() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    payment_service = PaymentService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    payload = {"method": "card", "amount": 8200}
    result = await payment_service.update("user-1", lpa_id, payload)
    assert result == payload


@pytest.mark.asyncio
async def test_pdf_service_status_transitions() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    pdf_service = PdfService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    response = await pdf_service.fetch("user-1", lpa_id, "lp1")
    body = json.loads(response.body)
    assert body["status"] == "in-queue"

    response = await pdf_service.fetch("user-1", lpa_id, "lp1")
    body = json.loads(response.body)
    assert body["status"] == "ready"


@pytest.mark.asyncio
async def test_who_are_you_and_who_is_registering() -> None:
    repository = FakeApplicationRepository()
    applications = ApplicationsService(repository)
    who_service = WhoAreYouService(applications, repository)
    registering_service = WhoIsRegisteringService(applications, repository)

    created = await applications.create("user-1", None)
    lpa_id = created["id"]

    result = await who_service.update("user-1", lpa_id, {"answer": "donor"})
    assert result["whoAreYouAnswered"] is True

    with pytest.raises(HTTPException):
        await who_service.update("user-1", lpa_id, {"answer": "duplicate"})

    result = await registering_service.update("user-1", lpa_id, {"whoIsRegistering": "donor"})
    assert result["whoIsRegistering"] == "donor"

    cleared = await registering_service.update("user-1", lpa_id, None)
    assert cleared == {}
