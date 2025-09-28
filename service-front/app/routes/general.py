"""General purpose routes that make up the public front-end."""
from collections import defaultdict
import logging
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator

from ..config import Settings, get_settings
from ..services.content import ContentService, GuidancePage, get_content_service

router = APIRouter(tags=["general"])
logger = logging.getLogger(__name__)


def get_templates(settings: Settings) -> Jinja2Templates:
    return Jinja2Templates(directory=str(settings.template_path))


def resolve_content_service(settings: Settings) -> ContentService:
    return get_content_service(settings.content_path)


def _render_template(
    template_name: str,
    request: Request,
    settings: Settings,
    **extra_context: object,
) -> HTMLResponse:
    templates = get_templates(settings)
    context = dict(extra_context)
    return templates.TemplateResponse(request, template_name, context)


class FeedbackSubmission(BaseModel):
    """Simple validation model for capturing user feedback."""

    name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    message: str = Field(min_length=10, max_length=2000)
    consent: bool = False

    @field_validator("name", mode="before")
    @classmethod
    def _clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("message", mode="before")
    @classmethod
    def _clean_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


@router.get("/", response_class=RedirectResponse, include_in_schema=False)
def index() -> RedirectResponse:
    """Mirror the legacy behaviour of redirecting `/` to `/home`."""

    return RedirectResponse(url="/home", status_code=307)


@router.get("/home", response_class=HTMLResponse)
def home(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return _render_template(
        "general/home.html", request, settings, title="Make a lasting power of attorney"
    )


@router.get("/terms", response_class=HTMLResponse)
def terms(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return _render_template("general/terms.html", request, settings, title="Terms of use")


@router.get("/accessibility", response_class=HTMLResponse)
def accessibility(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return _render_template("general/accessibility.html", request, settings, title="Accessibility")


@router.get("/privacy-notice", response_class=HTMLResponse)
def privacy(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return _render_template("general/privacy.html", request, settings, title="Privacy notice")


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return _render_template("general/contact.html", request, settings, title="Contact")


@router.get("/cookies", response_class=HTMLResponse)
def cookies(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return _render_template("general/cookies.html", request, settings, title="Cookies")


@router.get("/send-feedback", response_class=HTMLResponse)
def feedback_form(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return _render_template(
        "general/feedback.html",
        request,
        settings,
        title="Send feedback",
        form={},
        errors={},
    )


@router.post("/send-feedback")
def submit_feedback(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str | None = Form(default=None),
    email: str | None = Form(default=None),
    message: str = Form(...),
    consent: bool = Form(default=False),
    settings: Settings = Depends(get_settings),
):
    form_data = {"name": name, "email": email, "message": message, "consent": consent}

    try:
        submission = FeedbackSubmission.model_validate(form_data)
    except ValidationError as exc:  # pragma: no cover - exercised in tests
        errors = {error["loc"][0]: error["msg"] for error in exc.errors()}
        return _render_template(
            "general/feedback.html",
            request,
            settings,
            title="Send feedback",
            form=form_data,
            errors=errors,
        )

    background_tasks.add_task(
        logger.info,
        "Feedback submitted",
        extra={
            "name": submission.name,
            "email": submission.email,
            "consent": submission.consent,
        },
    )

    return RedirectResponse(url="/feedback-thanks", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/feedback-thanks", response_class=HTMLResponse)
def feedback_thanks(
    request: Request, settings: Settings = Depends(get_settings)
) -> HTMLResponse:
    return _render_template(
        "general/feedback_thanks.html", request, settings, title="Thank you for your feedback"
    )


@router.get("/guide", response_class=HTMLResponse)
def guidance_index(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    """List all available guidance topics grouped by category."""

    content_service = resolve_content_service(settings)

    grouped: Dict[str, List[GuidancePage]] = defaultdict(list)
    for page in content_service.iter_guidance_pages():
        grouped[page.category].append(page)

    for pages in grouped.values():
        pages.sort(key=lambda page: page.title)

    categories = sorted(grouped.items(), key=lambda item: item[0])

    return _render_template(
        "general/guidance_index.html",
        request,
        settings,
        title="Guidance",
        categories=categories,
    )


@router.get("/guide/{slug}", response_class=HTMLResponse)
def guidance_page(
    request: Request,
    slug: str,
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    """Render an individual guidance page by slug."""

    content_service = resolve_content_service(settings)
    page = content_service.get_guidance_page(slug)

    if page is None:
        raise HTTPException(status_code=404, detail="Guidance page not found")

    return _render_template(
        "general/guidance_page.html",
        request,
        settings,
        title=page.title,
        page=page,
    )
