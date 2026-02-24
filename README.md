# mnsAI

Document extraction platform with a FastAPI backend, Next.js frontend, and OCR/LLM-based processing pipelines.

## What is in this repository

- `backend/` – FastAPI API, SQLModel + Alembic migrations, OCR/extraction services (Google Document AI, OpenAI).
- `frontend/` – Next.js 15 (App Router) + React 18 + TypeScript app (shadcn/ui, Tailwind CSS, TanStack Query).
- `scripts/` – top-level helper scripts for build, test, deploy, and OpenAPI client generation.
- `docker-compose*.yml` – containerized local/prod-style environments.

## Stack

| Layer | Technologies |
|-------|-------------|
| Backend | FastAPI, SQLModel, Alembic, PostgreSQL, Pydantic Settings, Sentry |
| Integrations | OpenAI (`gpt-4o`), Google Document AI |
| Frontend | Next.js 15 (App Router, standalone output), React 18, TypeScript, Tailwind CSS, shadcn/ui (Radix primitives) |
| Data fetching | TanStack Query, Axios, auto-generated OpenAPI client (`@hey-api/openapi-ts`) |
| Auth | Cookie-based (`access_token`), Next.js middleware route guard, server-side API routes (`/api/auth/*`) |
| Tooling | Docker Compose, Traefik (local proxy), Playwright (E2E), Biome (lint/format), Ruff/Mypy/Pytest (backend) |

## Prerequisites

- Docker + Docker Compose
- For local frontend development (optional): Node.js 20+ (via `fnm` or `nvm`)

## Environment configuration

The backend loads variables from a top-level `.env` file. The frontend uses `NEXT_PUBLIC_API_URL` (compile-time) for API calls.

Create your env file from the example:

```bash
cp .env.example .env
```

Minimum variables to run the stack:

```env
PROJECT_NAME=mnsAI
ENVIRONMENT=local

SECRET_KEY=replace-with-a-random-secret
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=replace-with-a-strong-password

FRONTEND_HOST=http://localhost:3000
BACKEND_CORS_ORIGINS=http://localhost,http://localhost:3000

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

DOCKER_IMAGE_BACKEND=backend
DOCKER_IMAGE_FRONTEND=frontend

OPENAI_API_KEY=replace-with-openai-api-key
```

`DOMAIN` should match the host where the backend is reachable (for local development, keep `DOMAIN=localhost`).

> Note: this repo's default compose files do **not** define a Postgres container. Point `POSTGRES_*` to an existing database.

> Note: both `docker-compose.yml` and `docker-compose.override.yml` run `backend/scripts/prestart.sh` before starting FastAPI, so migrations/initial seed are applied on backend startup.

## Repo hygiene

- Never commit secrets (OAuth refresh tokens, API keys, passwords) to the repository.
- Keep runtime/build output out of git history (especially `frontend/.next/`).
- If `frontend/.next/` was accidentally tracked, untrack it with:

```bash
git rm -r --cached frontend/.next
git commit -m "Stop tracking frontend build artifacts"
```

## Quick start (Docker)

From the repository root:

```bash
docker compose build
docker compose up -d
```

Services:

| Service | URL |
|---------|-----|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| OpenAPI docs | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/api/v1/utils/health-check/` |
| Mailcatcher UI (local) | `http://localhost:1080` |

To stop:

```bash
docker compose down
```

## Local development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Next.js dev server runs at `http://localhost:3000`. API calls are routed to the backend via `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

#### Project structure (App Router)

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout (Providers wrapper)
│   ├── page.tsx            # Redirects to /dashboard
│   ├── (protected)/        # Auth-guarded pages (dashboard, items, extractor, admin, settings)
│   ├── (public)/           # Login, signup, password recovery
│   └── api/auth/           # Server-side auth route handlers (login, logout, me)
├── components/
│   ├── ui/                 # shadcn/ui primitives
│   └── ...                 # Feature components (admin, items, file-upload, etc.)
├── hooks/                  # useAuth, useToast
├── lib/                    # openapi-config, utils
├── src/client/             # Auto-generated OpenAPI client
├── middleware.ts            # Route protection (cookie-based)
└── tests/                  # Playwright E2E specs
```

### Backend

Backend source is under `backend/app`. Container startup pre-run steps are in `backend/scripts/prestart.sh` (wait/check DB, run migrations, seed initial data).

## Testing

Top-level integration flow (spins up Docker stack, runs backend tests, tears down):

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

A Playwright Docker service is also available via `docker-compose.override.yml`.

## Generated frontend API client

Regenerate the typed frontend client from the backend OpenAPI schema:

```bash
./scripts/generate-client.sh
```

This extracts the OpenAPI JSON from the backend, runs `@hey-api/openapi-ts`, and formats the output with Biome. Generated files are in `frontend/src/client/`.

## Common scripts

| Script | Purpose |
|--------|---------|
| `./scripts/build.sh` | Build Docker images |
| `./scripts/build-push.sh` | Build and push Docker images |
| `./scripts/deploy.sh` | Deployment helper |
| `./scripts/test.sh` | Full Docker-based test workflow |
| `./scripts/test-local.sh` | Local Docker test workflow |
| `./scripts/generate-client.sh` | Regenerate frontend API client |