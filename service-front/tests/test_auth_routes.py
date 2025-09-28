from http import HTTPStatus

import pytest
from starlette.testclient import TestClient

from app.routes.auth import get_api_client
from app.services.api_client import ApiClientError


class FakeApiClient:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.created_with: tuple[str, str] | None = None
        self.activation_token: str | None = None
        self.authenticated_with: tuple[str, str] | None = None
        self.should_fail = should_fail

    async def create_user(self, username: str, password: str) -> dict:
        if self.should_fail:
            raise ApiClientError("username-already-exists", status_code=400)
        self.created_with = (username, password)
        return {"userId": "user-1", "activation_token": "activate-1"}

    async def activate_user(self, activation_token: str) -> None:
        self.activation_token = activation_token

    async def authenticate(self, username: str, password: str, update_token: bool = True) -> dict:
        if self.should_fail:
            raise ApiClientError("invalid-user-credentials", status_code=401)
        self.authenticated_with = (username, password)
        return {
            "userId": "user-1",
            "username": username,
            "token": "token-abc",
            "expiresAt": "2025-01-01T00:00:00Z",
        }

    async def list_applications(self, token: str, user_id: str, *, page: int = 1, search: str | None = None) -> dict:
        return {"applications": [], "total": 0}


@pytest.fixture()
def client_with_api(app_instance):
    fake_api = FakeApiClient()
    app_instance.dependency_overrides[get_api_client] = lambda: fake_api
    with TestClient(app_instance) as test_client:
        yield test_client, fake_api
    app_instance.dependency_overrides.pop(get_api_client, None)


def test_register_success(client_with_api):
    client, fake_api = client_with_api

    response = client.post(
        "/register",
        data={
            "email": "user@example.com",
            "password": "Passw0rd!",
            "confirm_password": "Passw0rd!",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert response.headers["location"] == "/dashboard"
    assert fake_api.created_with == ("user@example.com", "Passw0rd!")
    assert fake_api.activation_token == "activate-1"
    assert fake_api.authenticated_with == ("user@example.com", "Passw0rd!")

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == HTTPStatus.OK
    assert "Your lasting power of attorney applications" in dashboard.text


def test_register_validation_error(client_with_api):
    client, _ = client_with_api

    response = client.post(
        "/register",
        data={
            "email": "invalid-email",
            "password": "short",
            "confirm_password": "short",
        },
    )

    assert response.status_code == HTTPStatus.OK
    text = response.text
    assert "Password must be at least 8 characters" in text
    assert "value is not a valid email address" in text


def test_register_password_mismatch(client_with_api):
    client, _ = client_with_api

    response = client.post(
        "/register",
        data={
            "email": "user@example.com",
            "password": "Passw0rd!",
            "confirm_password": "Different1!",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "Passwords do not match" in response.text


def test_register_api_error(app_instance):
    failing_api = FakeApiClient(should_fail=True)
    app_instance.dependency_overrides[get_api_client] = lambda: failing_api
    try:
        with TestClient(app_instance) as client:
            response = client.post(
                "/register",
                data={
                    "email": "user@example.com",
                    "password": "Passw0rd!",
                    "confirm_password": "Passw0rd!",
                },
            )
        assert response.status_code == HTTPStatus.OK
        assert "username-already-exists" in response.text
    finally:
        app_instance.dependency_overrides.pop(get_api_client, None)


def test_login_success(client_with_api):
    client, fake_api = client_with_api

    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "Passw0rd!"},
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert response.headers["location"] == "/dashboard"
    assert fake_api.authenticated_with == ("user@example.com", "Passw0rd!")


def test_login_api_error(app_instance):
    failing_api = FakeApiClient(should_fail=True)
    app_instance.dependency_overrides[get_api_client] = lambda: failing_api
    try:
        with TestClient(app_instance) as client:
            response = client.post(
                "/login",
                data={"email": "user@example.com", "password": "Passw0rd!"},
            )
        assert response.status_code == HTTPStatus.OK
        assert "invalid-user-credentials" in response.text
    finally:
        app_instance.dependency_overrides.pop(get_api_client, None)
