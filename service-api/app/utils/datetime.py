from __future__ import annotations

from datetime import datetime, timezone


def format_lpa_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")


__all__ = ["format_lpa_datetime"]
