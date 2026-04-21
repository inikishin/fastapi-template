---
name: project-structure
description: Canonical directory layout and architectural rules for every FastAPI + SQLAlchemy microservice built from this template. Load it before any task that adds or modifies code under src/, migrations/ or tests/. Defines the layering (router → service → manager → model), where each kind of file belongs, code/typing/naming/documentation requirements, and the mandatory make lint and make test checks every task must pass.
---

# Project Structure (FastAPI + SQLAlchemy)

## Purpose

This skill captures the **shared rules** that every microservice built from this template must follow:
- directory and file layout;
- layer separation and dependency direction;
- naming, formatting and documentation conventions;
- code, typing and error-handling requirements;
- mandatory checks before handing off a task.

The goal is a consistent codebase across services: a developer familiar with one project should instantly know where new code belongs and what to verify.

This skill is the **entry point**. Load it **before** any feature-specific skill (`create-model`, `generate-api-method`, `backend-testing`) so the agent already knows the structure and conventions.

## When to activate

- Before any creation or change of code under `src/`, `migrations/` or `tests/`.
- When choosing a name or directory for a new file.
- When the user asks "where do I put X", "how do I wire Y with Z", "what layout should I use".
- Before invoking `create-model`, `generate-api-method`, `backend-testing` — those skills assume this one is already loaded.
- After finishing any development task — to run the final checklist.

------------------------------------------------------------------------

## Layers and dependency direction

```
HTTP request
    │
    ▼
┌───────────────────────────┐
│ Router (src/api/v1/<f>/)  │  views.py, schemes.py
└───────────┬───────────────┘
            │ Depends(get_<f>_service)
            ▼
┌───────────────────────────┐
│ Service (src/services/<f>)│  business logic, composes managers
└───────────┬───────────────┘
            │ Manager(db)
            ▼
┌───────────────────────────┐
│ Manager (src/models/mgrs) │  data access — ONLY through managers
└───────────┬───────────────┘
            │ AsyncSession
            ▼
┌───────────────────────────┐
│ Model   (src/models/dbo)  │  declarative_base + mixins
└───────────────────────────┘
```

**Direction rules:**

- Dependencies flow strictly top-down. A manager does not know about services, a service does not know about routers.
- A router **never** talks to a manager or model directly — only through a service.
- A service **does not import** `sqlalchemy` (except `AsyncSession` for typing) and must not use FastAPI primitives (`Request`, `Response`, `HTTPException` — those live in the router).
- SQL queries run **only inside managers**. If a service writes `select(...)` — that's a violation.
- A manager receives `AsyncSession` in its constructor; it never creates one itself.

------------------------------------------------------------------------

## Project root

The root holds supporting artefacts only. **No Python business code lives in the root** — everything goes under `src/`.

| Item | Purpose |
| --- | --- |
| `README.md`, `CHANGELOG.md`, `setup.md`, `CLAUDE.md` | Documentation |
| `Dockerfile`, `docker-compose*.yml` | Containerisation |
| `Makefile` | Unified command set |
| `alembic.ini` | Alembic configuration |
| `migrations/` | Alembic revisions |
| `tests/` | Automated tests (see the `backend-testing` skill) |
| `scripts/` | Shell scripts for launch / deploy / maintenance |
| `requirements.txt`, `requirements-dev.txt` | Dependencies (runtime + dev) |
| `.env.example`, `.env` | Environment variables (`.env` is git-ignored) |
| `.pre-commit-config.yaml`, `ruff.toml`, `mypy.ini`, `pytest.ini` | Linter and test configs |
| `.gitignore`, `.gitlab-ci.yml`, `.gitlab/` | Git infrastructure |
| `docs/`, `templates/`, `assets/` | Additional resources as needed |

**Forbidden at root:** any `.py` file carrying business logic, entry points, or CLI commands. All of that goes into `src/`.

------------------------------------------------------------------------

## The `src/` directory

### Entry points

- `src/main.py` — the FastAPI app (`app = FastAPI(...)`, router mounting, middleware). Launched via `uvicorn src.main:app`.
- `src/worker.py` *(optional)* — background worker entry point (Taskiq / Celery).
- `src/scheduler.py` *(optional)* — task scheduler.

### Sub-packages

| Directory | Purpose | Required |
| --- | --- | --- |
| `src/api/` | HTTP layer: routes + shared schemas | Yes |
| `src/config/` | Configuration: app settings, DB/cache/queue connections, admin panel | Yes |
| `src/models/` | Data layer: ORM models and managers | Yes |
| `src/services/` | Business logic | Yes |
| `src/utils/` | Generic helpers with no domain attachment | Yes |
| `src/middlewares/` | Custom FastAPI middleware | As needed |
| `src/tasks/` | Background jobs (Taskiq / Celery) | As needed |
| `src/external/` | External-system clients (HTTP clients for third-party APIs) | As needed |

