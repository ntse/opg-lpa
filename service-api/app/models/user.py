from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    identity: Mapped[str | None] = mapped_column(String, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String)
    activation_token: Mapped[str | None] = mapped_column(String)

    active: Mapped[bool | None] = mapped_column(Boolean)
    failed_login_attempts: Mapped[int | None] = mapped_column(Integer, default=0)

    created: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    inactivity_flags: Mapped[dict | None] = mapped_column(JSONB)
    auth_token: Mapped[dict | None] = mapped_column(JSONB)
    email_update_request: Mapped[dict | None] = mapped_column(JSONB)
    password_reset_token: Mapped[dict | None] = mapped_column(JSONB)
    profile: Mapped[dict | None] = mapped_column(JSONB)


class DeletionLog(Base):
    __tablename__ = "deletion_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identity_hash: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    loggedAt: Mapped[datetime] = mapped_column("loggedAt", DateTime(timezone=True))


__all__ = ["Base", "User", "DeletionLog"]
