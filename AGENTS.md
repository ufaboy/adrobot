# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository.

## Project overview

This repository contains a take-home test assignment: a wrapper around the
**Keitaro** ad tracker (Admin API). Keitaro is a link builder that redirects incoming
visitors according to configured rules ("streams"/flows) and reports on redirects.

The app has two parts:

1. **Campaign creator** — creates a Keitaro campaign with two streams from a name,
   a list of countries, and an offer.
2. **Campaign editor** — adds/removes offers in an existing campaign's streams,
   keeps offer weights correct, and publishes changes back to Keitaro.

Submission: a GitHub link with a clear README covering migrations and running the app.

## Functional requirements

### 1. Campaign creator (`/campaigns/new`)

- **Form fields:**
  - `name` — campaign name (uniqueness is not enforced; Keitaro allows duplicates).
  - `geo` — one or more ISO 3166-1 alpha-2 country codes (multi-select, at least one).
  - `offer` — a single offer, picked via autocomplete (search by id or name).
  - `domain`, `group`, `traffic source` — dropdowns loaded from Keitaro, with defaults from env.
- **Created in Keitaro:**
  - Campaign: `type: position`, cost model CPC, cost 0 USD.
  - Stream 1: `type: regular`, position 1, filter `country` / mode `accept` / payload = geo list,
    `action_type: http`, redirect to `GOOGLE_URL` (env, default `https://google.com`).
  - Stream 2: `type: regular`, position 2, no filters, `schema: landings` without landings,
    `offers: [{offer_id, share: 100, state: active}]`.
- **Failure handling:** creation spans several API calls. If any step fails, delete the
  already-created campaign in Keitaro (compensating action) and return an error.
- On success the campaign is stored locally and the user is redirected to its editor.

### 2. Campaign editor (`/` and `/campaigns/:id`, where `id` is the Keitaro campaign id)

- `/` lists campaigns fetched from Keitaro, plus a "New campaign" button.
- The editor works on a **local snapshot** of the campaign's streams stored in our DB.

**Fetch streams from KT** — creates/refreshes the local snapshot:
- Streams without offers (e.g. the Google redirect stream) are stored and shown as plain,
  **read-only** streams. Their content (filters, actions) is not parsed or displayed.
- Offer present locally but missing in Keitaro → marked `removed` (as if removed in the UI).
- Offer present in Keitaro but missing locally → added as `active`.
- Shares are taken from Keitaro; local pins are preserved.
- If the stream has unpublished changes, fetching discards them after user confirmation.

**Editing an offer stream** (a stream with at least one offer, in Keitaro or locally):
- **Add offer** — autocomplete over the local offer catalog. Only offers with
  `state: active` are suggested. An offer already active in the stream cannot be added;
  if it is in the stream as `removed`, the UI offers **Bring back** instead.
- **Remove** — the offer turns grey, its share becomes 0%, and it stays in the stream's
  archive with state `removed`.
- **Bring back** — returns a removed offer to `active`.
- **Pin** — editing a share manually pins it; a toggle unpins it.
- Any change marks the stream as **dirty** (highlighted yellow = unpublished).
- **Push** (per stream) — sends the stream's `active` offers with their shares to Keitaro.
  Removed offers are not sent. After success the stream is clean (white).
- **Cancel** (per stream) — reverts all unpublished changes (adds, removes, bring-backs,
  pins, shares) to the last state synced with Keitaro.

**Weight rules** (shares are integers, percent):
- Pinned shares never change on recalculation.
- The remainder `100 − Σ pinned` is split evenly among unpinned active offers using the
  **largest remainder method**; leftover units go to the first offers by position.
  The total is always exactly 100 (e.g. 3 offers → 34/33/33).
- Recalculation runs on every add / remove / bring back / pin change.
- Removed offers have share 0 and lose their pin.
- Validation: Σ pinned > 100 is rejected. If all active offers are pinned and the sum ≠ 100,
  Push is blocked with a clear message.

### Out of scope

- **Statistics** — the Keitaro emulator exposes no report endpoints (mention in README).
- **Authentication** — internal tool; the Keitaro API key lives only on the backend.
- **Concurrent editing** — single user, last write wins (mention in README).

