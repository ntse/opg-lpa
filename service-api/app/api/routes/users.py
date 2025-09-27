from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import (
    get_email_service,
    get_password_service,
    get_user_service,
    require_user_authorization,
)
from app.schemas.auth import AuthenticateResponse
from app.schemas.users import (
    EmailChangeRequest,
    EmailTokenResponse,
    EmailVerifyRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordTokenChangeRequest,
    UserCreateRequest,
    UserCreateResponse,
    UserDeletionLogResponse,
    UserSearchResponse,
    PasswordResetActivationResponse,
)
from app.services import EmailService, PasswordService, UsersService

router = APIRouter(prefix="/v2/users", tags=["users"])


@router.post("/", response_model=UserCreateResponse)
async def create_user(
    payload: UserCreateRequest,
    service: UsersService = Depends(get_user_service),
) -> UserCreateResponse | Response:
    if payload.activationToken:
        result = await service.activate(payload.activationToken.strip())
        if result is True:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        raise HTTPException(status_code=400, detail=result)

    if payload.username and payload.password:
        result = await service.create(payload.username.strip(), payload.password)
        if isinstance(result, str):
            raise HTTPException(status_code=400, detail=result)
        return UserCreateResponse(**result)

    raise HTTPException(status_code=400, detail="Either activationToken or username & password must be passed")


@router.get("/search", response_model=UserSearchResponse | UserDeletionLogResponse)
async def search_user(
    email: str,
    service: UsersService = Depends(get_user_service),
):
    result = await service.search_by_username(email.strip())
    if result is False:
        raise HTTPException(status_code=404, detail="No user found with supplied email address")

    if result.get("isDeleted"):
        return UserDeletionLogResponse(**result)

    return UserSearchResponse(**result)


@router.get("/match", response_model=list[UserSearchResponse])
async def match_users(
    query: str,
    offset: int = 0,
    limit: int = 10,
    service: UsersService = Depends(get_user_service),
) -> list[UserSearchResponse]:
    results = await service.match_users(query=query, offset=offset, limit=limit)
    return [UserSearchResponse(**record) for record in results]


@router.post("/{user_id}/email", response_model=EmailTokenResponse)
async def change_email(
    user_id: str,
    payload: EmailChangeRequest,
    _: None = Depends(require_user_authorization),
    service: EmailService = Depends(get_email_service),
) -> EmailTokenResponse:
    result = await service.generate_token(user_id, payload.newEmail)
    if isinstance(result, str):
        status_code = 400 if result != "user-not-found" else 404
        raise HTTPException(status_code=status_code, detail=result)
    return EmailTokenResponse(**result)


@router.post("/email")
async def verify_email(
    payload: EmailVerifyRequest,
    service: EmailService = Depends(get_email_service),
) -> Response:
    result = await service.update_email_using_token(payload.emailUpdateToken)
    if result.is_error:
        detail = result.error or "invalid-token"
        status_code = 400 if detail in {"username-already-exists"} else 404 if detail == "invalid-token" else 500
        raise HTTPException(status_code=status_code, detail=detail)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/password", response_model=AuthenticateResponse)
async def change_password_with_current(
    user_id: str,
    payload: PasswordChangeRequest,
    _: None = Depends(require_user_authorization),
    service: PasswordService = Depends(get_password_service),
) -> AuthenticateResponse:
    result = await service.change_password(user_id, payload.currentPassword, payload.newPassword)
    if isinstance(result, str):
        raise HTTPException(status_code=401, detail=result)
    return AuthenticateResponse(**result)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password_with_token(
    payload: PasswordTokenChangeRequest,
    service: PasswordService = Depends(get_password_service),
) -> Response:
    result = await service.update_password_using_token(payload.passwordToken, payload.newPassword)
    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    status_code = 400 if result in {"invalid-password", "nothing-modified"} else 404
    raise HTTPException(status_code=status_code, detail=result)


@router.post(
    "/password-reset",
    response_model=EmailTokenResponse | PasswordResetActivationResponse,
)
async def reset_password(
    payload: PasswordResetRequest,
    service: PasswordService = Depends(get_password_service),
):
    result = await service.generate_token(payload.username)
    if isinstance(result, str):
        if result == "user-not-found":
            raise HTTPException(status_code=404, detail=result)
        raise HTTPException(status_code=400, detail=result)
    if "activation_token" in result:
        return PasswordResetActivationResponse(**result)
    return EmailTokenResponse(**result)


__all__ = ["router"]
