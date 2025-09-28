"""HTTP client wrapper for communicating with the service API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class ApiClientError(Exception):
    """Base exception for service API errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiConnectionError(ApiClientError):
    """Raised when the service API cannot be reached."""


@dataclass(slots=True)
class ApiClient:
    """Thin wrapper around httpx for the service API."""

    base_url: str
    timeout: float = 10.0

    async def create_user(self, username: str, password: str) -> dict:
        payload = {"username": username, "password": password}
        return await self._post_json("/v2/users/", payload)

    async def activate_user(self, activation_token: str) -> dict | None:
        payload = {"activationToken": activation_token}
        response = await self._post("/v2/users/", payload)
        if response.status_code == 204:
            return None
        # Fall back to JSON payload if provided (should not generally occur)
        return await self._json_or_empty(response)

    async def authenticate(self, username: str, password: str, update_token: bool = True) -> dict:
        payload = {
            "username": username,
            "password": password,
            "Update": update_token,
        }
        return await self._post_json("/v2/authenticate", payload)

    async def list_applications(
        self,
        token: str,
        user_id: str,
        *,
        page: int = 1,
        search: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {"page": page}
        if search:
            params["search"] = search
        return await self._get_json(f"/v2/user/{user_id}/applications", token=token, params=params)

    async def create_application(
        self,
        token: str,
        user_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict:
        return await self._post_json(
            f"/v2/user/{user_id}/applications",
            payload or {},
            token=token,
        )

    async def get_application(self, token: str, user_id: str, application_id: int) -> dict:
        return await self._get_json(
            f"/v2/user/{user_id}/applications/{application_id}",
            token=token,
        )

    async def update_type(
        self,
        token: str,
        user_id: str,
        application_id: int,
        app_type: str | None,
    ) -> dict:
        payload: dict[str, Any] | None = {"type": app_type} if app_type else {"type": None}
        return await self._put_json(
            f"/v2/user/{user_id}/applications/{application_id}/type",
            payload,
            token=token,
        )

    async def update_who_is_registering(
        self,
        token: str,
        user_id: str,
        application_id: int,
        value: str | None,
    ) -> dict:
        payload = {"whoIsRegistering": value} if value else None
        return await self._post_json(
            f"/v2/user/{user_id}/applications/{application_id}/who-is-registering",
            payload,
            token=token,
        )

    async def update_who_are_you(
        self,
        token: str,
        user_id: str,
        application_id: int,
        answer: str,
    ) -> dict:
        return await self._post_json(
            f"/v2/user/{user_id}/applications/{application_id}/who-are-you",
            {"answer": answer},
            token=token,
        )

    async def update_donor(
        self,
        token: str,
        user_id: str,
        application_id: int,
        donor: dict[str, Any],
    ) -> dict:
        return await self._put_json(
            f"/v2/user/{user_id}/applications/{application_id}/donor",
            donor,
            token=token,
        )

    async def update_instruction(
        self,
        token: str,
        user_id: str,
        application_id: int,
        instruction: str | None,
    ) -> dict:
        payload = {"instruction": instruction} if instruction else {"instruction": None}
        return await self._put_json(
            f"/v2/user/{user_id}/applications/{application_id}/instruction",
            payload,
            token=token,
        )

    async def update_preference(
        self,
        token: str,
        user_id: str,
        application_id: int,
        preference: str | None,
    ) -> dict:
        payload = {"preference": preference} if preference else None
        return await self._put_json(
            f"/v2/user/{user_id}/applications/{application_id}/preference",
            payload,
            token=token,
        )

    async def update_certificate_provider(
        self,
        token: str,
        user_id: str,
        application_id: int,
        provider: dict[str, Any],
    ) -> dict:
        return await self._put_json(
            f"/v2/user/{user_id}/applications/{application_id}/certificate-provider",
            provider,
            token=token,
        )

    async def delete_certificate_provider(
        self,
        token: str,
        user_id: str,
        application_id: int,
    ) -> None:
        await self._delete(
            f"/v2/user/{user_id}/applications/{application_id}/certificate-provider",
            token=token,
        )

    async def update_repeat_case_number(
        self,
        token: str,
        user_id: str,
        application_id: int,
        value: str,
    ) -> dict:
        return await self._put_json(
            f"/v2/user/{user_id}/applications/{application_id}/repeat-case-number",
            {"repeatCaseNumber": value},
            token=token,
        )

    async def delete_repeat_case_number(
        self,
        token: str,
        user_id: str,
        application_id: int,
    ) -> None:
        await self._delete(
            f"/v2/user/{user_id}/applications/{application_id}/repeat-case-number",
            token=token,
        )

    async def update_payment(
        self,
        token: str,
        user_id: str,
        application_id: int,
        payment: dict[str, Any],
    ) -> dict:
        return await self._put_json(
            f"/v2/user/{user_id}/applications/{application_id}/payment",
            payment,
            token=token,
        )

    async def get_pdf_status(
        self,
        token: str,
        user_id: str,
        application_id: int,
        pdf_type: str,
    ) -> dict:
        return await self._get_json(
            f"/v2/user/{user_id}/applications/{application_id}/pdfs/{pdf_type}",
            token=token,
        )

    async def lock_application(
        self,
        token: str,
        user_id: str,
        application_id: int,
    ) -> dict:
        return await self._post_json(
            f"/v2/user/{user_id}/applications/{application_id}/lock",
            {},
            token=token,
        )

    async def add_primary_attorney(
        self,
        token: str,
        user_id: str,
        application_id: int,
        payload: dict[str, Any],
    ) -> dict:
        return await self._post_json(
            f"/v2/user/{user_id}/applications/{application_id}/primary-attorneys",
            payload,
            token=token,
        )

    async def delete_primary_attorney(
        self,
        token: str,
        user_id: str,
        application_id: int,
        attorney_id: int,
    ) -> None:
        await self._delete(
            f"/v2/user/{user_id}/applications/{application_id}/primary-attorneys/{attorney_id}",
            token=token,
        )

    async def add_notified_person(
        self,
        token: str,
        user_id: str,
        application_id: int,
        payload: dict[str, Any],
    ) -> dict:
        return await self._post_json(
            f"/v2/user/{user_id}/applications/{application_id}/notified-people",
            payload,
            token=token,
        )

    async def delete_notified_person(
        self,
        token: str,
        user_id: str,
        application_id: int,
        person_id: int,
    ) -> None:
        await self._delete(
            f"/v2/user/{user_id}/applications/{application_id}/notified-people/{person_id}",
            token=token,
        )

    async def _get_json(
        self,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict:
        response = await self._request("GET", path, token=token, params=params)
        return await self._read_json(response)

    async def _post_json(
        self,
        path: str,
        payload: dict[str, Any] | None,
        *,
        token: str | None = None,
    ) -> dict:
        response = await self._request("POST", path, token=token, json=payload)
        return await self._read_json(response)

    async def _put_json(
        self,
        path: str,
        payload: dict[str, Any] | None,
        *,
        token: str | None = None,
    ) -> dict:
        response = await self._request("PUT", path, token=token, json=payload)
        return await self._read_json(response)

    async def _delete(self, path: str, *, token: str | None = None) -> None:
        await self._request("DELETE", path, token=token)

    async def _post(self, path: str, payload: dict[str, Any] | None, *, token: str | None = None) -> httpx.Response:
        return await self._request("POST", path, token=token, json=payload)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers: dict[str, str] = {}
        if token:
            headers["Token"] = token
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                response = await client.request(method, path, json=json, params=params, headers=headers)
        except httpx.RequestError as exc:  # pragma: no cover - network errors mocked in tests
            raise ApiConnectionError("Unable to reach service API") from exc
        if response.status_code >= 400:
            detail = await self._json_error(response)
            raise ApiClientError(detail, status_code=response.status_code)
        return response

    async def _read_json(self, response: httpx.Response) -> dict:
        try:
            return response.json()
        except ValueError as exc:
            raise ApiClientError("Invalid JSON response from service API") from exc

    async def _json_error(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("detail"):
                detail = payload["detail"]
                if isinstance(detail, str):
                    return detail
                if isinstance(detail, list):
                    return ", ".join(str(item) for item in detail)
        except ValueError:
            pass
        return f"Service API returned {response.status_code}"

    async def _json_or_empty(self, response: httpx.Response) -> dict | None:
        try:
            return response.json()
        except ValueError:
            return None


__all__ = ["ApiClient", "ApiClientError", "ApiConnectionError"]
