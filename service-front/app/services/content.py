"""Services for loading static content from the repository."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Iterable

from markdown_it import MarkdownIt


@dataclass(frozen=True)
class GuidancePage:
    """Representation of a guidance page stored as Markdown."""

    slug: str
    title: str
    category: str
    body_html: str


class ContentService:
    """Utility to read structured content from the content directory."""

    def __init__(self, content_root: Path) -> None:
        self._content_root = content_root
        self._md = MarkdownIt()

    @property
    def guidance_dir(self) -> Path:
        return self._content_root / "guidance"

    def iter_guidance_pages(self) -> Iterable[GuidancePage]:
        """Yield all available guidance pages as :class:`GuidancePage`."""

        for path in sorted(self.guidance_dir.glob("*.md")):
            stem = path.stem
            category, title = self._split_stem(stem)
            slug = self._slugify(stem)
            with path.open("r", encoding="utf-8") as file:
                html = self._md.render(file.read())
            yield GuidancePage(slug=slug, title=title, category=category, body_html=html)

    def get_guidance_page(self, slug: str) -> GuidancePage | None:
        """Return a guidance page by slug if available."""

        for page in self.iter_guidance_pages():
            if page.slug == slug:
                return page
        return None

    @staticmethod
    def _split_stem(stem: str) -> tuple[str, str]:
        if "_" in stem:
            category, title = stem.split("_", 1)
        else:
            category, title = "General", stem
        return category.replace("-", " ").strip(), title.replace("-", " ").strip()

    @staticmethod
    def _slugify(value: str) -> str:
        parts = re.split(r"[^A-Za-z0-9]+", value.lower())
        return "-".join(part for part in parts if part)


@lru_cache
def get_content_service(content_root: Path) -> ContentService:
    return ContentService(content_root)


__all__ = ["ContentService", "GuidancePage", "get_content_service"]
