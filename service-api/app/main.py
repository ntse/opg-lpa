from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import ROUTERS
from app.core.database import database
from app.models import Base


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with database.engine.begin() as connection:  # pragma: no cover - exercised in integration
        await connection.run_sync(Base.metadata.create_all)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="OPG LPA Service API", version="2.0.0", lifespan=lifespan)

    for router in ROUTERS:
        app.include_router(router)

    return app


app = create_app()


__all__ = ["app", "create_app"]
