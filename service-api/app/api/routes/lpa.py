from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import (
    get_applications_service,
    get_correspondent_service,
    get_donor_service,
    get_instruction_service,
    get_lock_service,
    get_notified_people_service,
    get_payment_service,
    get_pdf_service,
    get_preference_service,
    get_repeat_case_number_service,
    get_primary_attorney_service,
    get_replacement_attorney_service,
    get_certificate_provider_service,
    get_type_service,
    get_who_are_you_service,
    get_who_is_registering_service,
    require_user_authorization,
)
from app.services import (
    ApplicationsService,
    CertificateProviderService,
    CorrespondentService,
    DonorService,
    InstructionService,
    LockService,
    NotifiedPeopleService,
    PaymentService,
    PdfService,
    PreferenceService,
    RepeatCaseNumberService,
    PrimaryAttorneyService,
    ReplacementAttorneyService,
    TypeService,
    WhoAreYouService,
    WhoIsRegisteringService,
)

router = APIRouter(prefix="/v2/user", tags=["lpa"])


@router.get("/{user_id}/applications")
async def list_applications(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100, alias="perPage"),
    search: str | None = Query(None),
    _: None = Depends(require_user_authorization),
    service: ApplicationsService = Depends(get_applications_service),
):
    return await service.fetch_all(user_id, page=page, per_page=per_page, search=search)


@router.post("/{user_id}/applications", status_code=status.HTTP_201_CREATED)
async def create_application(
    user_id: str,
    payload: dict | None = None,
    _: None = Depends(require_user_authorization),
    service: ApplicationsService = Depends(get_applications_service),
):
    return await service.create(user_id, payload)


@router.get("/{user_id}/applications/{application_id}")
async def get_application(
    user_id: str,
    application_id: int,
    _: None = Depends(require_user_authorization),
    service: ApplicationsService = Depends(get_applications_service),
):
    return await service.fetch(user_id, application_id)


@router.patch("/{user_id}/applications/{application_id}")
async def patch_application(
    user_id: str,
    application_id: int,
    payload: dict | None = None,
    _: None = Depends(require_user_authorization),
    service: ApplicationsService = Depends(get_applications_service),
):
    return await service.patch(user_id, application_id, payload)


