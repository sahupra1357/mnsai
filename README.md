# Extractor

Document extraction platform with a FastAPI backend, React frontend, and OCR/LLM-based processing pipelines.

## What is in this repository

- `backend/`: FastAPI API, SQLModel + Alembic migrations, OCR/extraction services.
- `frontend/`: Vite + React + TypeScript app (Chakra UI + TanStack Router/Query).
- `scripts/`: top-level helper scripts for build, test, deploy, and OpenAPI client generation.
- `docker-compose*.yml`: containerized local/prod-style environments.

## Stack

- Backend: FastAPI, SQLModel, Alembic, PostgreSQL, OpenAI + Google Document AI integrations.
- Frontend: React, TypeScript, Vite, Chakra UI.
- Tooling: Docker Compose, Playwright (E2E), Ruff/Mypy/Pytest for backend quality checks.

## Prerequisites

- Docker + Docker Compose
- For local frontend development (optional): Node.js (via `fnm` or `nvm`)

## Environment configuration

The backend loads variables from a top-level `.env` file.

Create your env file from the example:

```bash
cp .env.example .env
```

Minimum variables to run the stack:

```env
PROJECT_NAME=Extractor
ENVIRONMENT=local

SECRET_KEY=replace-with-a-random-secret
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=replace-with-a-strong-password

FRONTEND_HOST=http://localhost:5173
BACKEND_CORS_ORIGINS=["http://localhost:5173"]

POSTGRES_SERVER=host.docker.internal
POSTGRES_PORT=5432
POSTGRES_DB=extractor
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace-with-db-password

DOMAIN=localhost
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
EMAILS_FROM_EMAIL=noreply@example.com
SENTRY_DSN=
```

> Note: this repo's default compose files do **not** define a Postgres container. Point `POSTGRES_*` to an existing database.

> Note: both `docker-compose.yml` and `docker-compose.override.yml` run `backend/scripts/prestart.sh` before starting FastAPI, so migrations/initial seed are applied on backend startup.

## Quick start (Docker)

From the repository root:

```bash
docker compose build
docker compose up -d
```

Services:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/api/v1/utils/health-check/`

To stop:

```bash
docker compose down
```

## Local development

### Frontend (fast feedback loop)

```bash
cd frontend
npm install
npm run dev
```

The Vite app runs at `http://localhost:5173` and talks to backend via `VITE_API_URL`.

### Backend

Backend source is under `backend/app`. Container startup pre-run steps are in `backend/scripts/prestart.sh` (wait/check DB, run migrations, seed initial data).

## Testing

Top-level integration flow:

```bash
./scripts/test.sh
```

Local variant (keeps stack up for inspection):

```bash
./scripts/test-local.sh
```

Backend checks (inside backend container/environment):

- Lint/type checks: `backend/scripts/lint.sh`
- Tests + coverage: `backend/scripts/test.sh`

Frontend E2E (Playwright):

```bash
cd frontend
npx playwright test
```

## Generated frontend API client

Regenerate the typed frontend client from backend OpenAPI schema:

```bash
./scripts/generate-client.sh
```

Generated files are in `frontend/src/client/`.

## Common scripts

- `./scripts/build.sh`: build images.
- `./scripts/build-push.sh`: build and push images.
- `./scripts/deploy.sh`: deployment helper.
- `./scripts/test.sh`: full Docker-based test workflow.
- `./scripts/test-local.sh`: local Docker test workflow.
- `./scripts/generate-client.sh`: regenerate frontend API client.