from http import HTTPStatus
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.routes.auth import get_api_client


class FakeApplicationsApi:
    def __init__(self) -> None:
        self.auth_calls: list[tuple[str, str]] = []
        self.list_calls: list[tuple[str, int, str | None]] = []
        self.created_applications: int = 1
        self.update_type_calls: list[str | None] = []
        self.update_registering_calls: list[str | None] = []
        self.update_donor_calls: list[dict[str, Any]] = []
        self.primary_added: list[dict[str, Any]] = []
        self.primary_deleted: list[int] = []
        self.notified_added: list[dict[str, Any]] = []
        self.notified_deleted: list[int] = []
        self.update_instruction_calls: list[str | None] = []
        self.update_preference_calls: list[str | None] = []
        self.certificate_provider_updates: list[dict[str, Any]] = []
        self.certificate_provider_deletes: int = 0
        self.repeat_case_number_updates: list[str] = []
        self.repeat_case_number_deletes: int = 0
        self.payment_updates: list[dict[str, Any]] = []
        self.lock_calls: int = 0
        self.pdf_status_responses: dict[str, dict[str, Any]] = {
            "lp1": {"status": "ready"},
            "lp3": {"status": "pending"},
            "lpa120": {"status": "not-requested"},
        }
        self.applications: dict[int, dict[str, Any]] = {
            1: self._default_application(1)
        }

    def _default_application(self, app_id: int) -> dict[str, Any]:
        return {
            "id": app_id,
            "user": "user-1",
            "updatedAt": "2025-01-01T00:00:00Z",
            "locked": False,
            "repeatCaseNumber": None,
            "document": {
                "type": None,
                "donor": {},
                "primaryAttorneys": [],
                "peopleToNotify": [],
                "whoIsRegistering": None,
                "instruction": None,
                "preference": None,
                "certificateProvider": None,
            },
            "metadata": {},
            "payment": {},
        }

    async def authenticate(self, username: str, password: str, update_token: bool = True) -> dict[str, Any]:
        self.auth_calls.append((username, password))
        return {
            "userId": "user-1",
            "username": username,
            "token": "token-123",
            "expiresAt": "2026-01-01T00:00:00Z",
        }

    async def create_user(self, username: str, password: str) -> dict[str, Any]:  # pragma: no cover - unused
        raise NotImplementedError

    async def activate_user(self, activation_token: str) -> dict | None:  # pragma: no cover - unused
        return None

    async def list_applications(self, token: str, user_id: str, *, page: int = 1, search: str | None = None) -> dict:
        self.list_calls.append((token, page, search))
        return {
            "applications": list(self.applications.values()),
            "total": len(self.applications),
        }

    async def create_application(self, token: str, user_id: str, payload: dict[str, Any] | None = None) -> dict:
        self.created_applications += 1
        application = self._default_application(self.created_applications)
        self.applications[self.created_applications] = application
        return application

    async def update_who_are_you(self, token: str, user_id: str, application_id: int, answer: str) -> dict:
        # Not stored for assertions – single use best-effort
        return {"whoAreYouAnswered": True}

    async def update_who_is_registering(
        self,
        token: str,
        user_id: str,
        application_id: int,
        value: str | None,
    ) -> dict:
        self.update_registering_calls.append(value)
        self.applications[application_id]["document"]["whoIsRegistering"] = value
        return {"whoIsRegistering": value}

    async def update_type(self, token: str, user_id: str, application_id: int, app_type: str | None) -> dict:
        self.update_type_calls.append(app_type)
        self.applications[application_id]["document"]["type"] = app_type
        return {"type": app_type}

    async def get_application(self, token: str, user_id: str, application_id: int) -> dict:
        return self.applications[application_id]

    async def update_donor(self, token: str, user_id: str, application_id: int, donor: dict[str, Any]) -> dict:
        self.update_donor_calls.append(donor)
        self.applications[application_id]["document"]["donor"] = donor
        return donor

    async def update_instruction(
        self,
        token: str,
        user_id: str,
        application_id: int,
        instruction: str | None,
    ) -> dict:
        self.update_instruction_calls.append(instruction)
        self.applications[application_id]["document"]["instruction"] = instruction
        return {"instruction": instruction}

    async def update_preference(
        self,
        token: str,
        user_id: str,
        application_id: int,
        preference: str | None,
    ) -> dict:
        self.update_preference_calls.append(preference)
        self.applications[application_id]["document"]["preference"] = preference
        return {"preference": preference}

    async def add_primary_attorney(
        self,
        token: str,
        user_id: str,
        application_id: int,
        payload: dict[str, Any],
    ) -> dict:
        self.primary_added.append(payload)
        payload = {**payload, "id": len(self.primary_added)}
        self.applications[application_id]["document"]["primaryAttorneys"].append(payload)
        return payload

    async def delete_primary_attorney(
        self,
        token: str,
        user_id: str,
        application_id: int,
        attorney_id: int,
    ) -> None:
        self.primary_deleted.append(attorney_id)
        attorneys = self.applications[application_id]["document"]["primaryAttorneys"]
        self.applications[application_id]["document"]["primaryAttorneys"] = [
            item for item in attorneys if item.get("id") != attorney_id
        ]

    async def add_notified_person(
        self,
        token: str,
        user_id: str,
        application_id: int,
        payload: dict[str, Any],
    ) -> dict:
        self.notified_added.append(payload)
        payload = {**payload, "id": len(self.notified_added)}
        self.applications[application_id]["document"]["peopleToNotify"].append(payload)
        return payload

    async def delete_notified_person(
        self,
        token: str,
        user_id: str,
        application_id: int,
        person_id: int,
    ) -> None:
        self.notified_deleted.append(person_id)
        people = self.applications[application_id]["document"]["peopleToNotify"]
        self.applications[application_id]["document"]["peopleToNotify"] = [
            item for item in people if item.get("id") != person_id
        ]

    async def update_certificate_provider(
        self,
        token: str,
        user_id: str,
        application_id: int,
        provider: dict[str, Any],
    ) -> dict[str, Any]:
        self.certificate_provider_updates.append(provider)
        self.applications[application_id]["document"]["certificateProvider"] = provider
        return provider

    async def delete_certificate_provider(
        self,
        token: str,
        user_id: str,
        application_id: int,
    ) -> None:
        self.certificate_provider_deletes += 1
        self.applications[application_id]["document"]["certificateProvider"] = None

    async def update_repeat_case_number(
        self,
        token: str,
        user_id: str,
        application_id: int,
        value: str,
    ) -> dict[str, Any]:
        self.repeat_case_number_updates.append(value)
        self.applications[application_id]["repeatCaseNumber"] = value
        return {"repeatCaseNumber": value}

    async def delete_repeat_case_number(
        self,
        token: str,
        user_id: str,
        application_id: int,
    ) -> None:
        self.repeat_case_number_deletes += 1
        self.applications[application_id]["repeatCaseNumber"] = None

    async def update_payment(
        self,
        token: str,
        user_id: str,
        application_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.payment_updates.append(payload)
        self.applications[application_id]["payment"] = payload
        return payload

    async def get_pdf_status(
        self,
        token: str,
        user_id: str,
        application_id: int,
        pdf_type: str,
    ) -> dict[str, Any]:
        return self.pdf_status_responses.get(pdf_type, {"status": "unknown"})

    async def lock_application(
        self,
        token: str,
        user_id: str,
        application_id: int,
    ) -> dict[str, Any]:
        self.lock_calls += 1
        self.applications[application_id]["locked"] = True
        return {"locked": True}


@pytest.fixture()
def authed_client(app_instance):
    fake_api = FakeApplicationsApi()
    app_instance.dependency_overrides[get_api_client] = lambda: fake_api
    with TestClient(app_instance) as client:
        login_response = client.post(
            "/login",
            data={"email": "user@example.com", "password": "Passw0rd!"},
            follow_redirects=False,
        )
        assert login_response.status_code == HTTPStatus.SEE_OTHER
        assert login_response.headers["location"] == "/dashboard"
        yield client, fake_api
    app_instance.dependency_overrides.pop(get_api_client, None)


def test_dashboard_lists_applications(authed_client):
    client, fake_api = authed_client

    response = client.get("/dashboard")

    assert response.status_code == HTTPStatus.OK
    assert "LPA-1" in response.text
    assert fake_api.list_calls


def test_dashboard_requires_login(app_instance):
    with TestClient(app_instance) as client:
        response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == HTTPStatus.SEE_OTHER
    assert response.headers["location"] == "/login"


def test_create_application_flow(authed_client):
    client, fake_api = authed_client

    response = client.post(
        "/applications/new",
        data={
            "who_are_you": "donor",
            "who_is_registering": "donor",
            "application_type": "property-and-financial",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert "/applications/" in response.headers["location"]
    assert fake_api.created_applications > 1
    assert fake_api.update_type_calls[-1] == "property-and-financial"


def test_application_detail_page(authed_client):
    client, _ = authed_client

    response = client.get("/applications/1")

    assert response.status_code == HTTPStatus.OK
    assert "Application 1" in response.text


def test_update_type(authed_client):
    client, fake_api = authed_client

    response = client.post(
        "/applications/1/type",
        data={"lpa_type": "health-and-welfare"},
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.update_type_calls[-1] == "health-and-welfare"


def test_update_donor_details(authed_client):
    client, fake_api = authed_client

    response = client.post(
        "/applications/1/donor",
        data={
            "firstname": "Alice",
            "lastname": "Smith",
            "email": "alice@example.com",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.update_donor_calls[-1]["firstname"] == "Alice"


def test_add_primary_attorney(authed_client):
    client, fake_api = authed_client

    response = client.post(
        "/applications/1/primary-attorneys",
        data={"attorney_name": "John Doe", "attorney_email": "john@example.com", "attorney_type": "human"},
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.primary_added[-1]["name"] == "John Doe"


def test_add_notified_person(authed_client):
    client, fake_api = authed_client

    response = client.post(
        "/applications/1/notified-people",
        data={"notify_name": "Alex", "notify_email": "alex@example.com"},
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.notified_added[-1]["name"] == "Alex"


def test_save_instruction_and_preference(authed_client):
    client, fake_api = authed_client

    response_instruction = client.post(
        "/applications/1/instruction",
        data={"instruction": "Only invest in green funds."},
        follow_redirects=False,
    )
    response_preference = client.post(
        "/applications/1/preference",
        data={"preference": "Keep donations to local charities."},
        follow_redirects=False,
    )

    assert response_instruction.status_code == HTTPStatus.SEE_OTHER
    assert response_preference.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.update_instruction_calls[-1] == "Only invest in green funds."
    assert fake_api.update_preference_calls[-1] == "Keep donations to local charities."


def test_repeat_case_number_update_and_clear(authed_client):
    client, fake_api = authed_client

    response = client.post(
        "/applications/1/repeat-case-number",
        data={"repeat_case_number": "1234"},
        follow_redirects=False,
    )
    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.repeat_case_number_updates[-1] == "1234"
    assert fake_api.applications[1]["repeatCaseNumber"] == "1234"

    response = client.post(
        "/applications/1/repeat-case-number",
        data={"repeat_case_number": ""},
        follow_redirects=False,
    )
    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.repeat_case_number_deletes > 0
    assert fake_api.applications[1]["repeatCaseNumber"] is None


def test_certificate_provider_update_and_remove(authed_client):
    client, fake_api = authed_client

    response = client.post(
        "/applications/1/certificate-provider",
        data={
            "cp_name": "Test Provider",
            "cp_email": "provider@example.com",
            "cp_phone": "01234",
        },
        follow_redirects=False,
    )
    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.certificate_provider_updates[-1]["name"] == "Test Provider"

    response = client.post(
        "/applications/1/certificate-provider",
        data={"cp_name": "", "cp_email": ""},
        follow_redirects=False,
    )
    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.certificate_provider_deletes > 0
    assert fake_api.applications[1]["document"]["certificateProvider"] is None


def test_payment_update(authed_client):
    client, fake_api = authed_client

    response = client.post(
        "/applications/1/payment",
        data={"payment_method": "card", "payment_amount": "82.50", "payment_reference": "ABC"},
        follow_redirects=False,
    )
    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.payment_updates[-1]["amount"] == 8250
    assert fake_api.payment_updates[-1]["method"] == "card"


def test_lock_application(authed_client):
    client, fake_api = authed_client

    response = client.post("/applications/1/lock", follow_redirects=False)

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert fake_api.lock_calls == 1
    assert fake_api.applications[1]["locked"] is True


def test_pdf_statuses_displayed(authed_client):
    client, fake_api = authed_client
    fake_api.pdf_status_responses = {
        "lp1": {"status": "ready"},
        "lp3": {"status": "queued"},
        "lpa120": {"status": "not-requested"},
    }

    response = client.get("/applications/1")

    assert "LP1" in response.text
    assert "ready" in response.text