@router.delete("/{user_id}/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    user_id: str,
    application_id: int,
    _: None = Depends(require_user_authorization),
    service: ApplicationsService = Depends(get_applications_service),
):
    await service.delete(user_id, application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{user_id}/applications/{application_id}/donor")
async def update_donor(
    user_id: str,
    application_id: int,
    payload: dict | None = None,
    _: None = Depends(require_user_authorization),
    service: DonorService = Depends(get_donor_service),
):
    return await service.update(user_id, application_id, payload)


@router.put("/{user_id}/applications/{application_id}/instruction")
async def update_instruction(
    user_id: str,
    application_id: int,
    payload: dict | None = None,
    _: None = Depends(require_user_authorization),
    service: InstructionService = Depends(get_instruction_service),
):
    return await service.update(user_id, application_id, payload)


@router.put("/{user_id}/applications/{application_id}/preference")
async def update_preference(
    user_id: str,
    application_id: int,
    payload: dict | None = None,
    _: None = Depends(require_user_authorization),
    service: PreferenceService = Depends(get_preference_service),
):
    return await service.update(user_id, application_id, payload)


@router.put("/{user_id}/applications/{application_id}/correspondent")
async def update_correspondent(
    user_id: str,
    application_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: CorrespondentService = Depends(get_correspondent_service),
):
    return await service.update(user_id, application_id, payload)


@router.delete("/{user_id}/applications/{application_id}/correspondent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_correspondent(
    user_id: str,
    application_id: int,
    _: None = Depends(require_user_authorization),
    service: CorrespondentService = Depends(get_correspondent_service),
):
    await service.delete(user_id, application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{user_id}/applications/{application_id}/repeat-case-number")
async def update_repeat_case_number(
    user_id: str,
    application_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: RepeatCaseNumberService = Depends(get_repeat_case_number_service),
):
    return await service.update(user_id, application_id, payload)


@router.delete("/{user_id}/applications/{application_id}/repeat-case-number", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repeat_case_number(
    user_id: str,
    application_id: int,
    _: None = Depends(require_user_authorization),
    service: RepeatCaseNumberService = Depends(get_repeat_case_number_service),
):
    await service.delete(user_id, application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/applications/{application_id}/notified-people", status_code=status.HTTP_201_CREATED)
async def create_notified_person(
    user_id: str,
    application_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: NotifiedPeopleService = Depends(get_notified_people_service),
):
    return await service.create(user_id, application_id, payload)


@router.put("/{user_id}/applications/{application_id}/notified-people/{person_id}")
async def update_notified_person(
    user_id: str,
    application_id: int,
    person_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: NotifiedPeopleService = Depends(get_notified_people_service),
):
    return await service.update(user_id, application_id, person_id, payload)


@router.delete("/{user_id}/applications/{application_id}/notified-people/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notified_person(
    user_id: str,
    application_id: int,
    person_id: int,
    _: None = Depends(require_user_authorization),
    service: NotifiedPeopleService = Depends(get_notified_people_service),
):
    await service.delete(user_id, application_id, person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{user_id}/applications/{application_id}/certificate-provider")
async def update_certificate_provider(
    user_id: str,
    application_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: CertificateProviderService = Depends(get_certificate_provider_service),
):
    return await service.update(user_id, application_id, payload)


@router.delete(
    "/{user_id}/applications/{application_id}/certificate-provider",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_certificate_provider(
    user_id: str,
    application_id: int,
    _: None = Depends(require_user_authorization),
    service: CertificateProviderService = Depends(get_certificate_provider_service),
):
    await service.delete(user_id, application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{user_id}/applications/{application_id}/type")
async def update_type(
    user_id: str,
    application_id: int,
    payload: dict | None = None,
    _: None = Depends(require_user_authorization),
    service: TypeService = Depends(get_type_service),
):
    return await service.update(user_id, application_id, payload)


@router.put("/{user_id}/applications/{application_id}/payment")
async def update_payment(
    user_id: str,
    application_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.update(user_id, application_id, payload)


@router.get("/{user_id}/applications/{application_id}/pdfs/{pdf_type}")
async def get_pdf_status(
    user_id: str,
    application_id: int,
    pdf_type: str,
    _: None = Depends(require_user_authorization),
    service: PdfService = Depends(get_pdf_service),
):
    return await service.fetch(user_id, application_id, pdf_type)


@router.post("/{user_id}/applications/{application_id}/lock", status_code=status.HTTP_201_CREATED)
async def lock_application(
    user_id: str,
    application_id: int,
    _: None = Depends(require_user_authorization),
    service: LockService = Depends(get_lock_service),
):
    return await service.lock(user_id, application_id)


@router.post("/{user_id}/applications/{application_id}/primary-attorneys", status_code=status.HTTP_201_CREATED)
async def create_primary_attorney(
    user_id: str,
    application_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: PrimaryAttorneyService = Depends(get_primary_attorney_service),
):
    return await service.create(user_id, application_id, payload)


@router.put("/{user_id}/applications/{application_id}/primary-attorneys/{attorney_id}")
async def update_primary_attorney(
    user_id: str,
    application_id: int,
    attorney_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: PrimaryAttorneyService = Depends(get_primary_attorney_service),
):
    return await service.update(user_id, application_id, attorney_id, payload)


@router.delete("/{user_id}/applications/{application_id}/primary-attorneys/{attorney_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_primary_attorney(
    user_id: str,
    application_id: int,
    attorney_id: int,
    _: None = Depends(require_user_authorization),
    service: PrimaryAttorneyService = Depends(get_primary_attorney_service),
):
    await service.delete(user_id, application_id, attorney_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/applications/{application_id}/replacement-attorneys", status_code=status.HTTP_201_CREATED)
async def create_replacement_attorney(
    user_id: str,
    application_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: ReplacementAttorneyService = Depends(get_replacement_attorney_service),
):
    return await service.create(user_id, application_id, payload)


@router.put("/{user_id}/applications/{application_id}/replacement-attorneys/{attorney_id}")
async def update_replacement_attorney(
    user_id: str,
    application_id: int,
    attorney_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: ReplacementAttorneyService = Depends(get_replacement_attorney_service),
):
    return await service.update(user_id, application_id, attorney_id, payload)


@router.delete("/{user_id}/applications/{application_id}/replacement-attorneys/{attorney_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_replacement_attorney(
    user_id: str,
    application_id: int,
    attorney_id: int,
    _: None = Depends(require_user_authorization),
    service: ReplacementAttorneyService = Depends(get_replacement_attorney_service),
):
    await service.delete(user_id, application_id, attorney_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{user_id}/applications/{application_id}/who-are-you")
async def update_who_are_you(
    user_id: str,
    application_id: int,
    payload: dict,
    _: None = Depends(require_user_authorization),
    service: WhoAreYouService = Depends(get_who_are_you_service),
):
    return await service.update(user_id, application_id, payload)


@router.put("/{user_id}/applications/{application_id}/who-is-registering")
async def update_who_is_registering(
    user_id: str,
    application_id: int,
    payload: dict | None = None,
    _: None = Depends(require_user_authorization),
    service: WhoIsRegisteringService = Depends(get_who_is_registering_service),
):
    return await service.update(user_id, application_id, payload)


__all__ = ["router"]