Do not create additional top-level packages without a strong reason.

------------------------------------------------------------------------

## `src/api/` — HTTP layer

### Structure

```
src/api/
├── __init__.py
├── schemes.py                  # shared schemas used across routes
└── v1/
    ├── __init__.py
    └── <feature>/
        ├── __init__.py
        ├── views.py            # APIRouter + endpoints
        └── schemes.py          # Pydantic request/response schemas for this feature
```

`v1/` is the API version. The `/api/v1` prefix is mounted once in `src/main.py`: `app.include_router(<feature>_router, prefix="/api/v1")`. The router itself carries only `prefix="/<feature>"`.

### `src/api/schemes.py` — shared schemas

Holds **only reusable** building blocks:
- `BaseResponse`, `ErrorResponse`, `Response200Schema` … `Response503Schema` — typed response bodies.
- `RESPONSE_SCHEMAS` (code → `{model, description}`) and `RESPONSE_GROUPS` (group → [codes]) — expanded into the `responses=` mapping of a decorator via `get_responses(ResponseGroup.ALL_ERRORS)` from `src/utils/helpers.py`.
- `PaginationParams`, `PaginationSchema`, `SortParams`, `OrderParams`.
- `DataResponseSchema[T]`, `ListDataResponseSchema[T]`, `NamedEntitySchema`, `IDMixinSchema` — envelope wrappers.
- Reusable FK filters (`ProjectBaseFilters`, `ConstructionObjectBaseFilters`, …) — shared query-param mixins.

**Rule for `src/api/schemes.py`:** nothing domain-specific — feature schemas belong in `src/api/v1/<feature>/schemes.py`. Only the shared building blocks every feature depends on.

### `src/api/v1/<feature>/views.py` — routers

Each module contains a single `APIRouter`:

```python
<feature>_router = APIRouter(prefix="/<feature-kebab>", tags=["<Feature>"])
```

- Router name: `<feature>_router` (snake_case).
- URL prefix is kebab-case (`/calendar-plans`).
- One `views.py` file = one router. It is mounted in `src/main.py` via `app.include_router(<feature>_router, prefix="/api/v1")`.
- The endpoint body does only three things: collect parameters, call the service, return the result. No business logic.
- The service is injected via `Depends(get_<feature>_service)` — the factory lives next to the service.

The full endpoint rules (`@catch_all_exceptions` wrapping, `get_responses(...)`, `summary` / `description`, authorization, frontend error display, pagination / sorting / filtering) live in the **`generate-api-method`** skill.

### `src/api/v1/<feature>/schemes.py` — feature schemas

Feature-specific Pydantic schemas for requests / responses / filters. Naming:

- `<Action><Entity>Request` — request body (`CreateUserRequest`, `UpdateUserRequest`).
- `<Action><Entity>Response` or `<Entity>Schema` — response body.
- `<Entity>ListResponseSchema` — list wrapper (inherits from `ListDataResponseSchema[T]` in `src/api/schemes.py`).
- `<Entity>Filters` — query parameters for filtering.

------------------------------------------------------------------------

## `src/config/` — configuration

### Structure

```
src/config/
├── __init__.py
├── settings.py                 # AppConfig (pydantic-settings) + app_config singleton
├── logger.py                   # LoggerProvider
├── postgres/
│   ├── __init__.py
│   └── db_config.py            # async_engine, async_sessionmaker, get_session
├── redis.py                    # (optional) Redis client
├── kafka/                      # (optional) Kafka producers / consumers
├── taskiq/                     # (optional) Taskiq broker / scheduler
└── admin/                      # (optional) SQLAdmin configuration (see the "Admin panel" section)
    ├── __init__.py
    ├── categories.py
    ├── config.py
    ├── custom_base.py
    └── model_admin/
        ├── __init__.py
        ├── base_admin.py
        └── <entity>.py
```

**Rules:**

- Configuration is read via `pydantic-settings` from `.env` inside `settings.py`. A new setting = a new `AppConfig` field + a matching entry in `.env.example`.
- `async_engine` and `async_sessionmaker` are created **once** in `src/config/postgres/db_config.py`. No other place should create its own engine or sessionmaker.
- The `get_session()` dependency factory is the **only** legitimate way to acquire an `AsyncSession` in endpoints.
- Log via `LoggerProvider().get_logger(__name__)` in every file that needs logging.

### Admin panel (SQLAdmin)

