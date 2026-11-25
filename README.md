# Adrobot — Keitaro wrapper

A take-home assignment: a small web app on top of the [Keitaro](https://keitaro.io) ad tracker
Admin API.

- **Campaign creator:** builds a Keitaro campaign with two streams from a name, a list of
  countries, and an offer. Stream 1 redirects visitors from the given countries to Google,
  stream 2 sends everyone else to the offer.
- **Campaign editor:** adds and removes offers in a campaign's streams, keeps offer weights
  correct (with pinning), and pushes changes back to Keitaro.

> **Status:** project scaffold. The features above are in progress.

## Tech stack

| Part     | Stack                                                                             |
|----------|-----------------------------------------------------------------------------------|
| Backend  | Python 3.13, FastAPI, async SQLAlchemy 2 + asyncpg, Alembic, Pydantic v2, uv      |
| Frontend | React + TypeScript (Vite), React Router, TanStack Query, Tailwind CSS, shadcn/ui |
| Database | PostgreSQL 17                                                                     |
| Tooling  | ruff, mypy, pytest · oxlint, Vitest · Docker Compose · GitHub Actions            |

## Quick start (Docker)

Requires Docker with Compose v2.

1. Create the backend config and set your Keitaro API key:

   ```bash
   cp backend/.env.example backend/.env
   # edit backend/.env: KEITARO_API_KEY=..., DEFAULT_*_ID=...
   ```

2. Start everything:

   ```bash
   docker compose up --build      # or: make up
   ```

3. Open:
   - Frontend: <http://localhost:5173>
   - API docs (OpenAPI): <http://localhost:8000/docs>

The backend container applies database migrations automatically on startup.

## Local development

Requirements: Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 24, pnpm
(`corepack enable`), Docker (for Postgres). `make` is optional — every target is listed
with its raw command below.

```bash
cp backend/.env.example backend/.env    # then fill in KEITARO_API_KEY etc.
cp frontend/.env.example frontend/.env  # optional, defaults work
```

| Step                    | make                | Raw command                                                           |
|-------------------------|---------------------|-----------------------------------------------------------------------|
| Install dependencies    | `make install`      | `uv sync --directory backend` and `pnpm --dir frontend install`       |
| Start Postgres          | `make dev-db`       | `docker compose up -d db`                                             |
| Apply migrations        | `make migrate`      | `uv run --directory backend alembic upgrade head`                     |
| Run the API (reload)    | `make dev-backend`  | `uv run --directory backend uvicorn app.main:app --reload --port 8000` |
| Run the frontend        | `make dev-frontend` | `pnpm --dir frontend dev`                                             |

The frontend runs on <http://localhost:5173> and calls the API at `VITE_API_URL`
(default `http://localhost:8000`).

### Dev container (optional)

`.devcontainer/` provides a ready environment (Python 3.13, uv, Node 24, pnpm, make) that
reuses the `db` service from `docker-compose.yml`. Open the repository in VS Code and run
**Dev Containers: Reopen in Container**.

## Tests and checks

Tests run against a real PostgreSQL database `app_test`, created automatically by
`docker/postgres-init/` on the first start of the `db` container. Each test runs inside a
transaction that is rolled back. Tests never call the real Keitaro API.

| Check                 | make                 | Raw command                                                                 |
|-----------------------|----------------------|-----------------------------------------------------------------------------|
| All tests             | `make test`          | both commands below                                                         |
| Backend tests         | `make test-backend`  | `uv run --directory backend pytest`                                         |
| Frontend tests        | `make test-frontend` | `pnpm --dir frontend test`                                                  |
| Lint and type checks  | `make lint`          | `ruff check`, `ruff format --check`, `mypy` (backend); `pnpm typecheck`, `pnpm lint` (frontend) |
| Auto-format backend   | `make format`        | `uv run --directory backend ruff format .`                                  |

CI (GitHub Actions) runs the same checks on every push.

## Configuration

Backend (`backend/.env`, see `backend/.env.example`):

| Variable                     | Description                                         |
|------------------------------|-----------------------------------------------------|
| `DATABASE_URL`               | Async SQLAlchemy URL of the app database            |
| `TEST_DATABASE_URL`          | Database used by the test suite                     |
| `CORS_ORIGINS`               | JSON list of allowed browser origins                |
| `KEITARO_API_URL`            | Keitaro Admin API base URL                          |
| `KEITARO_API_KEY`            | Keitaro API key (never committed)                   |
| `GOOGLE_URL`                 | Redirect target of the country stream               |
| `DEFAULT_DOMAIN_ID`          | Default domain in the campaign creator              |
| `DEFAULT_GROUP_ID`           | Default campaign group                              |
| `DEFAULT_TRAFFIC_SOURCE_ID`  | Default traffic source                              |
| `OFFERS_CACHE_TTL_MINUTES`   | Freshness of the local offer catalog                |

Frontend (`frontend/.env`): `VITE_API_URL` — backend base URL, baked in at build time.

## Limitations

- No statistics: the Keitaro instance used for this assignment exposes no report endpoints.
- No authentication: an internal tool; the Keitaro API key stays on the backend.
- Single user: concurrent edits of the same stream are not coordinated (last write wins).
