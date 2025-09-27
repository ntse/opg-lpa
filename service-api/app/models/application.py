from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[str] = mapped_column("user", String, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column("updatedAt", DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column("startedAt", DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column("createdAt", DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column("completedAt", DateTime(timezone=True))
    locked_at: Mapped[datetime | None] = mapped_column("lockedAt", DateTime(timezone=True))
    locked: Mapped[bool | None] = mapped_column(Boolean, default=False)
    who_are_you_answered: Mapped[bool | None] = mapped_column("whoAreYouAnswered", Boolean)
    seed: Mapped[bool | None] = mapped_column(Boolean)
    repeat_case_number: Mapped[str | None] = mapped_column("repeatCaseNumber", String)
    document: Mapped[dict | None] = mapped_column(JSONB)
    payment: Mapped[dict | None] = mapped_column(JSONB)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB)


__all__ = ["Application"]
