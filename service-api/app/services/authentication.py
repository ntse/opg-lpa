from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt

from app.config import get_settings
from app.services.repositories import AuthTokenData, UserRecord, UserRepository
from app.utils.datetime import format_lpa_datetime
from app.utils.token import generate_token


class AuthenticationService:
    MAX_ALLOWED_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCK_TIME = timedelta(minutes=15)
    TOKEN_UPDATE_THROTTLE_SECONDS = 5

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository
        self.settings = get_settings()

    async def with_password(
        self, username: str | None, password: str | None, create_token: bool
    ) -> dict | str:
        if not username or not password:
            return "missing-credentials"

        user = await self.repository.get_by_username(username)

        if user is None:
            return "user-not-found"

        if not user.is_active():
            return "account-not-active"

        if user.failed_login_attempts >= self.MAX_ALLOWED_LOGIN_ATTEMPTS:
            if self._is_account_lock_active(user):
                return "account-locked/max-login-attempts"

            await self.repository.reset_failed_login_counter(user.id)
            user.failed_login_attempts = 0

        if not self._verify_password(password, user.password_hash):
            await self.repository.increment_failed_login_counter(user.id)

            if user.failed_login_attempts + 1 >= self.MAX_ALLOWED_LOGIN_ATTEMPTS:
                return "invalid-user-credentials/account-locked"

            return "invalid-user-credentials"

        inactivity_flags_cleared = user.inactivity_flags is not None

        await self.repository.update_last_login_time(user.id)

        if user.failed_login_attempts > 0:
            await self.repository.reset_failed_login_counter(user.id)

        response: dict[str, object] = {
            "userId": user.id,
            "username": user.username,
            "last_login": format_lpa_datetime(user.last_login_at),
            "inactivityFlagsCleared": inactivity_flags_cleared,
        }

        if create_token:
            token_details = await self._create_new_token(user)
            response.update(token_details)

        return response

    async def with_token(self, token_str: str, extend_token: bool) -> dict | str:
        return await self.update_token(token_str, needs_update=extend_token, throttle=True)

    async def update_token(
        self,
        token_str: str,
        needs_update: bool = True,
        throttle: bool = True,
        expires_at: datetime | None = None,
    ) -> dict | str:
        user = await self.repository.get_by_auth_token(token_str)

        if user is None:
            return "invalid-token"

        token_data = user.auth_token

        if token_data is None:
            return "invalid-token"

        now = datetime.now(timezone.utc)

        if token_data.expires_at < now:
            return "token-has-expired"

        max_expires_at = now + timedelta(seconds=self.settings.session.token_ttl_seconds)
        should_update = needs_update

        if throttle and should_update and token_data.updated_at is not None:
            seconds_since_update = (now - token_data.updated_at).total_seconds()
            if seconds_since_update < self.TOKEN_UPDATE_THROTTLE_SECONDS:
                should_update = False

        if expires_at is None:
            if should_update:
                next_expires_at = max_expires_at
            else:
                next_expires_at = token_data.expires_at
        else:
            next_expires_at = min(expires_at, max_expires_at)

        expires_in = max(0, int((next_expires_at - now).total_seconds()))

        if should_update:
            updated_token = AuthTokenData(
                token=token_data.token,
                created_at=token_data.created_at,
                updated_at=now,
                expires_at=next_expires_at,
            )
            await self.repository.update_auth_token_expiry(user.id, updated_token)
            token_data = updated_token
        else:
            token_data = AuthTokenData(
                token=token_data.token,
                created_at=token_data.created_at,
                updated_at=token_data.updated_at,
                expires_at=next_expires_at,
            )

        return {
            "token": token_data.token,
            "userId": user.id,
            "username": user.username,
            "last_login": format_lpa_datetime(user.last_login_at),
            "expiresIn": expires_in,
            "expiresAt": format_lpa_datetime(token_data.expires_at),
        }

    async def _create_new_token(self, user: UserRecord) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.settings.session.token_ttl_seconds)
        token_value = generate_token(32)

        token_data = AuthTokenData(
            token=token_value,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
        )

        await self.repository.set_auth_token(user.id, token_data)

        return {
            "token": token_value,
            "expiresIn": self.settings.session.token_ttl_seconds,
            "expiresAt": format_lpa_datetime(expires_at),
        }

    def _verify_password(self, password: str, hashed: str | None) -> bool:
        if not hashed:
            return False

        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False

    def _is_account_lock_active(self, user: UserRecord) -> bool:
        if user.last_failed_login_at is None:
            return False

        threshold = datetime.now(timezone.utc) - self.ACCOUNT_LOCK_TIME
        return user.last_failed_login_at > threshold


__all__ = ["AuthenticationService"]
