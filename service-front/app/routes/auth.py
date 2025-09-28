"""Routes for account registration and authentication."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator, ValidationInfo

from ..config import Settings, get_settings
from ..services.api_client import ApiClient, ApiClientError, ApiConnectionError

router = APIRouter(tags=["auth"])


def get_templates(settings: Settings) -> Jinja2Templates:
    return Jinja2Templates(directory=str(settings.template_path))


def get_api_client(settings: Settings = Depends(get_settings)) -> ApiClient:
    return ApiClient(base_url=str(settings.api_base_url), timeout=settings.api_request_timeout)


class RegistrationForm(BaseModel):
    email: EmailStr = Field(alias="email")
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, value: str, info: ValidationInfo) -> str:
        password = info.data.get("password")
        if password and value != password:
            raise ValueError("Passwords do not match")
        return value


class LoginForm(BaseModel):
    email: EmailStr = Field(alias="email")
    password: str


def _render_template(
    request: Request,
    template: str,
    settings: Settings,
    **context: object,
) -> HTMLResponse:
    templates = get_templates(settings)
    return templates.TemplateResponse(request, template, context)


@router.get("/register", response_class=HTMLResponse, name="register")
async def register_form(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    return _render_template(
        request,
        "auth/register.html",
        settings,
        title="Create an account",
        form={},
        errors={},
    )


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    settings: Settings = Depends(get_settings),
    api: ApiClient = Depends(get_api_client),
) -> Response:
    raw_form = {"email": email, "password": password, "confirm_password": confirm_password}
    try:
        form = RegistrationForm.model_validate(raw_form)
    except ValidationError as exc:
        errors: dict[str, str] = {}
        for err in exc.errors():
            loc = err.get("loc", [])
            key = loc[0] if loc else "__all__"
            if key in {"__root__"}:
                key = "__all__"
            errors[key] = err.get("msg", "Invalid value")
        return _render_template(
            request,
            "auth/register.html",
            settings,
            title="Create an account",
            form=raw_form,
            errors=errors,
        )

    try:
        create_response = await api.create_user(form.email, form.password)
        activation_token = create_response.get("activation_token")
        if activation_token:
            await api.activate_user(activation_token)
        auth_response = await api.authenticate(form.email, form.password)
    except ApiConnectionError:
        errors = {"__all__": "Unable to reach the service API. Please try again."}
        return _render_template(
            request,
            "auth/register.html",
            settings,
            title="Create an account",
            form=raw_form,
            errors=errors,
        )
    except ApiClientError as exc:
        detail = exc.args[0]
        errors = {"__all__": detail}
        return _render_template(
            request,
            "auth/register.html",
            settings,
            title="Create an account",
            form=raw_form,
            errors=errors,
        )

    _store_session(request, auth_response)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse, name="login")
async def login_form(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    return _render_template(
        request,
        "auth/login.html",
        settings,
        title="Sign in",
        form={},
        errors={},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    settings: Settings = Depends(get_settings),
    api: ApiClient = Depends(get_api_client),
) -> Response:
    raw_form = {"email": email, "password": password}
    try:
        form = LoginForm.model_validate(raw_form)
    except ValidationError as exc:
        errors: dict[str, str] = {}
        for err in exc.errors():
            loc = err.get("loc", [])
            key = loc[0] if loc else "__all__"
            if key in {"__root__"}:
                key = "__all__"
            errors[key] = err.get("msg", "Invalid value")
        return _render_template(
            request,
            "auth/login.html",
            settings,
            title="Sign in",
            form=raw_form,
            errors=errors,
        )

    try:
        auth_response = await api.authenticate(form.email, form.password)
    except ApiConnectionError:
        errors = {"__all__": "Unable to reach the service API. Please try again."}
        return _render_template(
            request,
            "auth/login.html",
            settings,
            title="Sign in",
            form=raw_form,
            errors=errors,
        )
    except ApiClientError as exc:
        errors = {"__all__": exc.args[0]}
        return _render_template(
            request,
            "auth/login.html",
            settings,
            title="Sign in",
            form=raw_form,
            errors=errors,
        )

    _store_session(request, auth_response)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.pop("user", None)
    return RedirectResponse(url="/home", status_code=status.HTTP_303_SEE_OTHER)


def _store_session(request: Request, auth_response: dict) -> None:
    request.session["user"] = {
        "id": auth_response.get("userId"),
        "username": auth_response.get("username"),
        "token": auth_response.get("token"),
        "expiresAt": auth_response.get("expiresAt"),
    }


__all__ = ["router"]
