from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from random import randint
from typing import Any

from dateutil import parser
from sqlalchemy import and_, cast, delete, func, insert, select, update
from sqlalchemy.types import String as SQLString
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.user import DeletionLog, User


@dataclass(slots=True)
class AuthTokenData:
    token: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime

    @property
    def expires_in_seconds(self) -> int:
        return int(abs((self.expires_at - datetime.now(timezone.utc)).total_seconds()))

    @classmethod
    def from_raw(cls, raw: dict | None) -> "AuthTokenData | None":
        if not raw:
            return None
        try:
            def _dt(value: object) -> datetime:
                if isinstance(value, datetime):
                    return value
                return parser.isoparse(str(value))

            return cls(
                token=raw["token"],
                created_at=_dt(raw.get("createdAt")),
                updated_at=_dt(raw.get("updatedAt")),
                expires_at=_dt(raw.get("expiresAt")),
            )
        except Exception:
            return None

    def to_json(self) -> dict:
        return {
            "token": self.token,
            "createdAt": self.created_at.astimezone(timezone.utc).isoformat(),
            "updatedAt": self.updated_at.astimezone(timezone.utc).isoformat(),
            "expiresAt": self.expires_at.astimezone(timezone.utc).isoformat(),
        }


@dataclass(slots=True)
class UserRecord:
    id: str
    username: str | None
    password_hash: str | None
    active_raw: bool | str | None
    failed_login_attempts: int
    last_login_at: datetime | None
    last_failed_login_at: datetime | None
    inactivity_flags: dict | None
    auth_token: AuthTokenData | None
    number_of_lpas: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    activated_at: datetime | None = None
    deleted_at: datetime | None = None
    activation_token: str | None = None

    def is_active(self) -> bool:
        value = self.active_raw

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.upper() == "Y"

        return False


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(
        self,
        user_id: str,
        username: str,
        password_hash: str,
        activation_token: str,
        created_at: datetime,
    ) -> bool:
        stmt = insert(User).values(
            id=user_id,
            identity=username,
            password_hash=password_hash,
            activation_token=activation_token,
            active=False,
            failed_login_attempts=0,
            created=created_at,
            updated=created_at,
        )

        try:
            await self.session.execute(stmt)
        except IntegrityError:
            return False

        return True

    async def get_by_username(self, username: str) -> UserRecord | None:
        stmt = select(User).where(User.identity == username).limit(1)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_record(user)

    async def activate_user(self, token: str, *, activated_at: datetime) -> bool:
        stmt = (
            update(User)
            .where(User.activation_token == token)
            .values(
                active=True,
                updated=activated_at,
                activated=activated_at,
                activation_token=None,
            )
            .returning(User.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_auth_token(self, token: str) -> UserRecord | None:
        stmt = select(User).where(User.auth_token["token"].astext == token).limit(1)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_record(user)

    async def get_by_id(self, user_id: str) -> UserRecord | None:
        stmt = select(User).where(User.id == user_id).limit(1)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_record(user)

    async def match_users(self, query: str, *, offset: int = 0, limit: int = 10) -> list[UserRecord]:
        pattern = f"%{query}%"
        stmt = (
            select(User)
            .where(User.identity.ilike(pattern))
            .order_by(User.identity.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return [self._to_record(user) for user in result.scalars()]

    async def update_last_login_time(self, user_id: str) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login=now, inactivity_flags=None)
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def set_new_password(self, user_id: str, password_hash: str) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(password_hash=password_hash, updated=now, auth_token=None)
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def reset_failed_login_counter(self, user_id: str) -> bool:
        stmt = update(User).where(User.id == user_id).values(failed_login_attempts=0)
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def increment_failed_login_counter(self, user_id: str) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                last_failed_login=now,
                failed_login_attempts=func.coalesce(User.failed_login_attempts, 0) + 1,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def set_auth_token(self, user_id: str, token: AuthTokenData) -> bool:
        stmt = update(User).where(User.id == user_id).values(auth_token=token.to_json())
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def update_auth_token_expiry(self, user_id: str, token: AuthTokenData) -> bool:
        stmt = update(User).where(User.id == user_id).values(auth_token=token.to_json())
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def add_password_reset_token(self, user_id: str, token: AuthTokenData) -> bool:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(password_reset_token=token.to_json())
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def get_by_reset_token(self, token: str) -> UserRecord | None:
        stmt = select(User).where(User.password_reset_token["token"].astext == token).limit(1)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._to_record(user)

    async def update_password_using_token(self, token: str, password_hash: str) -> tuple[bool, str | None]:
        stmt = (
            update(User)
            .where(User.password_reset_token["token"].astext == token)
            .values(
                password_hash=password_hash,
                password_reset_token=None,
                updated=datetime.now(timezone.utc),
                auth_token=None,
            )
        )
        result = await self.session.execute(stmt)
        if result.rowcount == 1:
            return True, None
        return False, "nothing-modified"

    async def add_email_update_token_and_new_email(
        self, user_id: str, token: AuthTokenData, new_email: str
    ) -> bool:
        payload = {
            "token": token.to_json(),
            "email": new_email,
        }
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(email_update_request=payload)
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def update_email_using_token(self, token: str) -> tuple[bool, str | None, UserRecord | None]:
        stmt = select(User).where(User.email_update_request["token"]["token"].astext == token).limit(1)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None or not user.email_update_request:
            return False, "invalid-token", None

        request = user.email_update_request
        token_payload = request.get("token", {})

        try:
            expires_at = token_payload.get("expiresAt")
            if isinstance(expires_at, datetime):
                expiry_dt = expires_at
            else:
                expiry_dt = parser.isoparse(expires_at)
        except Exception:
            return False, "invalid-token", None

        if expiry_dt < datetime.now(timezone.utc):
            return False, "invalid-token", None

        new_email = request.get("email")
        if not new_email:
            return False, "invalid-token", None

        clash_stmt = select(User.id).where(User.identity == new_email, User.id != user.id).limit(1)
        clash = await self.session.execute(clash_stmt)
        if clash.scalar_one_or_none():
            return False, "username-already-exists", None

        update_stmt = (
            update(User)
            .where(User.id == user.id)
            .values(identity=new_email, updated=datetime.now(timezone.utc), email_update_request=None)
            .returning(User.id)
        )
        updated = await self.session.execute(update_stmt)
        if updated.scalar_one_or_none() is None:
            return False, "nothing-modified", None

        return True, None, self._to_record(user)

    async def delete_user(self, user_id: str, deleted_at: datetime) -> bool:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                deleted=deleted_at,
                active=None,
                identity=None,
                password_hash=None,
                activation_token=None,
                failed_login_attempts=None,
                created=None,
                updated=None,
                activated=None,
                last_login=None,
                last_failed_login=None,
                inactivity_flags=None,
                auth_token=None,
                email_update_request=None,
                password_reset_token=None,
                profile=None,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    def _to_record(self, user: User | None) -> UserRecord | None:
        if user is None:
            return None

        auth_token = AuthTokenData.from_raw(user.auth_token)

        return UserRecord(
            id=user.id,
            username=user.identity,
            password_hash=user.password_hash,
            active_raw=user.active,
            failed_login_attempts=user.failed_login_attempts or 0,
            last_login_at=user.last_login,
            last_failed_login_at=user.last_failed_login,
            inactivity_flags=user.inactivity_flags,
            auth_token=auth_token,
            number_of_lpas=user.profile.get("numberOfLpas") if isinstance(user.profile, dict) else None,
            created_at=user.created,
            updated_at=user.updated,
            activated_at=user.activated,
            deleted_at=user.deleted,
            activation_token=user.activation_token,
        )


@dataclass(slots=True)
class ApplicationRecord:
    id: int
    user_id: str
    updated_at: datetime | None
    started_at: datetime | None
    created_at: datetime | None
    completed_at: datetime | None
    locked_at: datetime | None
    locked: bool | None
    who_are_you_answered: bool | None
    seed: bool | None
    repeat_case_number: str | None
    document: dict | None
    payment: dict | None
    metadata: dict | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user": self.user_id,
            "updatedAt": self.updated_at,
            "startedAt": self.started_at,
            "createdAt": self.created_at,
            "completedAt": self.completed_at,
            "lockedAt": self.locked_at,
            "locked": self.locked,
            "whoAreYouAnswered": self.who_are_you_answered,
            "seed": self.seed,
            "repeatCaseNumber": self.repeat_case_number,
            "document": self.document,
            "payment": self.payment,
            "metadata": self.metadata,
        }


class ApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_id(self) -> int:
        for _ in range(10):
            candidate = randint(1_000_000, 99_999_999_999)
            exists = await self.session.execute(
                select(Application.id).where(Application.id == candidate)
            )
            if exists.scalar_one_or_none() is None:
                return candidate
        raise RuntimeError("unable to generate unique LPA id")

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
        stmt = insert(Application).values(
            id=application_id,
            user=user_id,
            document=document,
            metadata_json=metadata,
            payment=payment,
            repeatCaseNumber=repeat_case_number,
            startedAt=started_at,
            updatedAt=updated_at,
            createdAt=started_at,
            locked=False,
            whoAreYouAnswered=False,
        )
        try:
            await self.session.execute(stmt)
        except IntegrityError as exc:  # pragma: no cover - defensive, should be rare
            if "unique" in str(exc).lower():
                raise RuntimeError("duplicate application id") from exc
            raise
        return await self.get_by_id(application_id, user_id)

    async def get_by_id(
        self, application_id: int, user_id: str | None = None
    ) -> ApplicationRecord | None:
        filters = [Application.id == application_id]
        if user_id is not None:
            filters.append(Application.user_id == user_id)

        result = await self.session.execute(select(Application).where(and_(*filters)).limit(1))
        row = result.scalar_one_or_none()
        return self._to_record(row)

    async def list_by_user(
        self,
        user_id: str,
        *,
        search: str | None = None,
        offset: int = 0,
        limit: int = 25,
    ) -> tuple[list[ApplicationRecord], int]:
        filters = [Application.user_id == user_id]
        if search:
            term = search.strip()
            if term.isdigit():
                filters.append(Application.id == int(term))
            else:
                normalised = term.replace(" ", "")
                if normalised.upper().startswith("A") and normalised[1:].isdigit():
                    filters.append(Application.id == int(normalised[1:]))
                elif len(term) >= 3:
                    filters.append(cast(Application.document, SQLString).ilike(f"%{term}%"))

        where_clause = and_(*filters)
        total_result = await self.session.execute(
            select(func.count()).select_from(Application).where(where_clause)
        )
        total = total_result.scalar_one()

        if total == 0:
            return [], 0

        query = (
            select(Application)
            .where(where_clause)
            .order_by(Application.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )

        records = await self.session.execute(query)
        return [self._to_record(row) for row in records.scalars()], total

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
        values: dict[Any, Any] = {}
        if document is not None:
            values[Application.document] = document
        if metadata is not None:
            values[Application.metadata_json] = metadata
        if payment is not None:
            values[Application.payment] = payment
        if repeat_case_number is not None:
            values[Application.repeat_case_number] = repeat_case_number
        if locked is not None:
            values[Application.locked] = locked
        if locked_at is not None:
            values[Application.locked_at] = locked_at
        if who_are_you_answered is not None:
            values[Application.who_are_you_answered] = who_are_you_answered
        if updated_at is not None:
            values[Application.updated_at] = updated_at

        if not values:
            return False

        stmt = (
            update(Application)
            .where(and_(Application.id == application_id, Application.user_id == user_id))
            .values(values)
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def delete_application(self, application_id: int, user_id: str) -> bool:
        stmt = delete(Application).where(
            and_(Application.id == application_id, Application.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    def _to_record(self, application: Application | None) -> ApplicationRecord | None:
        if application is None:
            return None

        return ApplicationRecord(
            id=application.id,
            user_id=application.user_id,
            updated_at=application.updated_at,
            started_at=application.started_at,
            created_at=application.created_at,
            completed_at=application.completed_at,
            locked_at=application.locked_at,
            locked=application.locked,
            who_are_you_answered=application.who_are_you_answered,
            seed=application.seed,
            repeat_case_number=application.repeat_case_number,
            document=application.document or {},
            payment=application.payment or {},
            metadata=application.metadata_json or {},
        )


@dataclass(slots=True)
class DeletionLogRecord:
    identity_hash: str
    type: str
    reason: str
    logged_at: datetime


class DeletionLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_log(self, identity_hash: str, log_type: str, reason: str, logged_at: datetime) -> bool:
        stmt = insert(DeletionLog).values(
            identity_hash=identity_hash,
            type=log_type,
            reason=reason,
            loggedAt=logged_at,
        )
        try:
            await self.session.execute(stmt)
        except IntegrityError:
            return False
        return True

    async def get_log_by_identity_hash(self, identity_hash: str) -> DeletionLogRecord | None:
        stmt = (
            select(DeletionLog)
            .where(DeletionLog.identity_hash == identity_hash)
            .order_by(DeletionLog.loggedAt.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return DeletionLogRecord(
            identity_hash=record.identity_hash,
            type=record.type,
            reason=record.reason,
            logged_at=record.loggedAt,
        )


__all__ = [
    "AuthTokenData",
    "UserRecord",
    "UserRepository",
    "ApplicationRecord",
    "ApplicationRepository",
    "DeletionLogRecord",
    "DeletionLogRepository",
]
