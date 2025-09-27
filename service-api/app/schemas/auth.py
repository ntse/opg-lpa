from __future__ import annotations

from pydantic import BaseModel, Field


class AuthenticateRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    authToken: str | None = None
    Update: str | bool | None = Field(default=None, description="When false, token expiry is not extended")

    def should_update_token(self) -> bool:
        if isinstance(self.Update, bool):
            return self.Update
        if isinstance(self.Update, str):
            return self.Update.lower() != "false"
        return True


class AuthenticateResponse(BaseModel):
    userId: str
    username: str | None = None
    last_login: str | None = None
    inactivityFlagsCleared: bool | None = None
    token: str | None = None
    expiresIn: int | None = None
    expiresAt: str | None = None


class TokenValidationResponse(BaseModel):
    token: str
    userId: str
    username: str | None = None
    last_login: str | None = None
    expiresIn: int
    expiresAt: str | None = None


class SessionStatusResponse(BaseModel):
    valid: bool
    remainingSeconds: int | None = None
    problem: str | None = None


class SessionExpiryRequest(BaseModel):
    expireInSeconds: int


__all__ = [
    "AuthenticateRequest",
    "AuthenticateResponse",
    "TokenValidationResponse",
    "SessionStatusResponse",
    "SessionExpiryRequest",
]
