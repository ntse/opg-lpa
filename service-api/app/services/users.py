from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

import bcrypt
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.services.repositories import DeletionLogRepository, UserRecord, UserRepository
from app.utils import format_lpa_datetime, generate_token, is_password_valid


class UsersService:
    def __init__(self, users: UserRepository, logs: DeletionLogRepository) -> None:
        self.users = users
        self.logs = logs
        self._email_adapter: TypeAdapter[EmailStr] = TypeAdapter(EmailStr)

    async def create(self, username: str, password: str) -> dict | str:
        if not self._is_email_valid(username):
            return "invalid-username"

        existing = await self.users.get_by_username(username)
        if existing is not None:
            return "username-already-exists"

        if not is_password_valid(password):
            return "invalid-password"

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        created_at = datetime.now(timezone.utc)

        # Retry a few times in case of a collision on the generated identifiers
        for _ in range(5):
            user_id = secrets.token_hex(16)
            activation_token = generate_token(16)

            created = await self.users.create_user(
                user_id=user_id,
                username=username,
                password_hash=password_hash,
                activation_token=activation_token,
                created_at=created_at,
            )

            if created:
                return {
                    "userId": user_id,
                    "activation_token": activation_token,
                }

        return "username-already-exists"

    async def activate(self, activation_token: str) -> bool | str:
        success = await self.users.activate_user(activation_token, activated_at=datetime.now(timezone.utc))
        if not success:
            return "account-not-found"
        return True

    async def search_by_username(self, username: str) -> dict | bool:
        user = await self.users.get_by_username(username)
        if user is None:
            identity_hash = self._hash_identity(username)
            log = await self.logs.get_log_by_identity_hash(identity_hash)
            if log is None:
                return False

            return {
                "isDeleted": True,
                "deletedAt": format_lpa_datetime(log.logged_at),
                "reason": log.reason,
            }

        return self._record_to_dict(user)

    async def match_users(self, query: str, offset: int = 0, limit: int = 10) -> list[dict]:
        records = await self.users.match_users(query, offset=offset, limit=limit)
        return [self._record_to_dict(record) for record in records]

    async def delete(self, user_id: str, reason: str = "user-initiated") -> bool:
        identity_email = None
        user = await self.users.get_by_id(user_id)
        if user is not None and user.username:
            identity_email = user.username

        deleted = await self.users.delete_user(user_id, deleted_at=datetime.now(timezone.utc))
        if deleted:
            identity_hash = self._hash_identity(identity_email or user_id)
            await self.logs.add_log(identity_hash, "account-deleted", reason, datetime.now(timezone.utc))
        return deleted

    def _record_to_dict(self, record: UserRecord) -> dict:
        return {
            "userId": record.id,
            "username": record.username,
            "isActive": record.is_active(),
            "lastLoginAt": format_lpa_datetime(record.last_login_at),
            "updatedAt": format_lpa_datetime(record.updated_at),
            "createdAt": format_lpa_datetime(record.created_at),
            "activatedAt": format_lpa_datetime(record.activated_at),
            "lastFailedLoginAttemptAt": format_lpa_datetime(record.last_failed_login_at),
            "failedLoginAttempts": record.failed_login_attempts,
            "numberOfLpas": record.number_of_lpas,
        }

    def _hash_identity(self, identity: str) -> str:
        return hashlib.sha512(identity.strip().lower().encode("utf-8")).hexdigest()

    def _is_email_valid(self, email: str) -> bool:
        try:
            self._email_adapter.validate_python(email)
        except ValidationError:
            return False
        return True


__all__ = ["UsersService"]
