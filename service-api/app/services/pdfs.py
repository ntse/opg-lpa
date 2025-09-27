from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException
from starlette.responses import JSONResponse

from app.services.applications import ApplicationsService
from app.services.repositories import ApplicationRepository

_VALID_TYPES = {"lp1", "lp3", "lpa120"}


class PdfService:
    def __init__(self, applications: ApplicationsService, repository: ApplicationRepository) -> None:
        self.applications = applications
        self.repository = repository

    async def fetch(self, user_id: str, application_id: int, pdf_type: str) -> JSONResponse:
        # download attempt (.pdf)
        if pdf_type.endswith(".pdf"):
            raise HTTPException(status_code=404, detail="PDF downloads not available in local mock")

        if pdf_type not in _VALID_TYPES:
            raise HTTPException(status_code=404, detail="PDF type not found")

        record = await self.applications.get_record(user_id, application_id)
        metadata: Dict[str, Any] = record.metadata or {}
        pdf_state: Dict[str, Any] = metadata.get("pdfStatus", {})

        entry = pdf_state.get(pdf_type)
        if not entry:
            # first time: queue it and set status to in-queue
            entry = {
                "type": pdf_type,
                "complete": True,
                "status": "in-queue",
                "queuedAt": datetime.now(timezone.utc).isoformat(),
            }
            pdf_state[pdf_type] = entry
            metadata["pdfStatus"] = pdf_state
            await self.repository.update_application(
                application_id,
                user_id,
                metadata=metadata,
                updated_at=datetime.now(timezone.utc),
            )
        else:
            # transition to ready automatically for simplicity
            entry = dict(entry)
            entry["status"] = "ready"

        return JSONResponse(entry)


__all__ = ["PdfService"]
