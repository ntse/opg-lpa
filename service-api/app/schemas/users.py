from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    activationToken: Optional[str] = None


class UserCreateResponse(BaseModel):
    userId: str
    activation_token: str


class UserActivationResponse(BaseModel):
    success: bool


class UserSearchResponse(BaseModel):
    userId: str
    username: str | None
    isActive: bool
    lastLoginAt: str | None = None
    updatedAt: str | None = None
    createdAt: str | None = None
    activatedAt: str | None = None
    lastFailedLoginAttemptAt: str | None = None
    failedLoginAttempts: int | None = None
    numberOfLpas: int | None = None


class UserDeletionLogResponse(BaseModel):
    isDeleted: bool
    deletedAt: str | None = None
    reason: str | None = None


class EmailChangeRequest(BaseModel):
    newEmail: str = Field(..., alias="newEmail")


class EmailTokenResponse(BaseModel):
    token: str
    expiresIn: int
    expiresAt: str | None = None


class EmailVerifyRequest(BaseModel):
    emailUpdateToken: str


class PasswordChangeRequest(BaseModel):
    currentPassword: str
    newPassword: str


class PasswordTokenChangeRequest(BaseModel):
    passwordToken: str
    newPassword: str


class PasswordResetRequest(BaseModel):
    username: str


class PasswordResetActivationResponse(BaseModel):
    activation_token: str | None = None


__all__ = [
    "UserCreateRequest",
    "UserCreateResponse",
    "UserActivationResponse",
    "UserSearchResponse",
    "UserDeletionLogResponse",
    "EmailChangeRequest",
    "EmailTokenResponse",
    "EmailVerifyRequest",
    "PasswordChangeRequest",
    "PasswordTokenChangeRequest",
    "PasswordResetRequest",
    "PasswordResetActivationResponse",
]
