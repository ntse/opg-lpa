from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt

from app.services.authentication import AuthenticationService
from app.services.repositories import AuthTokenData, UserRepository
from app.utils import format_lpa_datetime, generate_token, is_password_valid


class PasswordService:
    TOKEN_TTL_SECONDS = 86400

    def __init__(self, users: UserRepository, auth: AuthenticationService) -> None:
        self.users = users
        self.auth = auth

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> dict | str:
        user = await self.users.get_by_id(user_id)
        if user is None:
            return "user-not-found"

        if not is_password_valid(new_password):
            return "invalid-new-password"

        if not user.password_hash or not bcrypt.checkpw(old_password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return "invalid-user-credentials"

        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        await self.users.set_new_password(user.id, password_hash)

        return await self.auth.with_password(user.username or "", new_password, True)

    async def generate_token(self, username: str) -> dict | str:
        user = await self.users.get_by_username(username)
        if user is None:
            return "user-not-found"

        if not user.is_active():
            return {
                "activation_token": user.activation_token,
            }

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.TOKEN_TTL_SECONDS)
        token_value = generate_token(16)

        token = AuthTokenData(
            token=token_value,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
        )

        await self.users.add_password_reset_token(user.id, token)

        return {
            "token": token_value,
            "expiresIn": self.TOKEN_TTL_SECONDS,
            "expiresAt": format_lpa_datetime(expires_at),
        }

    async def update_password_using_token(self, token: str, new_password: str) -> str | None:
        if not is_password_valid(new_password):
            return "invalid-password"

        user = await self.users.get_by_reset_token(token)
        if user is None:
            return "invalid-token"

        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        updated, error = await self.users.update_password_using_token(token, password_hash)
        if not updated:
            return error or "nothing-modified"

        await self.users.reset_failed_login_counter(user.id)
        return None


__all__ = ["PasswordService"]
