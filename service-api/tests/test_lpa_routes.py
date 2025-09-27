from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.api.deps import (
    get_auth_service,
    get_notified_people_service,
    get_payment_service,
    get_pdf_service,
    get_repeat_case_number_service,
    get_who_are_you_service,
    get_who_is_registering_service,
    get_certificate_provider_service,
    get_type_service,
)
from app.main import app


class FakeAuthService:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.calls: list[tuple[str, bool]] = []

    async def with_token(self, token: str, extend_token: bool) -> dict[str, Any]:
        self.calls.append((token, extend_token))
        return {"userId": self.user_id}


class FakeNotifiedService:
    def __init__(self) -> None:
        self.created: list[tuple[str, int, dict[str, Any]]] = []
        self.updated: list[tuple[str, int, int, dict[str, Any]]] = []
        self.deleted: list[tuple[str, int, int]] = []

    async def create(self, user_id: str, application_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self.created.append((user_id, application_id, payload))
        return {"id": 1, **payload}

    async def update(
        self, user_id: str, application_id: int, person_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self.updated.append((user_id, application_id, person_id, payload))
        return {"id": person_id, **payload}

    async def delete(self, user_id: str, application_id: int, person_id: int) -> None:
        self.deleted.append((user_id, application_id, person_id))


class FakeRepeatCaseNumberService:
    def __init__(self) -> None:
        self.updated: list[tuple[str, int, dict[str, Any]]] = []
        self.deleted: list[tuple[str, int]] = []

    async def update(self, user_id: str, application_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self.updated.append((user_id, application_id, payload))
        return {"repeatCaseNumber": 1234}

    async def delete(self, user_id: str, application_id: int) -> None:
        self.deleted.append((user_id, application_id))


class FakePaymentService:
    def __init__(self) -> None:
        self.updated: list[tuple[str, int, dict[str, Any]]] = []

    async def update(self, user_id: str, application_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self.updated.append((user_id, application_id, payload))
        return payload


class FakePdfService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str]] = []

    async def fetch(self, user_id: str, application_id: int, pdf_type: str):
        self.calls.append((user_id, application_id, pdf_type))
        return JSONResponse({"status": "ready"})


class FakeWhoAreYouService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, dict[str, Any]]] = []

    async def update(self, user_id: str, application_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((user_id, application_id, payload))
        return {"whoAreYouAnswered": True}


class FakeWhoIsRegisteringService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, dict[str, Any] | None]] = []

    async def update(
        self, user_id: str, application_id: int, payload: dict[str, Any] | None
    ) -> dict[str, Any]:
        self.calls.append((user_id, application_id, payload))
        return {"whoIsRegistering": payload.get("whoIsRegistering") if payload else None}


