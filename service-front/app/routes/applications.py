"""Routes for managing LPA applications in the FastAPI front end."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Awaitable
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from ..config import Settings, get_settings
from ..services.api_client import ApiClient, ApiClientError, ApiConnectionError
from .auth import get_api_client

router = APIRouter(tags=["applications"])


def get_templates(settings: Settings) -> Jinja2Templates:
    return Jinja2Templates(directory=str(settings.template_path))


def _current_user(request: Request) -> dict | None:
    user = request.session.get("user")
    if not user:
        return None
    if not user.get("token") or not user.get("id"):
        return None
    return user


def _redirect(path: str, message: str | None = None, level: str = "success") -> RedirectResponse:
    if message:
        separator = "&" if "?" in path else "?"
        path = f"{path}{separator}{urlencode({level: message})}"
    return RedirectResponse(url=path, status_code=status.HTTP_303_SEE_OTHER)


def _handle_api_error(request: Request, error: ApiClientError, fallback_path: str) -> RedirectResponse:
    if error.status_code == 401:
        request.session.pop("user", None)
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return _redirect(fallback_path, message=str(error), level="error")


def _strip_value(value: object) -> object | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, dict):
        cleaned = {k: _strip_value(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v is not None} or None
    return value


def _parse_amount_to_pence(raw: str | None) -> int | None:
    if raw is None:
        return None
    cleaned = raw.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        pounds = Decimal(cleaned)
    except InvalidOperation as exc:  # pragma: no cover - error path exercised in tests
        raise ValueError("Enter a valid amount") from exc
    if pounds < 0:
        raise ValueError("Amount must be zero or more")
    return int((pounds * 100).quantize(Decimal("1")))


async def _fetch_pdf_statuses(api: ApiClient, token: str, user_id: str, application_id: int) -> dict[str, dict]:
    statuses: dict[str, dict] = {}
    for pdf_type in ("lp1", "lp3", "lpa120"):
        try:
            statuses[pdf_type] = await api.get_pdf_status(token, user_id, application_id, pdf_type)
        except ApiConnectionError:
            statuses[pdf_type] = {"status": "unavailable"}
        except ApiClientError as exc:
            statuses[pdf_type] = {"status": "error", "detail": str(exc)}
    return statuses


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard(
    request: Request,
    settings: Settings = Depends(get_settings),
    api: ApiClient = Depends(get_api_client),
    page: int = Query(1, ge=1),
    search: str | None = Query(None),
) -> Response:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    templates = get_templates(settings)
    success_message = request.query_params.get("success")
    error_message = request.query_params.get("error")

    try:
        payload = await api.list_applications(
            user["token"],
            user["id"],
            page=page,
            search=search or None,
        )
        applications = payload.get("applications", [])
        total = payload.get("total", len(applications))
    except ApiConnectionError:
        applications = []
        total = 0
        error_message = error_message or "Unable to reach the service API. Please try again."
    except ApiClientError as exc:
        return _handle_api_error(request, exc, "/login")

    context = {
        "request": request,
        "title": "Your lasting power of attorney applications",
        "applications": applications,
        "total": total,
        "page": page,
        "search": search or "",
        "success": success_message,
        "error": error_message,
        "user": user,
    }
    return templates.TemplateResponse(request, "applications/dashboard.html", context)


@router.get("/applications/new", response_class=HTMLResponse, name="application-new")
async def new_application_form(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    templates = get_templates(settings)
    context = {
        "request": request,
        "title": "Start a new application",
        "form": {},
        "errors": {},
    }
    return templates.TemplateResponse(request, "applications/new.html", context)


@router.post("/applications/new", response_class=HTMLResponse)
async def create_application(
    request: Request,
    settings: Settings = Depends(get_settings),
    api: ApiClient = Depends(get_api_client),
) -> Response:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    form_data = await request.form()
    form = {key: form_data.get(key, "") for key in form_data.keys()}
    who_are_you = form.get("who_are_you") or None
    who_is_registering = form.get("who_is_registering") or None
    application_type = form.get("application_type") or None

    try:
        created = await api.create_application(user["token"], user["id"], payload=None)
    except ApiConnectionError:
        templates = get_templates(settings)
        context = {
            "request": request,
            "title": "Start a new application",
            "form": form,
            "errors": {"__all__": "Unable to reach the service API. Please try again."},
        }
        return templates.TemplateResponse(request, "applications/new.html", context)
    except ApiClientError as exc:
        if exc.status_code == 401:
            request.session.pop("user", None)
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        templates = get_templates(settings)
        context = {
            "request": request,
            "title": "Start a new application",
            "form": form,
            "errors": {"__all__": str(exc)},
        }
        return templates.TemplateResponse(request, "applications/new.html", context)

    application_id = created.get("id")

    async def _attempt(call: Awaitable[object]) -> None:
        try:
            await call
        except (ApiClientError, ApiConnectionError):  # pragma: no cover - best effort, not fatal
            return

    if who_are_you:
        await _attempt(api.update_who_are_you(user["token"], user["id"], application_id, who_are_you))
    if who_is_registering is not None:
        await _attempt(
            api.update_who_is_registering(user["token"], user["id"], application_id, who_is_registering or None)
        )
    if application_type:
        await _attempt(api.update_type(user["token"], user["id"], application_id, application_type))

    return _redirect(
        f"/applications/{application_id}",
        message="Application created",
        level="success",
    )


@router.get(
    "/applications/{application_id}",
    response_class=HTMLResponse,
    name="application-detail",
)
async def application_detail(
    request: Request,
    application_id: int,
    settings: Settings = Depends(get_settings),
    api: ApiClient = Depends(get_api_client),
) -> Response:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        application = await api.get_application(user["token"], user["id"], application_id)
    except ApiConnectionError:
        return _redirect(
            "/dashboard",
            message="Unable to load the application right now. Please try again.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, "/dashboard")

    pdf_statuses = await _fetch_pdf_statuses(api, user["token"], user["id"], application_id)

    templates = get_templates(settings)
    context = {
        "request": request,
        "title": f"Application {application_id}",
        "application": application,
        "user": user,
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
        "pdf_statuses": pdf_statuses,
    }
    return templates.TemplateResponse(request, "applications/detail.html", context)


@router.post("/applications/{application_id}/type")
async def update_application_type(
    request: Request,
    application_id: int,
    lpa_type: str = Form(default=""),
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        await api.update_type(user["token"], user["id"], application_id, lpa_type or None)
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to save the LPA type. Please try again.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(f"/applications/{application_id}", message="Application type saved", level="success")


@router.post("/applications/{application_id}/registering")
async def update_who_is_registering(
    request: Request,
    application_id: int,
    who_is_registering: str = Form(default=""),
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        await api.update_who_is_registering(
            user["token"],
            user["id"],
            application_id,
            who_is_registering or None,
        )
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to update the registration details right now.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Registration details updated",
        level="success",
    )


@router.post("/applications/{application_id}/donor")
async def update_donor_details(
    request: Request,
    application_id: int,
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    donor = {
        "firstname": form.get("firstname"),
        "lastname": form.get("lastname"),
        "email": form.get("email"),
        "phone": form.get("phone"),
        "address": {
            "line1": form.get("address_line1"),
            "line2": form.get("address_line2"),
            "town": form.get("address_town"),
            "postcode": form.get("address_postcode"),
        },
    }
    donor = _strip_value(donor) or {}

    try:
        await api.update_donor(user["token"], user["id"], application_id, donor)
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to save donor details. Please try again.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Donor details saved",
        level="success",
    )


@router.post("/applications/{application_id}/instruction")
async def update_instruction(
    request: Request,
    application_id: int,
    instruction: str = Form(default=""),
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        await api.update_instruction(
            user["token"],
            user["id"],
            application_id,
            instruction.strip() or None,
        )
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to save instructions at the moment.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Instructions saved",
        level="success",
    )


@router.post("/applications/{application_id}/preference")
async def update_preference(
    request: Request,
    application_id: int,
    preference: str = Form(default=""),
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        await api.update_preference(
            user["token"],
            user["id"],
            application_id,
            preference.strip() or None,
        )
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to save preferences at the moment.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Preferences saved",
        level="success",
    )


@router.post("/applications/{application_id}/repeat-case-number")
async def update_repeat_case_number(
    request: Request,
    application_id: int,
    repeat_case_number: str = Form(default=""),
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    trimmed = repeat_case_number.strip()

    try:
        if trimmed:
            await api.update_repeat_case_number(user["token"], user["id"], application_id, trimmed)
            message = "Repeat case number saved"
        else:
            await api.delete_repeat_case_number(user["token"], user["id"], application_id)
            message = "Repeat case number cleared"
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to update the repeat case number right now.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(f"/applications/{application_id}", message=message, level="success")


@router.post("/applications/{application_id}/certificate-provider")
async def update_certificate_provider(
    request: Request,
    application_id: int,
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    provider = _strip_value(
        {
            "name": form.get("cp_name"),
            "email": form.get("cp_email"),
            "phone": form.get("cp_phone"),
            "address": {
                "line1": form.get("cp_address_line1"),
                "line2": form.get("cp_address_line2"),
                "town": form.get("cp_address_town"),
                "postcode": form.get("cp_address_postcode"),
            },
        }
    )

    try:
        if provider:
            await api.update_certificate_provider(user["token"], user["id"], application_id, provider)
            message = "Certificate provider saved"
        else:
            await api.delete_certificate_provider(user["token"], user["id"], application_id)
            message = "Certificate provider removed"
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to update the certificate provider right now.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(f"/applications/{application_id}", message=message, level="success")


@router.post("/applications/{application_id}/payment")
async def update_payment_details(
    request: Request,
    application_id: int,
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    method = (form.get("payment_method") or "").strip()
    reference = (form.get("payment_reference") or "").strip()
    amount_raw = form.get("payment_amount")

    try:
        amount_pence = _parse_amount_to_pence(amount_raw)
    except ValueError as exc:
        return _redirect(
            f"/applications/{application_id}",
            message=str(exc),
            level="error",
        )

    payload: dict[str, Any] = {}
    if method:
        payload["method"] = method
    if amount_pence is not None:
        payload["amount"] = amount_pence
    if reference:
        payload["reference"] = reference

    if not payload:
        return _redirect(
            f"/applications/{application_id}",
            message="Enter payment details to save",
            level="error",
        )

    try:
        await api.update_payment(user["token"], user["id"], application_id, payload)
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to update payment details right now.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Payment details saved",
        level="success",
    )


@router.post("/applications/{application_id}/lock")
async def lock_application(
    request: Request,
    application_id: int,
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        await api.lock_application(user["token"], user["id"], application_id)
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to lock the application right now.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Application locked",
        level="success",
    )


@router.post("/applications/{application_id}/primary-attorneys")
async def add_primary_attorney(
    request: Request,
    application_id: int,
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    attorney_payload = _strip_value(
        {
            "name": form.get("attorney_name"),
            "email": form.get("attorney_email"),
            "type": form.get("attorney_type") or "human",
        }
    ) or {}

    if not attorney_payload.get("name"):
        return _redirect(
            f"/applications/{application_id}",
            message="Enter the attorney's name",
            level="error",
        )

    try:
        await api.add_primary_attorney(user["token"], user["id"], application_id, attorney_payload)
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to add the attorney right now.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Attorney added",
        level="success",
    )


@router.post("/applications/{application_id}/primary-attorneys/{attorney_id}/delete")
async def delete_primary_attorney(
    request: Request,
    application_id: int,
    attorney_id: int,
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        await api.delete_primary_attorney(user["token"], user["id"], application_id, attorney_id)
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to remove the attorney right now.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Attorney removed",
        level="success",
    )


@router.post("/applications/{application_id}/notified-people")
async def add_notified_person(
    request: Request,
    application_id: int,
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()
    payload = _strip_value(
        {
            "name": form.get("notify_name"),
            "email": form.get("notify_email"),
            "relationship": form.get("notify_relationship"),
        }
    ) or {}

    if not payload.get("name"):
        return _redirect(
            f"/applications/{application_id}",
            message="Enter the person's name",
            level="error",
        )

    try:
        await api.add_notified_person(user["token"], user["id"], application_id, payload)
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to add the person to notify right now.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Person to notify added",
        level="success",
    )


@router.post("/applications/{application_id}/notified-people/{person_id}/delete")
async def delete_notified_person(
    request: Request,
    application_id: int,
    person_id: int,
    api: ApiClient = Depends(get_api_client),
) -> RedirectResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        await api.delete_notified_person(user["token"], user["id"], application_id, person_id)
    except ApiConnectionError:
        return _redirect(
            f"/applications/{application_id}",
            message="Unable to remove the person to notify right now.",
            level="error",
        )
    except ApiClientError as exc:
        return _handle_api_error(request, exc, f"/applications/{application_id}")

    return _redirect(
        f"/applications/{application_id}",
        message="Person removed",
        level="success",
    )


__all__ = ["router"]
