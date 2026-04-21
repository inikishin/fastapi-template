# FastAPI + SQLAlchemy Microservice Template

Baseline template for the team's microservices: FastAPI, async SQLAlchemy + Alembic, PostgreSQL, a pytest setup backed by a real test database, and a library of Claude Code skills that keep every service consistent in its layout, migrations, authentication and external integrations.

The template assumes that most routine work (creating a model, adding an endpoint, writing tests, enabling Kafka/Redis/Taskiq/Keycloak, plugging into the Raport ecosystem) is performed by the agent through the shipped skills — the human only makes the business decisions.

## Why use it

- A fast start for a new microservice with a proper `src/` layout (router → service → manager → model).
- Shared rules for naming, typing, logging, migrations and tests — identical across every service.
- A ready-made automated test stack on top of real PostgreSQL (drop/create the test database, load dumps, paired auth test).
- A Claude Code skill library covering typical tasks: initial setup, model creation, API generation, testing, Raport integration.
- `BaseManager` and `BaseService` supply CRUD, filtering, pagination and mapping helpers — no reinventing the wheel per service.

## Layout

```
template-fastapi/
├── src/                         # every Python file
│   ├── main.py                  # FastAPI entry point
│   ├── api/v1/<feature>/        # routers and feature-specific schemas
│   ├── services/                # business logic (BaseService)
│   ├── models/                  # ORM + managers (BaseManager)
│   ├── config/                  # settings, logger, postgres
│   ├── middlewares/             # (empty by default; filled in by initial-setup)
│   ├── tasks/                   # (empty by default; Taskiq via initial-setup)
│   ├── external/                # HTTP clients for third-party services
│   └── utils/                   # helpers, shared error schemas
├── tests/                       # pytest + dump_data + conftest
├── migrations/                  # Alembic
├── claude/skills/               # → rename to .claude/skills/ before the first run
├── Makefile
├── requirements.txt             # runtime
├── requirements-dev.txt         # pytest, linters, pre-commit
└── .env.example
```

## First-time setup

### 1. Clone and handle the `claude/` directory

```bash
git clone <repo-url> my-service
cd my-service
```

**Important.** Inside the template repository the skills directory is called `claude/` (no leading dot) so that Git tracks it openly and Claude Code does not mix skills across different projects. **Before the first run** you have to rename it:

```bash
mv claude .claude
```

If the project already owns a `.claude/` directory (for example, you keep your own Claude Code settings there), copy the contents carefully instead:

```bash
mkdir -p .claude
cp -r claude/. .claude/
rm -rf claude
```

Afterwards Claude Code picks up six skills: `project-structure`, `initial-setup`, `create-model`, `generate-api-method`, `backend-testing`, `report-microservice`.

Once the skills are in place, run `/init` in Claude Code so it generates a fresh `CLAUDE.md` tailored to this particular service. The file is git-ignored by design — each clone maintains its own.

### 2. Python environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

### 3. Configuration

```bash
cp .env.example .env
# edit .env: set DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASS to real values
# the rest (PROJECT_TITLE, version, port) can be tweaked as you like
```

PostgreSQL must be running and reachable using the parameters in `.env`. For the test suite the database user needs `CREATE DATABASE` permission — pytest recreates a dedicated test database on every run.

### 4. Migrations

```bash
make upgrade          # apply every migration
```

### 5. Confirm the setup

```bash
make lint             # ruff + ruff-format + mypy
make test             # pytest with coverage
make run              # dev server, http://0.0.0.0:8000/api/openapi
```

A detailed walkthrough — including how to enable the optional services (Redis, Kafka, Taskiq, Keycloak authentication) — lives in the `initial-setup` skill.

## Using the Claude Code skills

Each skill owns a specific task. The order is always: load `project-structure` first (it defines the layering and the naming rules), then the feature-specific skill. Wrap up with `make lint` and `make test`.

| Skill | When to invoke |
|---|---|
| `project-structure` | **Always first.** Layering rules, naming, the pre-handoff checklist. |
| `initial-setup` | First-time configuration; enabling Kafka / Redis / Taskiq / Keycloak; diagnostics when the project refuses to come up. |
| `create-model` | New ORM model + manager + optional admin view (SQLAdmin) + Alembic migration. |
| `generate-api-method` | New API endpoint: Pydantic schemas → service method → router. |
| `backend-testing` | Automated tests for endpoints / services / managers. Test database seed dumps. |
| `report-microservice` | Plug the service into the Raport ecosystem: main-service HTTP client, Keycloak password-grant, curated API reference. |

A typical end-to-end feature flow:

```
project-structure → create-model → generate-api-method → backend-testing → make lint → make test
```

Inside every skill (`.claude/skills/<skill>/SKILL.md`) you'll find the step-by-step workflow, code templates, a pre-handoff checklist and common mistakes. Assets (files ready to be copied into the project) live under `assets/` next to each skill.

## Makefile commands

```bash
make run                          # local dev server (uvicorn --reload)
make lint                         # ruff + ruff-format + mypy via pre-commit
make test                         # pytest with coverage; HTML report in htmlcov/
make migrate msg="short_name"     # new Alembic revision
make upgrade                      # alembic upgrade head
make downgrade                    # alembic downgrade -1
make history                      # revision history
```

## Conventions at a glance

- **Python 3.12+**, PEP8 with a 120-character line limit (ruff + ruff-format).
- **English** in code, comments, docstrings, logs and OpenAPI strings.
- **URLs** in kebab-case (`/calendar-plans`, not `/calendar_plans`).
- **Layers do not mix:** router ↛ manager/model; service ↛ FastAPI; service ↛ `sqlalchemy` (only `AsyncSession` for typing).
- **`BaseManager`** already covers CRUD, filtering, sorting, pagination, bulk operations and full-text search — write custom methods only for non-trivial SQL.
- **`BaseService`** ships `map_obj_to_schema`, `map_nested_fields`, `map_aggregated_array_fields`, `_natural_sort_key`.
- **`@catch_all_exceptions`** decorates every endpoint; `responses=` expands `get_responses(ResponseGroup.<...>)`.
- **Tests** run against the real test database seeded from `tests/dump_data/dumps/`. Dumps stay minimal — only rows the tests actually rely on.
- **Protected endpoints** require a paired test: authorized + `@pytest.mark.no_auth_mock` → 401/403.
- **Coverage** stays at 70% or higher.

## Where to read next

- `.claude/skills/<skill>/SKILL.md` — detailed rules for each area.
- `src/api/v1/user/` + `src/services/user/info.py` + `src/models/managers/user.py` + `tests/test_api/test_user/` — a live reference path from the router all the way down to the test, usable as a generation anchor.
