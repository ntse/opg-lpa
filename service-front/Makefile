.PHONY: install test serve fmt lint

install:
	uv pip install -e .[dev]

test:
	uv run pytest

serve:
	uv run uvicorn app.main:app --reload

lint:
	uv run ruff check app tests

fmt:
	uv run ruff format app tests