## Keitaro integration

- **Target:** a Keitaro **emulator** (FastAPI) at `KEITARO_API_URL`
  (`https://keitaro-for-tests.etolegko.com/admin_api`). Its OpenAPI schema is at
  `https://keitaro-for-tests.etolegko.com/openapi.json` and is the source of truth for
  available endpoints. Request bodies are free-form JSON — follow real Keitaro Admin API v1 formats.
- **Auth:** `Api-Key: <KEITARO_API_KEY>` header. The key is set only in `backend/.env`;
  never commit it, log it, or send it to the frontend.
- **Available endpoints (v1):** CRUD for `campaigns` and `streams`
  (`GET /campaigns/{id}/streams`), read-only `offers`, `groups?type=campaigns`,
  `domains`, `traffic_sources`. No search/pagination on `offers` (~170 items), no reports.
- **The reviewer sees a journal of every API call made with our key.** Keep traffic lean:
  no calls per keystroke, cache reference data, no polling.
- **Offer catalog:** mirrored into the local `offers` table; synced on startup and when
  older than 10 minutes, plus a manual "Refresh offers" action. Autocomplete and offer
  names in the editor read from this table.
- **Single client:** all Keitaro calls go through one async client module
  (`app/integrations/keitaro/`) behind an interface. Services never use `httpx` directly.
- **Tests never call the real emulator.** Use a fake client or `respx`.
- **Manual testing against the emulator:** test campaigns must be named with the prefix
  `dev-test-` and deleted after verification. Do not modify campaigns you did not create
  (e.g. `test_kashapov_campaign1`).

## Language policy

- **All code, comments, docstrings, commit messages, and documentation must be written in English.**
- This applies regardless of the language used in conversation with the developer.
  The developer may communicate in Russian or other languages; agents reply in that
  language in chat, but everything committed to the repository stays in English.

## Tech stack

### Backend

- **Python 3.13** — pinned everywhere: `backend/.python-version`, the Docker image, and CI.
- **FastAPI** — HTTP API framework, async endpoints.
- **SQLAlchemy 2.x, async** — `AsyncSession` + `asyncpg`, 2.0-style API
  (`select()`, `Mapped[]`, `mapped_column()`).
- **Alembic** — database migrations, using the async template.
- **Pydantic v2** — request/response schemas and settings (`pydantic-settings`).
- **PostgreSQL** — used for development, tests, and Docker. No SQLite.
- **Testing:** `pytest` + `pytest-asyncio` + `httpx.AsyncClient`.
- **Tooling:** `uv` for dependencies, `ruff` for linting/formatting, `mypy` for type checking.

### Frontend

- **React SPA built with Vite**, **TypeScript** in strict mode. The build output is
  static files served by nginx in Docker (with SPA fallback to `index.html`).
- **pnpm** as the package manager; the version is pinned via the `packageManager`
  field in `package.json` (enable with `corepack enable`).
- **React Router v8** (declarative mode). Routes: `/` (campaign list),
  `/campaigns/new` (creator), `/campaigns/:id` (editor).
- **TanStack Query** for server state; invalidate affected queries after mutations.
- **Tailwind CSS + shadcn/ui** — components are copied into `src/components/ui/`.
  Offer autocomplete and country multi-select are built on shadcn's `Command`.
- **Forms:** react-hook-form + zod.
- **Linting:** `tsc -b` (TypeScript 7) + **oxlint** with react / react-hooks / typescript
  rules (`.oxlintrc.json`, warnings fail the build). No Prettier. ESLint is not used:
  typescript-eslint does not support the TypeScript 7 native compiler, and oxlint is the
  Vite template default.
- **Scripts:** `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build`.
- **Testing:** Vitest + Testing Library.
- UI text is in English.
- The frontend talks to the backend only through the public HTTP API.

## Development environment

- **Primary workflow: native on the host (Windows).** `uv` and `pnpm` run on the host;
  only PostgreSQL runs in Docker (`make dev-db`).