The admin panel is built with the [**sqladmin**](https://aminalaee.dev/sqladmin/) library. It is mounted as a separate ASGI app on top of the FastAPI `app` under `/admin` (wired up in `src/main.py`).

Layout of `src/config/admin/`:

| File / directory | Purpose |
| --- | --- |
| `categories.py` | Admin section constants (the human-readable groups in the sidebar). Example: `CATEGORY_STRUCTURE = "Project structure"`, `CATEGORY_DICTIONARIES = "Dictionaries"`. |
| `config.py` | Instantiates `Admin(app, engine, ...)` and registers every view class via `admin.add_view(<EntityAdmin>)`. The single place where all admin views are collected. |
| `custom_base.py` | (optional) A subclass of `sqladmin.Admin` for customisations (localized error messages, deletion overrides, etc.). |
| `model_admin/base_admin.py` | `BaseAdmin(ModelView)` — the common ancestor of all view classes, supplying shared defaults (permissions, date format, visibility of `created_at`/`updated_at`, …). |
| `model_admin/<entity>.py` | One file per model. A class `<Entity>Admin(BaseAdmin, model=<Entity>)` configuring `category`, `name`, `name_plural`, `icon`, `column_list`, `column_details_list`, `form_columns`, `column_searchable_list`, `column_sortable_list`. |

**Admin rules:**

- One file per model. The file name is the entity's snake_case form.
- The view class inherits **only** from `BaseAdmin`, never directly from `sqladmin.ModelView`.
- The `category` value is taken from `categories.py`. If you need a new category, add a constant there — do not hardcode the string inside a view.
- After creating a new view class you **must** register it in `config.py`: `admin.add_view(<Entity>Admin)`. Without that line the section never appears in the UI.
- Admin authentication / authorization uses sqladmin's `AuthenticationBackend`; it also lives in `src/config/admin/` (usually `auth.py` or inside `config.py`).
- Validation, cascades and other logic belong to **services**, not to admin classes. Admin classes only configure display and the form.

Detailed templates for admin views live in the `create-model` skill.

------------------------------------------------------------------------

## `src/models/` — data layer

### Structure

```
src/models/
├── __init__.py
├── dbo/
│   ├── __init__.py
│   ├── models.py               # Base = declarative_base() + ORM classes (compact mode)
│   ├── mixins.py               # IDMixin, TimestampMixin, SortOrderMixin
│   ├── tables/                 # (optional) models grouped by domain: project_structure.py, calls.py, …
│   ├── views/                  # (optional) ORM classes for SQL views
│   └── database_models.py      # (optional) public re-export of every model, once there are many
└── managers/
    ├── __init__.py             # re-exports every manager
    ├── common.py               # BaseManager (generic CRUD + filtering + sorting + pagination)
    └── <entity>.py             # one file per manager
```

Two layout modes for models:

- **Compact (default in a fresh template):** `Base` and all ORM classes live together in `dbo/models.py`. Fine while there are only a handful of models. Alembic's `migrations/env.py` imports metadata from this module.
- **Extended (when models multiply):** `Base` moves into a dedicated `dbo/base_model.py`; ORM classes spread across `dbo/tables/<feature>.py`, grouped by domain; a public `dbo/database_models.py` is introduced with `from .base_model import Base as Base` plus re-exports of the models from `tables/`. In this mode Alembic imports from `database_models.py`. Migrating to the extended mode is a planned refactor — do not do it halfway.

### Model rules

- `Base` is a singleton for the whole project. Do not create a second `declarative_base`.
- Mixins come from `dbo/mixins.py`. Apply the ones you need when defining a model: `IDMixin` (UUID PK), `TimestampMixin` (`created_at` / `updated_at`), `SortOrderMixin` (user-controlled ordering).
- Domain-specific mixins (1C integration, lifecycle status, polymorphic references, etc.) are **not** shipped in the template — add them to `dbo/mixins.py` in the project that actually needs them.
- Models are **grouped by domain** into `dbo/tables/<feature>.py`. Do not create a file per model.
- Every model class **must** carry a docstring describing the business entity.
- `__tablename__` is snake_case and typically plural (`users`, `calendar_plans`).
- Foreign keys declare both `index=True` and an explicit `name="fk_..."` for the constraint.
- Every new model has to be visible to Alembic — imported in `dbo/database_models.py` (or directly in `dbo/models.py` while the project is still in compact mode).
- For versioning entities use `SQLAlchemy-Continuum`:
  ```python
  # at the top of the model file
  make_versioned(user_cls=None)
  # inside the class
  __versioned__ = {}
  # at the end of the file
  sqlalchemy.orm.configure_mappers()
  ```

### Manager rules

- One manager per primary entity: `<Entity>Manager`, file `managers/<entity>.py`.
- Inherits from `BaseManager` (`managers/common.py`); declares `entity = <Model>`.
- Constructor: `def __init__(self, db: AsyncSession)` — forwarded to `BaseManager`.
- Queries run **only** via SQLAlchemy ORM inside a manager. Services never write queries.
- `get_base_query()` is as plain as possible — no stray joins or where-clauses. If you need a variation, introduce a separate `get_<entity>_<purpose>_query()` method that returns a `Select` so it can be composed further.
- Public methods must carry a docstring. For `get_*_query` methods it is nice to quote the equivalent SQL in the docstring.
- The manager is re-exported through `managers/__init__.py` (`from .user import UserManager`). Consumers write `from src.models import managers` and use `managers.UserManager(db)`.

### What `BaseManager` already provides

Before writing a new method check whether the base class already covers the need — it usually does. Override / extend only when the behaviour really differs.

**Attributes a subclass declares:**

| Attribute | Type | Purpose |
| --- | --- | --- |
| `entity` | `Type[Base]` | **Required.** The ORM class this manager works with. |
| `join_columns` | `dict \| None` | A map of columns coming from joined entities (`{"project_name": Project.name}`) — consumed by `apply_filters` and `apply_ordering` when filtering or sorting by fields from joins. |
| `text_search_fields` | `dict[str, str]` | Declaration for `apply_full_text_search`: key = column name in the `select`, value = operator (`ilike`, `exact`, `startswith`, `endswith`, `gt` / `gte` / `lt` / `lte`, `uuid`, `date`, `in`, `not_in`, `is_null`). |
| `_special_filters_map` | `dict \| None` | Map of "non-standard" filters: `{"filter_name": {"filter_key": <column>, "filter_type": "eq" \| "contains" \| "overlap"}}` — useful when the query-param name does not match the column name. |

**Single-record CRUD:**

| Method | What it does |
| --- | --- |
| `create(payload, commit=True)` | Create an entity from a dict; commits and refreshes when `commit=True`. |
| `get_by_id(entity_id)` | Fetch the manager's entity by PK (via `session.get`). |
| `get_by_entity_id(entity_class, entity_id)` | Generic `session.get` for a foreign ORM class — when you need a related entity quickly without creating another manager. |
| `get_by_id_with_specified_fields(entity_id, fields, key_field="id")` | Like `get_by_id` but applies `load_only(...)` to load only the listed columns. |
| `get_by_ids(entity_ids)` | Fetch multiple entities by PK; an empty input returns `[]`. |
| `update_by_id(entity_id, payload, commit=True)` | Update fields of an existing entity; returns the updated object or `None`. |
| `delete_by_id(entity_id)` | Delete an entity by PK. |

**Bulk operations:**

| Method | What it does |
| --- | --- |
| `bulk_insert(entities_data, is_commit=False)` | One `INSERT` from a list of dicts. No commit by default — the caller decides when to flush. |
| `bulk_update(entities_to_update, is_commit=True)` | A single `UPDATE` statement matching on `id`. |
| `bulk_update_by_batch(entities_to_update, batch=32000)` | Same, but chunked into batches — required when the number of rows exceeds the driver's parameter limit. |
| `bulk_delete(entity_ids)` | A single `DELETE WHERE id IN (...)`. |
| `bulk_delete_by_batch(entity_ids, batch=32000)` | Batched deletion. |
| `bulk_upsert(data, key_field, update_fields, batch_size=5000, is_do_nothing=False)` | PostgreSQL-specific upsert via `INSERT ... ON CONFLICT DO UPDATE / DO NOTHING`. `key_field` — one column or a list — becomes the `index_elements`. |
| `create_or_update(entities)` | Takes a list of pydantic objects: rows with an `id` go through `update_by_id`, rows without — through `create`. Returns the final objects. |

**Queries: search, filtering, sorting, pagination, counting:**

| Method | What it does |
| --- | --- |
| `get_base_query() -> Select` | The default `select(self.entity)`. Override it when the baseline always includes joins or where-clauses. |
| `get_options_base_query() -> Select` | Query for options endpoints (typically `select(id, name)`). Defaults to `NotImplementedError` — override in the manager when the options feature is needed. |
| `search(query=None, order_by=None, pagination=None, with_scalars=True, search=None, **filters)` | The main search method: applies filters → full-text → ordering → pagination → returns a list of entities. Accepts any `Select` (falls back to `get_base_query`). |
| `count(query=None, search=None, group_by_field=None, **filters)` | Counts rows under the same filters and full-text. `group_by_field` switches to `COUNT(DISTINCT <col>)`. |
| `fetch(query, with_scalars=True, deduplicate=True, key_func=None)` | Runs an arbitrary `Select` and returns rows: scalars (ORM objects) or raw row tuples; optional deduplication. |
| `fetch_val(query) -> V \| None` | Runs a query and returns a single scalar value — for `SELECT COUNT(*)`, `SELECT EXISTS(...)`, etc. |
| `apply_filters(query, **filters)` | Applies a filter dict to a `Select`. Supports suffixes `__ilike`, `__in`, `__notin`, `__gt` / `__gte` / `__lt` / `__lte` / `__ne`, `__is` / `__isnot`, `__isnull` / `__isnotnull`, `__like`, plus "special" filters from `_special_filters_map`. `None` values are skipped. |
| `apply_filters_simple(query, **filters)` | A simpler variant: filters by columns that actually appear in the `SELECT` list of the `Select`. Useful for queries that go through subqueries or views. |
| `apply__in__filters_as_or(query, **filters)` | Takes only `*__in` filters and ties them with `OR` instead of `AND` — for "give me rows where any of these lists matched". |
| `add_order_to_query(query, order_by)` | Applies a single `order_by`. A leading `-` means DESC. For the `floor` / `section` tables natural sort kicks in (sorts by the numeric part of the string). |
| `apply_ordering(query, order_by)` | Applies a list of `order_by` clauses. |
| `apply_full_text_search(query, search)` | Applies the search substring to every column declared in `text_search_fields`, combining them with `OR`. |

**Not part of the public API (used internally), but worth knowing:**

- `_safe_operator(column_expr, op_name, value)` — wrapper over column operators (including `&&` for overlap and `@>` for contains on ARRAY / JSONB).
- `_deduplicate_rows(rows, key_func=None)` — deduplicates row tuples by a computed key.

**When to write your own method instead of using a base one:**

- The query is genuinely non-standard — a complex join, CTE, window functions, a custom GROUP BY. Name it `get_<purpose>_query()` (returns `Select`) or `<action>_<entities>()` (returns data).
- You need custom business validation before insert / update.
- In every other case — call the base methods from the service.

------------------------------------------------------------------------

## `src/services/` — business logic

### Structure

```
src/services/
├── __init__.py
├── common/
│   ├── __init__.py             # re-exports BaseService
│   └── base_service.py         # BaseService (ORM → pydantic mapping, etc.)
└── <feature>/
    ├── __init__.py
    └── <file>.py               # service class + get_<feature>_service
```

### Service rules

- Service class naming: `<Feature>Service` or `<Feature><Action>Service` (`UserInfoService`, `BookingCreateService`).
- Inherits from `BaseService` (`src/services/common/base_service.py`).
- The constructor receives an `AsyncSession` and immediately instantiates the managers it will use:
  ```python
  def __init__(self, db: AsyncSession):
      self.project_manager = managers.ProjectManager(db)
      self.queue_manager = managers.QueueManager(db)
  ```
- The dependency factory lives **right next to the service, in the same file**:
  ```python
  async def get_<feature>_service(
      db: AsyncSession = Depends(get_session),
  ) -> <Feature>Service:
      return <Feature>Service(db=db)
  ```
- **No imports** from `sqlalchemy` (except `AsyncSession` for typing). SQL belongs to managers.
- No imports of FastAPI primitives (`Request`, `HTTPException`) — those are the router's job.
- Public methods are `async` and carry a docstring. They return domain objects or pydantic schemas, **never `JSONResponse`**.
- When a service grows too large, split it into files inside `<feature>/` by operation (`info.py`, `create.py`, `update.py`).
- **Every public service method needs an automated test** (see the `backend-testing` skill).

### What `BaseService` already provides

`BaseService` is the Swiss Army knife for turning the results of manager queries into the pydantic schemas the router returns. Every method is static — it needs no `self` and never touches the database. Before hand-rolling a mapping loop, check whether something already exists.

| Method | Signature | When to use |
| --- | --- | --- |
| `map_obj_to_schema` | `(obj, schema_cls: Type[BaseModel]) -> BaseModel` | A single ORM entity (or any object with attributes) → an instance of a pydantic schema. Reads `schema_cls.model_fields` and pulls the same-named attributes from `obj`. The baseline for `GET /<entity>/{id}` and for list elements. |
| `map_nested_fields` | `(obj, schema_class: Type[BaseModel] \| None, field_base: str) -> dict \| None` | Flat result fields (`user_id`, `user_name`, `user_email`) → a dict for a nested pydantic schema. For each schema field it reads `f"{field_base}_{field}"` from `obj`. Returns `None` when **all** values are `None` — handy for optional nested blocks in the response. Passing `schema_class=None` also yields `None`, which lets you include the block conditionally. |
| `map_aggregated_array_fields` | `(obj, prefix: str, schema_cls: Type[T], suffixes=("ids", "names", "sort_orders")) -> list[T]` | Parallel arrays from PostgreSQL aggregation (`array_agg(...)`) → a list of pydantic schemas. Reads `f"{prefix}_{suffix}"` for every suffix, normalises array lengths (padding with `None`) and builds the objects. Rows where **all** fields are `None` are dropped. Use it when a single SQL row from `GROUP BY` carries aggregated child entities instead of separate JOIN rows. |
| `_natural_sort_key` | `(value: str) -> list` | Key for `sorted(..., key=BaseService._natural_sort_key)`: strings with numbers ("Floor 2", "Floor 10") are sorted by the numeric part rather than lexicographically. Private by convention, but often needed in services. |

**Common patterns:**

- "One object for an endpoint" — `self.map_obj_to_schema(project, ProjectSchema)`.
- "Paginated list" — `[self.map_obj_to_schema(p, ProjectSchema).model_dump() for p in projects]` followed by `ListDataResponseSchema.create(list_data=..., pagination=..., total=...)`.
- "Flat SQL with prefixed columns" (`manager.fetch(query, with_scalars=False)` → rows like `Row(id=..., project_id=..., project_name=..., project_code_1c=...)`) → `self.map_nested_fields(row, ProjectSchema, field_base="project")`.
- "Aggregated children in a single row" (`array_agg(member.id)`, `array_agg(member.name)`, `array_agg(member.sort_order)` grouped by `project.id`) → `self.map_aggregated_array_fields(row, "member", MemberSchema)`.

**When to add a method to a concrete service instead:**

- Complex business-transformation logic (forecast date computation, status mapping driven by domain rules) is no longer a utility — it belongs to the service method.
- A generic helper useful across multiple services — add it to `BaseService`, not to one service file.

------------------------------------------------------------------------

## `src/middlewares/` — FastAPI middleware

The directory ships in the template by default (an empty `__init__.py`). Populate it as you need: authorization (Keycloak), role checks, request logging, custom headers. One file per middleware: `<name>_middleware.py`. Wire them up in `src/main.py`.

Middleware specific to the Raport ecosystem (Keycloak and similar) is covered by the `report-microservice` skill.

------------------------------------------------------------------------

## `src/tasks/` — background jobs

The directory ships in the template by default (an empty `__init__.py`). One file per task or logical group: `<task>.py`. Usually Taskiq functions decorated with `@broker.task`. The broker itself is configured in `src/config/taskiq/`.

------------------------------------------------------------------------

## `src/external/` — external-system clients

One sub-directory per external system: `<system>/client.py`. The client is a standalone class, free of FastAPI, receiving its configuration through the constructor. Services compose external clients the same way they compose managers.

------------------------------------------------------------------------

## `src/utils/` — generic helpers

- `helpers.py` — technical helpers: `get_responses`, `catch_all_exceptions`, `get_pagination_info`, `pagination_params`, `safe_ilike`, `get_paginated_query`.
- `constants.py` — shared constants (enum values, magic numbers, timeouts).
- `exceptions.py` — custom exception classes.
- `datetime.py`, `json.py`, etc. — other technical utilities with no domain attachment.

**Do not put domain logic here** (tax computation, booking-number generation). Those belong to `services/` of the relevant feature.

------------------------------------------------------------------------

## `migrations/` — Alembic

- `migrations/env.py` — context setup. Imports `Base` (via `database_models`).
- `migrations/versions/<rev>_<slug>.py` — revisions.

### Rules

- Every ORM change comes with a new migration.
- Generation: `make migrate msg="<short_snake_case_message>"`.
- **Always read the generated migration by eye.** Alembic autogeneration occasionally:
  - misses `enum` types (`CREATE TYPE`);
  - skips indexes on FKs and `nullable=False` defaults;
  - does not emit `server_default`;
  - shuffles the order of operations in downgrade.
- Before merging, run locally: `make upgrade` → `make downgrade -1` → `make upgrade` (to verify the downgrade works).
- Revisions are never hand-written — autogeneration plus manual edits only.

------------------------------------------------------------------------

## `tests/` — automated tests

Mirrors `src/`. The full rules live in the **`backend-testing`** skill. Mandatory points:

- The test database is seeded from `tests/dump_data/` (the minimum set of rows per table).
- Levels: integration (through `client` + real DB) and unit (through the `async_session` mock).
- Every public service/manager method and every endpoint requires at least one happy path and one failure case.
- Protected endpoints require a paired test (authenticated + unauthenticated via the `no_auth_mock` marker).
- Coverage target: 70%.

------------------------------------------------------------------------

## Python code rules

### PEP8 and formatting

- PEP8, except for line length. **Line length is 120** (see `ruff.toml`).
- Formatter: `ruff format` (`make lint`). Quotes are double.
- Function call formatting:
  - if the call fits on one line, no line breaks;
  - if it does not fit, break after the opening parenthesis and align the closing one at the same indent:
    ```python
    result = some_function(
        arg1,
        arg2,
        keyword_arg=value,
    )
    ```
  - trailing comma in every multi-line listing.
- Keyword arguments: always supply the name unless the role is obvious from the function's name.

### Imports

- `isort`. Three blocks: standard library → third-party packages → local modules.
- Third-party imports are point-wise (`from fastapi import APIRouter`). `import *` is forbidden.
- Standard library imports are module-level (`import collections`); individual entities are imported point-wise when needed.
- Name collisions are resolved with `as`.

### `__init__.py`

- Imports only. No logic, no constants, no side effects.
- In a top-level package it acts as the module's public API.

### Typing

- Every function and method has type annotations for both arguments and return value.
- SQLAlchemy `Column` may stay without an annotation when the type is obvious from `Column(...)`.
- Use `Optional[X]` for nullable fields. Do not mix `None | X` and `Optional[X]` in the same file — pick one style.
- `List[X]` / `Dict[K, V]` are allowed; `list[X]` / `dict[K, V]` are preferred (Python 3.12).
- For `async` functions, the return type does not need `Awaitable` — `async def` implies it.

### Comments and docstrings

- **Comments are rare.** Write them when a function does something non-obvious, when a tricky case is handled, or when you need to reference a ticket / business context (`# see RAPORT-482 for the formula background`).
- Bad comments ("fetch user data", "build context"): if you want to write one, rename the function instead.
- **TODO / FIXME** never land in a commit. Either fix the issue or open a ticket and remove the comment.
- One-line docstring: `"""Describes the action."""` — a single line ending with a period.
- Multi-line docstring:
  ```python
  """
  Opening line with the description. Ends with a period.

  Details and the method's contract: parameters, return value, exceptions.
  """
  ```
- Public methods on managers and services **must** have a docstring.
- A model class carries a docstring with the business description of the entity.
- For `get_*_query` methods on a manager it is nice to quote the SQL in the docstring.
- **Every comment and docstring in `.py` files is English-only.** This applies to every microservice.

### Logging

- Logs are English-only — e.g. `logger.info("Requesting balance")`.
- Acquire a logger via `log = LoggerProvider().get_logger(__name__)` in every file.
- Levels: `debug` — development-time technical detail; `info` — lifecycle events; `warning` — anomalies without failure; `error` — operation failure; `exception` — only inside `except`, to capture the traceback.
- Never log secrets: tokens, passwords, personal data. Mask them before logging.

### Dead code

- Commented-out code, abandoned branches, throwaway scripts — delete them. Git keeps the history.

------------------------------------------------------------------------

## API construction rules

They live in the **`generate-api-method`** skill, including `@catch_all_exceptions`, `get_responses(ResponseGroup.ALL_ERRORS)`, `summary` / `description`, kebab-case URLs, pagination / sorting / filtering patterns, and ready-made endpoint templates.

Here, in `project-structure`, only the **file placement** part is fixed: where the router lives, where the schemas live, where the service factory sits — see the `src/api/` section above.

------------------------------------------------------------------------

## Naming conventions

- **Files and directories:** `snake_case` (`calendar_plan`, `work_group.py`).
- **URL prefixes:** `kebab-case` (`/calendar-plans`).
- **Classes:** `PascalCase` (`UserInfoService`, `ProjectManager`, `CreateBookingRequest`).
- **Functions and variables:** `snake_case` (`get_user_by_id`, `user_router`).
- **Router:** `<feature>_router`.
- **Service:** `<Feature>[Action]Service` (`UserInfoService`, `BookingCreateService`).
- **Manager:** `<Entity>Manager`.
- **Pydantic schemas:** `<Action><Entity>Request`, `<Action><Entity>Response`, `<Entity>Schema`, `<Entity>ListResponseSchema`, `<Entity>Filters`.
- **Database tables:** `snake_case`, typically plural (`users`, `calendar_plans`).

------------------------------------------------------------------------

## Decision matrix — "where does X go"

| Need | Directory | File | Feature skill |
| --- | --- | --- | --- |
| A new database table | `src/models/dbo/tables/` | `<feature>.py` (grouped by domain) + import in `database_models.py` | `create-model` |
| A new CRUD manager | `src/models/managers/` | `<entity>.py` + re-export in `managers/__init__.py` | `create-model` |
| An admin panel for a model | `src/config/admin/model_admin/` | `<entity>.py` + registration in `admin/config.py` | `create-model` |
| A new HTTP endpoint in an existing feature | `src/api/v1/<feature>/` | `views.py` | `generate-api-method` |
| A brand-new feature (endpoint bundle) | `src/api/v1/<feature>/` (new directory) | `views.py` + `schemes.py` | `generate-api-method` |
| A feature-scoped Pydantic request/response schema | `src/api/v1/<feature>/schemes.py` | — | `generate-api-method` |
| A shared schema (error, pagination, base filter) | `src/api/schemes.py` | — | — |
| Business logic | `src/services/<feature>/` | `<file>.py` (`info.py`, `create.py`, …) | `generate-api-method` |
| The `get_<feature>_service` factory | `src/services/<feature>/<file>.py` | next to the service | `generate-api-method` |
| Shared service utilities (mapping, …) | `src/services/common/` | `base_service.py` | — |
| An external API client | `src/external/<system>/` | `client.py` | — |
| Middleware (auth, etc.) | `src/middlewares/` | `<name>_middleware.py` | `report-microservice` |
| A background task | `src/tasks/` | `<task>.py` | — |
| A domain-free technical helper | `src/utils/` | `helpers.py` / `constants.py` / `exceptions.py` | — |
| A logger in a new file | anywhere under `src/` | `log = LoggerProvider().get_logger(__name__)` | — |
| A DB migration | `migrations/versions/` | generated via `make migrate msg="..."` | `create-model` |
| An API test | `tests/test_api/test_<feature>/` | `test_<endpoint>.py` | `backend-testing` |
| A service test | `tests/test_services/<feature>/` | `test_<file>.py` | `backend-testing` |
| A manager test | `tests/test_managers/` | `test_<entity>.py` | `backend-testing` |
| A background-task test | `tests/test_tasks/` | `test_<task>.py` | `backend-testing` |
| A new environment variable | `src/config/settings.py` + `.env.example` | field on `AppConfig` | `initial-setup` |
| Test seed data | `tests/dump_data/dumps/` | `dump_<table>.json` | `backend-testing` |

------------------------------------------------------------------------

## Mandatory post-task checks

After any development, **always** run the two commands below. A task counts as finished only when both are green.

```bash
make lint   # ruff + ruff-format + mypy via pre-commit
make test   # pytest with coverage (report at htmlcov/index.html)
```

If something fails:
- `make lint` — ruff has already applied the safe fixes; resolve the remaining errors by hand until the command is green;
- `make test` — inspect the failure, fix the code (not the test, unless the logic is genuinely broken), and rerun.

Other Makefile commands that come in handy:

```bash
make run                         # local dev server
make migrate msg="short_name"    # new Alembic revision
make upgrade                     # alembic upgrade head
make downgrade                   # alembic downgrade -1
make history                     # revision history
```

------------------------------------------------------------------------

## Pre-handoff checklist

1. **Structure.** Every new file sits in the layer and directory from the decision matrix above.
2. **Layers.** No cross-layer imports: router ↛ manager/model; service ↛ FastAPI; service ↛ `sqlalchemy` (except typing).
3. **Models.** A new model lives in `src/models/dbo/tables/<feature>.py` and is imported from `database_models.py`. The right mixins are applied.
4. **Manager.** Inherits from `BaseManager` and declares `entity = ...`. Queries go through the ORM only — no raw SQL without a strong reason.
5. **Service.** Inherits from `BaseService`. No `sqlalchemy` / FastAPI imports except for typing. The `get_<feature>_service` factory sits next to the class.
6. **Router.** Every endpoint has `@catch_all_exceptions`, `responses=get_responses(...)`, `summary`, `description`. URLs are kebab-case. Authorization is expressed via `Depends`.
7. **Migration.** If models changed, a migration is generated, read by eye, and run locally through `upgrade` → `downgrade -1` → `upgrade`.
8. **Tests.** Every new public method and endpoint has at least one happy path plus one failure case. Protected endpoints have the paired test (authenticated + `@pytest.mark.no_auth_mock`). Seed data lives in `tests/dump_data/dumps/` or in a local fixture with cleanup.
9. **Documentation.** Docstrings on every public method of managers and services, and on model classes. Swagger metadata on every endpoint.
10. **Logs and comments.** English only. No TODO / FIXME. No commented-out code.
11. **Typing.** Every new function carries type hints. `make lint` (mypy) is green.
12. **Configuration.** New environment variables appear both in `AppConfig` and in `.env.example`.
13. **`make lint`** — green.
14. **`make test`** — green, coverage stays at or above 70%.

------------------------------------------------------------------------

## Common mistakes

### A service runs SQL

The service writes `select(User)...` or `session.execute(...)`. That is the manager's job. Move it into `<Entity>Manager.get_<purpose>_query()` or `<Entity>Manager.<action>()`.

### A router hits a manager directly

That bypasses the service layer. Create a service — even one with a single pass-through method — and have the router call the service only.

### A model is declared under `dbo/tables/` but not picked up by a migration

The import in `src/models/dbo/database_models.py` is missing. Alembic's `env.py` only sees models exported through that module.

### Circular imports between `models` and `services`

A service imports a pydantic schema from `src/api/v1/...`, and a model imports something from a service. Break the cycle: schemas do not know about services, models know only about `Base`, mixins and other models.

### A helper with domain logic landed in `src/utils/`

`calculate_booking_tax` → `src/services/booking/tax.py`, not `src/utils/helpers.py`. `utils` holds only code reusable across domains.

### URL in snake_case

`/calendar_plans` → `/calendar-plans`. The jsonapi guideline plus consistency.

### Logs and docstrings in Russian

Keep English only. If you spot any, translate.

### `make lint` and `make test` were not run after the change

A task is not finished until both commands are green.

------------------------------------------------------------------------

## Related skills

- **`initial-setup`** — the first-time setup of the template for a new microservice.
- **`create-model`** — creating a new ORM model plus its manager and admin view.
- **`generate-api-method`** — creating a new API endpoint plus its service method and schemas.
- **`backend-testing`** — writing automated tests for the new codebase.
- **`report-microservice`** — specifics for microservices inside the "Raport" ecosystem (Keycloak auth, reference APIs).

Before any code task, load `project-structure` (this skill) first, then load the feature-specific one.
