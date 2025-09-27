from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.deps import get_auth_service
from app.schemas.auth import (
    AuthenticateRequest,
    AuthenticateResponse,
    SessionExpiryRequest,
    SessionStatusResponse,
)
from app.services.authentication import AuthenticationService

router = APIRouter(prefix="/v2", tags=["auth"])


@router.post("/authenticate", response_model=AuthenticateResponse)
async def authenticate(
    payload: AuthenticateRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> AuthenticateResponse:
    update_token = payload.should_update_token()
    response: dict | str | None = None

    if payload.authToken:
        response = await auth_service.with_token(payload.authToken.strip(), extend_token=update_token)
    elif payload.username and payload.password:
        response = await auth_service.with_password(
            payload.username.strip(), payload.password, create_token=update_token
        )
    else:
        raise HTTPException(status_code=400, detail="Either token or username & password must be passed")

    if isinstance(response, str):
        raise HTTPException(status_code=401, detail=response)

    return AuthenticateResponse(**response)


@router.get("/session-expiry", response_model=SessionStatusResponse)
async def session_expiry(
    CheckedToken: str | None = Header(default=None),
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> SessionStatusResponse:
    if not CheckedToken:
        raise HTTPException(status_code=400, detail="No CheckedToken was specified in the header")

    result = await auth_service.with_token(CheckedToken.strip(), extend_token=False)

    if isinstance(result, str):
        return SessionStatusResponse(valid=False, problem=result)

    return SessionStatusResponse(valid=True, remainingSeconds=result["expiresIn"])


@router.post("/session-set-expiry", response_model=SessionStatusResponse)
async def set_session_expiry(
    payload: SessionExpiryRequest,
    CheckedToken: str | None = Header(default=None),
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> SessionStatusResponse:
    if not CheckedToken:
        raise HTTPException(status_code=400, detail="No CheckedToken was specified in the header")

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=payload.expireInSeconds)

    result = await auth_service.update_token(
        CheckedToken.strip(),
        needs_update=True,
        throttle=False,
        expires_at=expires_at,
    )

    if isinstance(result, str):
        return SessionStatusResponse(valid=False, problem=result)

    return SessionStatusResponse(valid=True, remainingSeconds=result["expiresIn"])


__all__ = ["router"]
