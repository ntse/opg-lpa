from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import ROUTERS


def create_app() -> FastAPI:
    app = FastAPI(title="OPG LPA Service API", version="2.0.0")

    for router in ROUTERS:
        app.include_router(router)

    return app


app = create_app()


__all__ = ["app", "create_app"]
