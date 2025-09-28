"""Application factory for the FastAPI front-end service."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .routes import applications, auth, general, health


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    import mimetypes

    mimetypes.add_type("font/woff", ".woff")
    mimetypes.add_type("font/woff2", ".woff2")

    app = FastAPI(title="OPG LPA Front", version="0.1.0")

    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)

    # Simple CORS configuration to allow other internal services (e.g. admin UI)
    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(applications.router)
    app.include_router(general.router)

    # Serve compiled static assets from the legacy public directory
    static_files = StaticFiles(directory=str(settings.static_path), html=False)

    app.mount(settings.static_url, static_files, name="static")
    if settings.static_url != "/assets":
        app.mount("/assets", static_files, name="legacy-assets")

    return app


__all__ = ["create_app"]
