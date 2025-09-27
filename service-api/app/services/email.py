from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.services.repositories import AuthTokenData, UserRepository
from app.utils import format_lpa_datetime, generate_token


@dataclass(slots=True)
class EmailUpdateResult:
    error: str | None = None
    user_id: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


class EmailService:
    TOKEN_TTL_SECONDS = 86400

    def __init__(self, users: UserRepository) -> None:
        self.users = users
        self._email_adapter: TypeAdapter[EmailStr] = TypeAdapter(EmailStr)

    async def generate_token(self, user_id: str, new_email: str) -> dict | str:
        if not self._is_email_valid(new_email):
            return "invalid-email"

        user = await self.users.get_by_id(user_id)
        if user is None:
            return "user-not-found"

        requested_email_owner = await self.users.get_by_username(new_email)
        if requested_email_owner is not None:
            if requested_email_owner.id == user.id:
                return "username-same-as-current"
            return "username-already-exists"

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.TOKEN_TTL_SECONDS)
        token_value = generate_token(16)

        token = AuthTokenData(
            token=token_value,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
        )

        await self.users.add_email_update_token_and_new_email(user.id, token, new_email)

        return {
            "token": token_value,
            "expiresIn": self.TOKEN_TTL_SECONDS,
            "expiresAt": format_lpa_datetime(expires_at),
        }

    async def update_email_using_token(self, token: str) -> EmailUpdateResult:
        success, error, user = await self.users.update_email_using_token(token)
        if not success:
            return EmailUpdateResult(error=error or "invalid-token")

        return EmailUpdateResult(user_id=user.id if user else None)

    def _is_email_valid(self, email: str) -> bool:
        try:
            self._email_adapter.validate_python(email)
        except ValidationError:
            return False
        return True


__all__ = ["EmailService", "EmailUpdateResult"]
