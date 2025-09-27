from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest

from app.services.authentication import AuthenticationService
from app.services.repositories import AuthTokenData, UserRecord


@dataclass
class FakeRepository:
    user: UserRecord | None
    last_login_updated: bool = False
    resets: int = 0
    increments: int = 0
    stored_token: AuthTokenData | None = None
    updated_token: AuthTokenData | None = None

    async def get_by_username(self, username: str) -> UserRecord | None:
        if self.user and self.user.username == username:
            return self.user
        return None

    async def get_by_auth_token(self, token: str) -> UserRecord | None:
        if self.user and self.user.auth_token and self.user.auth_token.token == token:
            return self.user
        return None

    async def get_by_id(self, user_id: str) -> UserRecord | None:
        if self.user and self.user.id == user_id:
            return self.user
        return None

    async def update_last_login_time(self, user_id: str) -> bool:
        self.last_login_updated = True
        return True

    async def reset_failed_login_counter(self, user_id: str) -> bool:
        self.resets += 1
        if self.user:
            self.user.failed_login_attempts = 0
        return True

    async def increment_failed_login_counter(self, user_id: str) -> bool:
        self.increments += 1
        if self.user:
            self.user.failed_login_attempts += 1
        return True

    async def set_auth_token(self, user_id: str, token: AuthTokenData) -> bool:
        self.stored_token = token
        if self.user:
            self.user.auth_token = token
        return True

    async def update_auth_token_expiry(self, user_id: str, token: AuthTokenData) -> bool:
        self.updated_token = token
        if self.user:
            self.user.auth_token = token
        return True


@pytest.mark.asyncio
async def test_with_password_generates_token_for_valid_credentials() -> None:
    password = "Passw0rd!"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = UserRecord(
        id="user-123",
        username="user@example.com",
        password_hash=hashed,
        active_raw=True,
        failed_login_attempts=0,
        last_login_at=None,
        last_failed_login_at=None,
        inactivity_flags={"flag": True},
        auth_token=None,
    )

    repo = FakeRepository(user)
    service = AuthenticationService(repo)

    result = await service.with_password(user.username, password, create_token=True)

    assert isinstance(result, dict)
    assert result["userId"] == "user-123"
    assert result["inactivityFlagsCleared"] is True
    assert repo.stored_token is not None
    assert repo.last_login_updated is True


@pytest.mark.asyncio
async def test_with_password_increments_failed_counter_when_password_invalid() -> None:
    password = "Passw0rd!"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = UserRecord(
        id="user-123",
        username="user@example.com",
        password_hash=hashed,
        active_raw=True,
        failed_login_attempts=1,
        last_login_at=None,
        last_failed_login_at=None,
        inactivity_flags=None,
        auth_token=None,
    )

    repo = FakeRepository(user)
    service = AuthenticationService(repo)

    result = await service.with_password(user.username, "wrong", create_token=True)

    assert result == "invalid-user-credentials"
    assert repo.increments == 1


@pytest.mark.asyncio
async def test_with_password_returns_account_locked_when_threshold_reached() -> None:
    password = "Passw0rd!"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.now(timezone.utc)

    user = UserRecord(
        id="user-123",
        username="user@example.com",
        password_hash=hashed,
        active_raw=True,
        failed_login_attempts=5,
        last_login_at=None,
        last_failed_login_at=now,
        inactivity_flags=None,
        auth_token=None,
    )

    repo = FakeRepository(user)
    service = AuthenticationService(repo)

    result = await service.with_password(user.username, password, create_token=True)

    assert result == "account-locked/max-login-attempts"


@pytest.mark.asyncio
async def test_update_token_extends_expiry() -> None:
    now = datetime.now(timezone.utc)
    token = AuthTokenData(
        token="abc",
        created_at=now - timedelta(hours=1),
        updated_at=now - timedelta(seconds=10),
        expires_at=now + timedelta(minutes=10),
    )

    user = UserRecord(
        id="user-123",
        username="user@example.com",
        password_hash=None,
        active_raw=True,
        failed_login_attempts=0,
        last_login_at=None,
        last_failed_login_at=None,
        inactivity_flags=None,
        auth_token=token,
    )

    repo = FakeRepository(user)
    service = AuthenticationService(repo)

    result = await service.update_token(token.token)

    assert isinstance(result, dict)
    assert repo.updated_token is not None
    assert repo.updated_token.expires_at > token.expires_at
    assert result["expiresIn"] > 0