- **Full stack in Docker:** `docker compose up` starts `db`, `backend`, and `frontend`,
  each service with its own Dockerfile. This is the reproducible Linux environment.
- **Dev container (optional):** `.devcontainer/` reuses the root `docker-compose.yml`
  and adds a `workspace` service with Python 3.13, uv, Node 24, pnpm, and make.
  It reuses the same `db` service. It is a convenience, not a requirement.
- **Before publishing / sending to the reviewer:** always do a final manual check
  that the full stack builds and runs via `docker compose up`.

### Ports

| Service  | Port |
|----------|------|
| Postgres | 5432 |
| Backend  | 8000 |
| Frontend | 5173 (Vite dev server and nginx in Docker) |

## Cross-platform rules

Development happens on Windows, but the code must run unchanged on Linux/macOS and in containers.

- Use `pathlib.Path` for all filesystem paths. Never hardcode `\` or `/` separators
  in path strings, and never hardcode absolute paths.
- Line endings are normalized to LF via `.gitattributes` (`* text=auto eol=lf`).
  Shell scripts used in containers must have LF endings.
- No OS-specific commands in code, scripts, or Makefile recipes.
- CI on `ubuntu-latest` is the source of truth for "it works".

## Makefile

`make` is the task runner. Recipes must run identically under `cmd.exe` (Windows)
and `sh` (Linux/macOS/CI):

- Recipes only invoke cross-platform tools: `uv run …`, `pnpm --dir frontend …`,
  `docker compose …`.
- No `rm`, `cp`, `mkdir -p`, `export`, inline `VAR=value cmd`, `cd … &&` chains,
  or other shell-specific syntax. Use tool flags (`--directory`, `--dir`) or
  `uv run python -c …` instead.
- The README duplicates every command in raw form for people without `make`.

Targets:

| Target         | Purpose                                         |
|----------------|-------------------------------------------------|
| `install`      | Install backend and frontend dependencies       |
| `dev-db`       | Start only Postgres in Docker                   |
| `dev-backend`  | Run the FastAPI dev server with reload          |
| `dev-frontend` | Run the Vite dev server                         |
| `migrate`      | Apply Alembic migrations (`alembic upgrade head`) |
| `test`         | Run backend and frontend tests                  |
| `test-backend` | Run backend tests (pytest)                      |
| `test-frontend`| Run frontend tests (Vitest)                     |
| `lint`         | ruff check + ruff format --check + mypy + tsc -b + oxlint |
| `format`       | Auto-format backend code                        |
| `up`           | `docker compose up --build` (full stack)        |
| `down`         | `docker compose down`                           |

## Configuration

- Each part is self-contained with its own env example:
  `backend/.env.example` and `frontend/.env.example`. Real `.env` files are never committed.
- Backend settings are loaded via `pydantic-settings`; no secrets in code.
  Keitaro-related settings: `KEITARO_API_URL`, `KEITARO_API_KEY`, `GOOGLE_URL`,
  `DEFAULT_DOMAIN_ID`, `DEFAULT_GROUP_ID`, `DEFAULT_TRAFFIC_SOURCE_ID`,
  `OFFERS_CACHE_TTL_MINUTES`.
- `docker-compose.yml` overrides values for containers explicitly via `environment:`
  (e.g. the database host is `db` inside Docker and `localhost` on the host).
- Frontend calls the API directly at `VITE_API_URL` (default `http://localhost:8000`).
  The value is baked in at build time; in Docker it is passed as a build arg.
- The backend enables CORS with allowed origins from the `CORS_ORIGINS` env variable
  (default `http://localhost:5173`).

## Repository layout (target)

