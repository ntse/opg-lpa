# Lasting Power of Attorney API Service (FastAPI)

This service now runs on Python 3.13 with [FastAPI](https://fastapi.tiangolo.com/). It is responsible for managing authentication flows, user management, and LPA data that is consumed by the front-end services.

## Project layout

```
service-api/
├── app/                # FastAPI application code
│   ├── api/            # Route definitions and dependencies
│   ├── config/         # Environment driven settings
│   ├── core/           # Infrastructure helpers (database, etc.)
│   ├── models/         # SQLAlchemy ORM models
│   ├── schemas/        # Pydantic request/response models
│   ├── services/       # Domain services (authentication, repositories)
│   └── utils/          # Shared helpers
├── tests/              # Pytest based unit tests
├── Makefile            # Helpers for venv, install, run, test
└── pyproject.toml      # Dependency and build metadata
```

## Requirements

- Python 3.13
- Access to the Postgres instance that backs the service (same schema as the legacy PHP implementation)
- Optional: Docker / docker-compose if you want to run the wider stack locally

## Getting started

Create a virtual environment and install dependencies (the Makefile uses [`uv`](https://github.com/astral-sh/uv) to download Python 3.13 automatically if it is not already installed):

```
cd service-api
make install  # creates .venv using python3.13 and installs dependencies + dev extras
```

> **Note:** Package installation requires access to PyPI. In restricted environments you may need to pre-populate a wheel cache or point pip at an internal mirror.

Run the API locally:

```
make run  # uvicorn app.main:app --reload --host 0.0.0.0 --port 7001
```

Run the test suite:

```
make test
```

## Configuration

Settings are sourced from environment variables (mirroring the legacy service). Key variables include:

- `OPG_LPA_DB_URL` – SQLAlchemy connection string. Defaults to `postgresql+psycopg_async://lpauser:lpapass@localhost:5432/lpadb`.
- `OPG_LPA_AUTH_TOKEN_TTL` (`SESSION_TOKEN_TTL`) – Authentication token lifetime in seconds (defaults to 4500).

See `app/config/settings.py` for the full list and defaults.

## Health & authentication endpoints

The following endpoints are currently implemented:

- `GET /ping` – Full health check (Postgres connectivity, SQS queue depth, Sirius gateway reachability).
- `GET /ping/elb` – Elastic load balancer health check placeholder.
- `POST /v2/authenticate` – Authenticate via token or username/password.
- `GET /v2/session-expiry` – Validate a token without extending it.
- `POST /v2/session-set-expiry` – Force-set the expiry window for a token.
- `POST /v2/users` – Create a user account or activate an existing one.
- `GET /v2/users/search` – Fetch a user record by email (with deletion log fallback).
- `GET /v2/users/match` – Case-insensitive user search with pagination.
- `POST /v2/users/{userId}/email` – Request an email change token (requires `Token` header).
- `POST /v2/users/email` – Redeem an email change token.
- `POST /v2/users/{userId}/password` – Change password using current credentials (requires `Token`).
- `POST /v2/users/password` – Reset password using a password token.
- `POST /v2/users/password-reset` – Request a password reset or activation token by email.
- `GET /v2/user/{userId}/applications` – List a user's applications (supports `page`, `perPage`, `search`).
- `POST /v2/user/{userId}/applications` – Create a new application for a user.
- `GET /v2/user/{userId}/applications/{lpaId}` – Retrieve a specific application.
- `PATCH /v2/user/{userId}/applications/{lpaId}` – Update application metadata/document/payment fields.
- `DELETE /v2/user/{userId}/applications/{lpaId}` – Remove an application.
- `PUT /v2/user/{userId}/applications/{lpaId}/donor` – Replace the donor block on an application.
- `POST /v2/user/{userId}/applications/{lpaId}/primary-attorneys` – Append a primary attorney.
- `PUT /v2/user/{userId}/applications/{lpaId}/primary-attorneys/{attorneyId}` – Update a primary attorney.
- `DELETE /v2/user/{userId}/applications/{lpaId}/primary-attorneys/{attorneyId}` – Delete a primary attorney.
- `POST /v2/user/{userId}/applications/{lpaId}/replacement-attorneys` – Append a replacement attorney.
- `PUT /v2/user/{userId}/applications/{lpaId}/replacement-attorneys/{attorneyId}` – Update a replacement attorney.
- `DELETE /v2/user/{userId}/applications/{lpaId}/replacement-attorneys/{attorneyId}` – Delete a replacement attorney.
- `PUT /v2/user/{userId}/applications/{lpaId}/instruction` – Update the LPA instructions block.
- `PUT /v2/user/{userId}/applications/{lpaId}/preference` – Update the LPA preferences block.
- `PUT /v2/user/{userId}/applications/{lpaId}/correspondent` – Update the correspondent details.
- `DELETE /v2/user/{userId}/applications/{lpaId}/correspondent` – Remove correspondent information.
- `PUT /v2/user/{userId}/applications/{lpaId}/repeat-case-number` – Set the repeat case number (numeric).
- `DELETE /v2/user/{userId}/applications/{lpaId}/repeat-case-number` – Clear the repeat case number.
- `POST /v2/user/{userId}/applications/{lpaId}/lock` – Lock an application (idempotent, 403 if already locked).
- `POST /v2/user/{userId}/applications/{lpaId}/notified-people` – Add a person to notify.
- `PUT /v2/user/{userId}/applications/{lpaId}/notified-people/{personId}` – Update a notified person.
- `DELETE /v2/user/{userId}/applications/{lpaId}/notified-people/{personId}` – Remove a notified person.
- `PUT /v2/user/{userId}/applications/{lpaId}/payment` – Persist payment details for an application.
- `GET /v2/user/{userId}/applications/{lpaId}/pdfs/{pdfType}` – Request PDF generation status (lp1, lp3, lpa120).
- `PUT /v2/user/{userId}/applications/{lpaId}/who-are-you` – Record the “who are you” answer (one-time).
- `PUT /v2/user/{userId}/applications/{lpaId}/who-is-registering` – Record who is registering the LPA.
- `PUT /v2/user/{userId}/applications/{lpaId}/certificate-provider` – Update certificate provider details.
- `DELETE /v2/user/{userId}/applications/{lpaId}/certificate-provider` – Remove certificate provider information.
- `PUT /v2/user/{userId}/applications/{lpaId}/type` – Set the LPA type.

Responses mirror the legacy PHP service so existing consumers continue to function.

## Next steps

- Remove the legacy PHP modules once feature parity is achieved.
- Refresh integration tests to exercise the FastAPI routes.