class FakeCertificateProviderService:
    def __init__(self) -> None:
        self.updated: list[tuple[str, int, dict[str, Any]]] = []
        self.deleted: list[tuple[str, int]] = []

    async def update(self, user_id: str, application_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self.updated.append((user_id, application_id, payload))
        return payload

    async def delete(self, user_id: str, application_id: int) -> None:
        self.deleted.append((user_id, application_id))


class FakeTypeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, dict[str, Any] | None]] = []

    async def update(self, user_id: str, application_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        self.calls.append((user_id, application_id, payload))
        return {"type": payload.get("type") if payload else None}


@pytest.fixture
def test_client() -> tuple[
    TestClient,
    FakeAuthService,
    FakeNotifiedService,
    FakeRepeatCaseNumberService,
    FakePaymentService,
    FakePdfService,
    FakeWhoAreYouService,
    FakeWhoIsRegisteringService,
    FakeCertificateProviderService,
    FakeTypeService,
]:
    fake_auth = FakeAuthService("user-1")
    fake_notified = FakeNotifiedService()
    fake_repeat = FakeRepeatCaseNumberService()
    fake_payment = FakePaymentService()
    fake_pdf = FakePdfService()
    fake_who = FakeWhoAreYouService()
    fake_registering = FakeWhoIsRegisteringService()
    fake_certificate = FakeCertificateProviderService()
    fake_type = FakeTypeService()

    app.dependency_overrides[get_auth_service] = lambda: fake_auth
    app.dependency_overrides[get_notified_people_service] = lambda: fake_notified
    app.dependency_overrides[get_repeat_case_number_service] = lambda: fake_repeat
    app.dependency_overrides[get_payment_service] = lambda: fake_payment
    app.dependency_overrides[get_pdf_service] = lambda: fake_pdf
    app.dependency_overrides[get_who_are_you_service] = lambda: fake_who
    app.dependency_overrides[get_who_is_registering_service] = lambda: fake_registering
    app.dependency_overrides[get_certificate_provider_service] = lambda: fake_certificate
    app.dependency_overrides[get_type_service] = lambda: fake_type

    client = TestClient(app)
    try:
        yield (
            client,
            fake_auth,
            fake_notified,
            fake_repeat,
            fake_payment,
            fake_pdf,
            fake_who,
            fake_registering,
            fake_certificate,
            fake_type,
        )
    finally:
        app.dependency_overrides.clear()
        client.close()


def test_notified_people_routes(
    test_client: tuple[TestClient, FakeAuthService, FakeNotifiedService, FakeRepeatCaseNumberService, FakePaymentService, FakePdfService, FakeWhoAreYouService, FakeWhoIsRegisteringService, FakeCertificateProviderService, FakeTypeService]
) -> None:
    client, fake_auth, fake_notified, *_ = test_client

    response = client.post(
        "/v2/user/user-1/applications/1/notified-people",
        json={"name": "Alex"},
        headers={"Token": "abc"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Alex"

    response = client.put(
        "/v2/user/user-1/applications/1/notified-people/1",
        json={"name": "Updated"},
        headers={"Token": "abc"},
    )
    assert response.status_code == 200

    response = client.delete(
        "/v2/user/user-1/applications/1/notified-people/1",
        headers={"Token": "abc"},
    )
    assert response.status_code == 204

    assert len(fake_auth.calls) == 3


def test_repeat_case_number_routes(
    test_client: tuple[TestClient, FakeAuthService, FakeNotifiedService, FakeRepeatCaseNumberService, FakePaymentService, FakePdfService, FakeWhoAreYouService, FakeWhoIsRegisteringService, FakeCertificateProviderService, FakeTypeService]
) -> None:
    client, fake_auth, _, fake_repeat, *_ = test_client

    response = client.put(
        "/v2/user/user-1/applications/2/repeat-case-number",
        json={"repeatCaseNumber": "1234"},
        headers={"Token": "abc"},
    )
    assert response.status_code == 200

    response = client.delete(
        "/v2/user/user-1/applications/2/repeat-case-number",
        headers={"Token": "abc"},
    )
    assert response.status_code == 204

    assert len(fake_auth.calls) == 2


def test_payment_and_pdf_routes(
    test_client: tuple[TestClient, FakeAuthService, FakeNotifiedService, FakeRepeatCaseNumberService, FakePaymentService, FakePdfService, FakeWhoAreYouService, FakeWhoIsRegisteringService, FakeCertificateProviderService, FakeTypeService]
) -> None:
    client, fake_auth, _, _, fake_payment, fake_pdf, *_ = test_client

    response = client.put(
        "/v2/user/user-1/applications/3/payment",
        json={"method": "card"},
        headers={"Token": "abc"},
    )
    assert response.status_code == 200
    assert fake_payment.updated

    response = client.get(
        "/v2/user/user-1/applications/3/pdfs/lp1",
        headers={"Token": "abc"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert fake_pdf.calls

    assert len(fake_auth.calls) == 2


def test_who_routes(
    test_client: tuple[TestClient, FakeAuthService, FakeNotifiedService, FakeRepeatCaseNumberService, FakePaymentService, FakePdfService, FakeWhoAreYouService, FakeWhoIsRegisteringService, FakeCertificateProviderService, FakeTypeService]
) -> None:
    client, fake_auth, _, _, _, _, fake_who, fake_registering, *_ = test_client


def test_certificate_provider_and_type_routes(
    test_client: tuple[TestClient, FakeAuthService, FakeNotifiedService, FakeRepeatCaseNumberService, FakePaymentService, FakePdfService, FakeWhoAreYouService, FakeWhoIsRegisteringService, FakeCertificateProviderService, FakeTypeService]
) -> None:
    client, fake_auth, *_ , fake_certificate, fake_type = test_client

    response = client.put(
        "/v2/user/user-1/applications/5/certificate-provider",
        json={"name": "CP"},
        headers={"Token": "abc"},
    )
    assert response.status_code == 200
    assert fake_certificate.updated

    response = client.delete(
        "/v2/user/user-1/applications/5/certificate-provider",
        headers={"Token": "abc"},
    )
    assert response.status_code == 204
    assert fake_certificate.deleted

    response = client.put(
        "/v2/user/user-1/applications/5/type",
        json={"type": "hw"},
        headers={"Token": "abc"},
    )
    assert response.status_code == 200
    assert fake_type.calls