```
.
├── AGENTS.md
├── README.md
├── Makefile
├── .gitattributes
├── docker-compose.yml        # db, backend, frontend
├── .devcontainer/            # optional dev container (workspace service)
├── .github/workflows/ci.yml
├── docker/
│   └── postgres-init/        # creates the app_test database
├── backend/
│   ├── Dockerfile
│   ├── .env.example
│   ├── .python-version
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/              # migrations
│   ├── app/
│   │   ├── main.py           # FastAPI app factory / entrypoint
│   │   ├── core/             # config, logging, security
│   │   ├── db/               # async engine, session, base model
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── repositories/     # data-access layer
│   │   ├── services/         # business logic (incl. weight calculation)
│   │   ├── integrations/
│   │   │   └── keitaro/      # async Keitaro Admin API client
│   │   └── api/              # routers (versioned, e.g. /api/v1)
│   └── tests/
└── frontend/
    ├── Dockerfile
    ├── .env.example
    ├── nginx.conf            # static serving + SPA fallback
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx          # entry: router + QueryClientProvider
        ├── routes/           # page components (list, creator, editor)
        ├── components/       # feature components
        │   └── ui/           # shadcn/ui components
        ├── hooks/            # TanStack Query hooks
        └── lib/              # typed API client, shared utilities
```

## Backend conventions

- Layering: **router → service → repository → model**. Routers stay thin; business
  logic lives in services; database access lives in repositories.
- Use FastAPI dependency injection for DB sessions and shared dependencies.
- Async SQLAlchemy: never rely on lazy loading — load relationships explicitly
  (`selectinload`, `joinedload`). Set `expire_on_commit=False` on the session factory.
- Never return ORM objects directly from endpoints — always use Pydantic response models.
- Every schema change goes through an Alembic migration; never rely on `create_all()`
  outside tests.
- The backend container runs `alembic upgrade head` on startup, then starts `uvicorn`.
  Locally, migrations are applied with `make migrate`.
- Full type hints everywhere; code must pass `ruff check`, `ruff format --check`, and `mypy`.
- Consistent error responses via FastAPI exception handlers.
- API is versioned under `/api/v1` and documented via the auto-generated OpenAPI schema.
- Expose a `GET /health` endpoint for Docker healthchecks.

## Frontend conventions

- TypeScript strict mode; no `any` without a justification comment.
- A single typed API client module in `src/lib/` — components do not call `fetch` directly;
  they use TanStack Query hooks from `src/hooks/` built on that client.
- **No business logic on the frontend.** Weights are calculated only on the backend:
  every editor action (add, remove, bring back, pin, share edit) is an API call that
  persists the draft in the DB and returns the recalculated stream, which the UI renders.
- Keep components small and focused.
- Code must pass `pnpm typecheck`, `pnpm lint`, `pnpm test`, and `pnpm build`.
- Frontend tests: a few (3–5) Vitest + Testing Library tests for key UI behavior
  (dirty-stream highlighting, Push blocked state, Bring back instead of Add).

## Testing

- Tests run against a real PostgreSQL database `app_test`, created in the same Postgres
  container by an init script in `docker/postgres-init/`.
- Each test runs inside a transaction that is rolled back afterwards.
- Backend: unit tests for services, integration tests for API endpoints.
- The weight calculation and the sync rules (fetch / push / cancel) are pure logic and
  must have thorough unit tests, including the edge cases listed in "Weight rules".
- New features and bug fixes come with tests.
- All tests must pass before a change is considered done.

## CI

GitHub Actions (`.github/workflows/ci.yml`) on `ubuntu-latest`, on every push and PR:

- Backend: `ruff check`, `ruff format --check`, `mypy`, `pytest` against a Postgres service container.
- Frontend: `pnpm install --frozen-lockfile`, `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build`.

## Git

- Hosted on GitHub as a private repository; access is opened to the reviewer when submitting.
- Work happens directly on `main` in small, focused commits.
- Commit messages in English, imperative mood (e.g. `Add user listing endpoint`).
- No pre-commit hooks — run `make lint` and `make test` before committing; CI enforces the rest.
- Do not commit secrets, `.env` files, virtual environments, `node_modules`, or build artifacts.
- Agents never create remote repositories, push, or change repository visibility
  without an explicit instruction from the developer.

## Definition of done

1. Code follows the conventions above and is written in English.
2. `make lint` and `make test` pass locally, and CI is green.
3. The full stack builds and runs via `docker compose up`.
4. `README.md` explains how to set up, run, and test the project — both via Docker
   and natively, with raw commands alongside `make` targets.
