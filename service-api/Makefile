UV?=/home/sam/.local/bin/uv
PYTHON_VERSION?=3.13
VENV?=.venv
PYTHON?=$(VENV)/bin/python
PIP?=$(PYTHON) -m pip
UVICORN?=$(VENV)/bin/uvicorn
PYTEST?=$(VENV)/bin/pytest

.PHONY: venv install run dev test lint clean

venv:
	$(UV) venv --seed --clear --python $(PYTHON_VERSION) $(VENV)
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -e .[dev]

run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 7001

dev: install run

test:
	$(PYTEST)

lint:
	$(VENV)/bin/ruff check app tests

clean:
	rm -rf $(VENV) .pytest_cache
