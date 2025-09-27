from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services import (
    ApplicationsService,
    AuthenticationService,
    CorrespondentService,
    DeletionLogRepository,
    DonorService,
    EmailService,
    InstructionService,
    LockService,
    NotifiedPeopleService,
    PaymentService,
    PdfService,
    PasswordService,
    PreferenceService,
    RepeatCaseNumberService,
    PrimaryAttorneyService,
    ReplacementAttorneyService,
    UsersService,
    WhoAreYouService,
    WhoIsRegisteringService,
)
from app.services.repositories import ApplicationRepository, UserRepository


async def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticationService:
    repository = UserRepository(session)
    return AuthenticationService(repository)


async def get_application_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ApplicationRepository:
    return ApplicationRepository(session)


async def get_applications_service(
    repository: ApplicationRepository = Depends(get_application_repository),
) -> ApplicationsService:
    return ApplicationsService(repository)


async def get_user_service(
    session: AsyncSession = Depends(get_db_session),
) -> UsersService:
    users = UserRepository(session)
    logs = DeletionLogRepository(session)
    return UsersService(users, logs)


async def get_email_service(
    session: AsyncSession = Depends(get_db_session),
) -> EmailService:
    users = UserRepository(session)
    return EmailService(users)


async def get_password_service(
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> PasswordService:
    users = UserRepository(session)
    return PasswordService(users, auth_service)


async def get_donor_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> DonorService:
    return DonorService(applications, repository)


async def get_primary_attorney_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> PrimaryAttorneyService:
    return PrimaryAttorneyService(applications, repository)


async def get_replacement_attorney_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> ReplacementAttorneyService:
    return ReplacementAttorneyService(applications, repository)


async def get_instruction_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> InstructionService:
    return InstructionService(applications, repository)


async def get_preference_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> PreferenceService:
    return PreferenceService(applications, repository)


async def get_lock_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> LockService:
    return LockService(applications, repository)


async def get_correspondent_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> CorrespondentService:
    return CorrespondentService(applications, repository)


async def get_repeat_case_number_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> RepeatCaseNumberService:
    return RepeatCaseNumberService(applications, repository)


async def get_notified_people_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> NotifiedPeopleService:
    return NotifiedPeopleService(applications, repository)


async def get_payment_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> PaymentService:
    return PaymentService(applications, repository)


async def get_pdf_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> PdfService:
    return PdfService(applications, repository)


async def get_who_are_you_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> WhoAreYouService:
    return WhoAreYouService(applications, repository)


async def get_who_is_registering_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> WhoIsRegisteringService:
    return WhoIsRegisteringService(applications, repository)


async def get_certificate_provider_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> CertificateProviderService:
    return CertificateProviderService(applications, repository)


async def get_type_service(
    applications: ApplicationsService = Depends(get_applications_service),
    repository: ApplicationRepository = Depends(get_application_repository),
) -> TypeService:
    return TypeService(applications, repository)


async def require_user_authorization(
    user_id: str,
    Token: str | None = Header(default=None),
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> None:
    if not Token:
        raise HTTPException(status_code=401, detail="Token header is required")

    result = await auth_service.with_token(Token.strip(), extend_token=False)

    if isinstance(result, str) or result.get("userId") != user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")


__all__ = [
    "get_auth_service",
    "get_applications_service",
    "get_user_service",
    "get_email_service",
    "get_password_service",
    "get_donor_service",
    "get_instruction_service",
    "get_preference_service",
    "get_lock_service",
    "get_correspondent_service",
    "get_repeat_case_number_service",
    "get_notified_people_service",
    "get_payment_service",
    "get_pdf_service",
    "get_primary_attorney_service",
    "get_replacement_attorney_service",
    "get_who_are_you_service",
    "get_who_is_registering_service",
    "get_certificate_provider_service",
    "get_type_service",
    "require_user_authorization",
]
