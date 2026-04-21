---
name: generate-api-method
description: Creates a new API endpoint in the FastAPI + SQLAlchemy template — Pydantic request/response/filter schemas, a service method with its factory, and a router handler. The endpoint conforms to the shared contract — @catch_all_exceptions, get_responses(ResponseGroup.ALL_ERRORS), typed ResponseNNNSchema classes from src/api/schemes.py, kebab-case URLs. Requires project-structure to be loaded first and make lint / make test to pass afterwards.
---

# Generate API Method (FastAPI + SQLAlchemy)

## Purpose

This skill builds the full path from an HTTP request down to the manager call:

- Pydantic schemas in `src/api/v1/<feature>/schemes.py` (request, response, filters);
- a service method in `src/services/<feature>/<file>.py` and/or the `get_<feature>_service` factory next to it;
- a router handler in `src/api/v1/<feature>/views.py`, wrapped with `@catch_all_exceptions` and fully documented in OpenAPI;
- mounting the router in `src/main.py` the first time the feature is introduced.

The skill **does not** create ORM models, managers or migrations — that is the job of `create-model`. Typical flow: `create-model` → `generate-api-method` → `backend-testing`.

## When to activate

- The user describes a new endpoint (`GET /api/v1/projects`, `POST /api/v1/bookings`).
- A new method must be added to an existing feature router.
- An existing endpoint's contract is updated (new request/response fields, new filters).

**Always** load `project-structure` first — that is where the layering, naming and placement rules come from.

------------------------------------------------------------------------

## What to ask the user

Collect the full list **before** touching files. Offer sensible defaults for missing values.

### Required

1. **Method description** in the user's language (a short phrase like "list bookings for the current user"; `summary` / `description` in Swagger will be rephrased to English imperative voice).
2. **HTTP method:** `GET` / `POST` / `PUT` / `PATCH` / `DELETE`.
3. **URL:**
   - *prefix* — the feature name in kebab-case (`/projects`, `/calendar-plans`);
   - *path* relative to the prefix (`""`, `"/{id}"`, `"/check"`). The full URL always starts with `/api/v1`, and that prefix is mounted only once in `src/main.py` — never duplicated inside the router itself.
4. **OpenAPI tags** — the Swagger group name (`Projects`, `Calendar plans`).
5. **Authorization required** (yes / no).
6. **Service and method** — a reference such as `src/services/<feature>/<file>.py:<Service>.<method>`. If the method does not exist yet, create a stub that returns mock data until the real implementation lands.
7. **Request body** (for POST / PUT / PATCH) — JSON schema of fields with types and nullability.
8. **Response body** — JSON schema of the success payload, or the name of an already existing schema.

### Optional

9. **Query parameters** — a list of `param_name (Type, default?)`. With more than one, bundle them into a dedicated Pydantic model `<Entity>Filters` where each field uses `Query(...)`.
10. **Path parameters** — declared in the URL (`{id}`, `{user_id}`); their types and descriptions go into the function signature.
11. **Pagination / sorting** — whether they are needed (`PaginationParams` / `OrderParams` from `src/api/schemes.py`).
12. **Filtering** — which fields, with which suffixes (`__ilike`, `__in`, `__gte`, etc. — see `BaseManager.apply_filters` in `project-structure`).
13. **Narrow error group** — if the endpoint physically cannot produce the whole `ALL_ERRORS`, pass the appropriate `ResponseGroup` (`AUTH_ERRORS`, `CLIENT_ERRORS`, `SERVER_ERRORS`, `VALIDATION_ERRORS`, `RATE_LIMIT_ERRORS`).
14. **Popup-style error** — whether certain failure paths should return `HTTPException(detail={"message": "...", "show": True})` so the frontend renders a toast.

If the user answers vaguely, lock in the defaults and present the final plan before making changes.

------------------------------------------------------------------------

## Step 0 — Inspect the template

1. **Does the feature exist?**
   - The directory `src/api/v1/<feature>/` exists → add the endpoint to its `views.py`; the router is already mounted in `src/main.py`.
   - It does not → create the whole package (`__init__.py`, `views.py`, `schemes.py`) and add `app.include_router(<feature>_router, prefix="/api/v1")` to `src/main.py`.
2. **Does the service exist?**
   - There is `src/services/<feature>/<file>.py` with the class and a `get_<feature>_service` factory → add a new method.
   - There is none → create both the service and the factory. The service inherits from `BaseService`; its constructor accepts `AsyncSession` and instantiates the required managers.
3. **Do the managers it will rely on exist?** If not, **stop** and redirect the user to `create-model`.
4. **Check for collisions** between URLs and handler function names — within a router, handler names must be unique (FastAPI rejects duplicates).
5. **Source of truth for the response contract** — `src/api/schemes.py`: `ResponseNNNSchema`, `ResponseGroup`, `DataResponseSchema[T]`, `ListDataResponseSchema[T]`, `NamedEntitySchema`, `IDMixinSchema`, the shared `<Entity>BaseFilters`. Reuse them — do not clone duplicates.

**Reference files in the template:**

- `src/api/v1/user/views.py` — an endpoint using `@catch_all_exceptions`, `get_responses(ResponseGroup.ALL_ERRORS)`, `Depends(get_user_service)`.
- `src/api/v1/user/schemes.py` — the minimal feature schema `UserMeResponse`.
- `src/services/user/info.py` — `UserInfoService(BaseService)` and the `get_user_service` factory.
- `src/api/schemes.py` — every envelope class and `ResponseGroup`.
- `src/main.py` — the single place where routers are mounted under `/api/v1`.

------------------------------------------------------------------------

## Step 1 — Pydantic schemas (feature `schemes.py`)

File: `src/api/v1/<feature>/schemes.py`. Created together with the feature package; if it already exists, extend it with new classes instead of cloning the directory.

### Naming

- `<Action><Entity>Request` — request body: `CreateBookingRequest`, `UpdateBookingRequest`.
- `<Entity>Schema` — the canonical DTO for the entity in responses: `BookingSchema`, `ProjectSchema`.
- `<Action><Entity>Response` — a single-shot response with a non-standard shape: `CheckCalendarPlanResponse`.
- `<Entity>ListResponseSchema` — paginated list; inherits from `ListDataResponseSchema` and fixes `data: list[<Entity>Schema]`.
- `<Entity>Filters` — query parameters for a list endpoint.

### Template

```python
from typing import Optional
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, Field

from src.api.schemes import ListDataResponseSchema, NamedEntitySchema


class BookingSchema(NamedEntitySchema):
    """Business DTO of a booking returned in lists and detail endpoints."""

    project_id: Optional[UUID] = Field(None, description="Project the booking belongs to")
    start_at: Optional[str] = Field(None, description="Booking start time, ISO 8601")


class BookingListResponseSchema(ListDataResponseSchema):
    data: list[BookingSchema]


class CreateBookingRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Booking name")
    project_id: UUID = Field(..., description="Project the booking belongs to")
    start_at: str = Field(..., description="Booking start time, ISO 8601")


class BookingFilters(BaseModel):
    project_id: Optional[UUID] = Field(
        Query(None, description="Filter by project id"),
    )
    name__ilike: Optional[str] = Field(
        Query(None, description="Case-insensitive substring filter for name"),
    )
```

### Rules

- All `description=` values are English, imperative or declarative voice.
- Types: `UUID` for identifiers, `Optional[X]` for nullable fields, `list[X]` / `dict[K, V]` preferred over `List` / `Dict`.
- Shared building blocks (pagination, errors, common FK filters) are **reused** from `src/api/schemes.py`, never cloned inside a feature.
- For lists, inherit from `ListDataResponseSchema` (it already carries `pagination` and `data`).
- Filter fields always use `Query(...)` inside `Field(Query(...))` — otherwise FastAPI puts them into the request body.
- Filter suffixes (`__ilike`, `__in`, `__gte`, …) must match those supported by `BaseManager.apply_filters`.

------------------------------------------------------------------------

## Step 2 — Service and factory

File: `src/services/<feature>/<file>.py`. The file name reflects the logical group of operations: `info.py`, `create.py`, `bookings.py`.

### 2.1 When the service does not exist yet

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import LoggerProvider
from src.config.postgres.db_config import get_session
from src.models import managers
from src.services.common import BaseService

log = LoggerProvider().get_logger(__name__)


class BookingService(BaseService):
    """Business logic for bookings."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.booking_manager = managers.BookingManager(db)
        self.project_manager = managers.ProjectManager(db)

    async def list_bookings(
        self,
        filters: dict,
        order_by: list[str],
        pagination,
    ):
        # TODO: Implement real listing via self.booking_manager.search + count.
        return {"data": [], "pagination": None}


async def get_booking_service(
    db: AsyncSession = Depends(get_session),
) -> BookingService:
    return BookingService(db=db)
```

### 2.2 When the service already exists

Add the new method to the same class and leave the constructor alone unless you genuinely need a new manager. If a new manager is required, instantiate it once in `__init__` — no lazy instantiation.

### 2.3 Rules

- **The class always inherits from `BaseService`** — even if it does not use its helpers yet. Inheritance grants access to `map_obj_to_schema`, `map_nested_fields`, `map_aggregated_array_fields`, `_natural_sort_key` (see `project-structure`).
- The constructor takes **only** an `AsyncSession` and instantiates every manager it needs up front.
- **No imports** from `sqlalchemy` except `AsyncSession` for typing. `select`, `update`, `delete` belong to managers.
- **No imports** of FastAPI primitives (`Request`, `HTTPException`). Business exceptions are custom (`src/utils/exceptions.py`) and the router maps them.
- Public methods are `async def` with an English docstring. They return domain objects or pydantic schemas, **never `JSONResponse`**.
- The `get_<feature>_service` factory lives in the **same file** as the class. Splitting them clutters the endpoint with extra imports.
- When the method has no real logic yet, return a **typed mock** (a pydantic schema with placeholder values), not a bare dict — it makes writing the endpoint tests immediately easier.
- **Every** public service method requires an automated test (see `backend-testing`).

------------------------------------------------------------------------

## Step 3 — Router and endpoint

File: `src/api/v1/<feature>/views.py`.

### 3.1 When the router does not exist yet

```python
from fastapi import APIRouter

from src.config.logger import LoggerProvider

log = LoggerProvider().get_logger(__name__)

bookings_router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
)
```

Right after creating the router, **always** mount it in `src/main.py`:

```python
from src.api.v1.bookings.views import bookings_router

app.include_router(bookings_router, prefix="/api/v1")
```

The `/api/v1` prefix is mounted only in `main.py`. The router itself carries only the feature name (`prefix="/bookings"`).

### 3.2 Endpoint anatomy

```python
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.schemes import OrderParams, PaginationParams, ResponseGroup
from src.api.v1.bookings.schemes import (
    BookingFilters,
    BookingListResponseSchema,
    BookingSchema,
    CreateBookingRequest,
)
from src.services.bookings.bookings import BookingService, get_booking_service
from src.utils.helpers import catch_all_exceptions, get_responses, pagination_params


@bookings_router.get(
    "",
    responses={
        200: {
            "model": BookingListResponseSchema,
            "description": "List of bookings available to the current user",
        },
        **get_responses(ResponseGroup.ALL_ERRORS),
    },
    summary="List bookings",
    description="Returns a paginated list of bookings the current user is allowed to see.",
)
@catch_all_exceptions
async def list_bookings(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    request: Request,
    filters: BookingFilters = Depends(),
    pagination: PaginationParams = Depends(pagination_params),
    order_by: OrderParams = Depends(),
    service: BookingService = Depends(get_booking_service),
):
    return await service.list_bookings(
        filters=filters.model_dump(exclude_none=True),
        order_by=order_by.model_dump()["order_by"],
        pagination=pagination,
        user_id=request.user.id,
    )
```

### 3.3 Required elements

- The handler is **`async def`**. It returns a pydantic response schema (do not set `response_model=` on the decorator — the type is tracked through `responses={200: {"model": ...}}` and Swagger).
- The **`@catch_all_exceptions`** decorator from `src/utils/helpers.py` is always applied. It converts `HTTPException`, `RequestValidationError`, `ValidationError`, `ClientDisconnect` and any unexpected exception into a `JSONResponse` with a typed `ResponseNNNSchema` body (`code`, `message`, optional `details`).
- The `responses=` argument combines the success response with `**get_responses(<ResponseGroup>)`:
  - `ResponseGroup.ALL_ERRORS` — default (includes 400/401/403/404/413/422/429/500/503);
  - `ResponseGroup.AUTH_ERRORS` — 401/403 (open or semi-open endpoints that do not validate input);
  - `ResponseGroup.CLIENT_ERRORS` — 400/404/422;
  - `ResponseGroup.SERVER_ERRORS` — 500/503;
  - `ResponseGroup.VALIDATION_ERRORS` — 422;
  - `ResponseGroup.RATE_LIMIT_ERRORS` — 429.
  When unsure, use `ALL_ERRORS`. A narrower group is justified only when you can actually prove the other codes cannot be produced.
- `summary=` and `description=` are mandatory, English, imperative voice. They become the title and the paragraph under the endpoint in Swagger.
- Path parameters: `<name>: <Type>` in the signature, with `Path(..., description="...")` when the description is non-trivial.
- Query parameters: single ones use `Query(..., description="...")`; a group goes into a dedicated `<Entity>Filters` via `Depends()`.
- **No business logic in the body** — only parameter gathering, a service call, returning the result.

### 3.4 The endpoint body

Only the following are allowed:

1. Parameter gathering (`filters.model_dump(exclude_none=True)`, `pagination`, `request.user.id`).
2. A single service call (`await service.<method>(...)`).
3. A short 403/404 guard when the service returns `None` or an empty structure:
   ```python
   result = await service.get_booking(booking_id)
   if result is None:
       raise HTTPException(status_code=404, detail="Booking not found")
   return result
   ```

Anything heavier (computations, conditional branches, transformations) belongs to the service.

### 3.5 Variations per HTTP method

- **GET / list:** follow the signature in the template above. Response — `<Entity>ListResponseSchema`.
- **GET / detail:**
  ```python
  @bookings_router.get("/{booking_id}", ...)
  @catch_all_exceptions
  async def get_booking(
      credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
      booking_id: UUID,
      service: BookingService = Depends(get_booking_service),
  ):
      booking = await service.get_booking(booking_id)
      if booking is None:
          raise HTTPException(status_code=404, detail="Booking not found")
      return booking
  ```
- **POST / create:** add `payload: CreateBookingRequest` to the signature. The success entry in `responses=` uses status 201 (`responses={201: {"model": <EntitySchema>, "description": "..."}, **get_responses(ResponseGroup.ALL_ERRORS)}`). Set `status_code=201` on the decorator.
- **PUT / PATCH / update:** a path parameter `{id}` plus `payload: UpdateBookingRequest`. For PATCH the payload fields are `Optional[...]` with default `None`.
- **DELETE:** returns `204 No Content` or `200` with an empty object. Use `status_code=204` on the decorator and return nothing.

------------------------------------------------------------------------

## Step 4 — Authorization

- **Protected endpoint:** add `credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]` as the first parameter after any self-specific ones. This shows the lock in Swagger and lets the `mock_http_bearer` test fixture intercept the token.
- **The `user_id` from the token** arrives through middleware and is available as `request.user.id`. The middleware lives in `src/middlewares/` and is bootstrapped by the `report-microservice` skill (Keycloak in the Raport ecosystem). On a fresh template with no middleware wired up yet, passing `user_id` as a query parameter is acceptable as a temporary workaround for the first runs.
- **Public endpoint** (healthcheck, open dictionaries): do not attach `HTTPBearer()` and state explicitly in `summary` (or `description`) that the endpoint is public.
- **A paired test is mandatory** for a protected endpoint: (1) authorized happy path → 200, (2) unauthorized test marked with `@pytest.mark.no_auth_mock` → 401/403 (see `backend-testing`). Without the paired test, a regression where `HTTPBearer` is removed from an endpoint slips through.

------------------------------------------------------------------------

## Step 5 — Pagination, sorting, filtering

### Pagination

```python
from src.api.schemes import PaginationParams
from src.utils.helpers import pagination_params

pagination: PaginationParams = Depends(pagination_params)
```

Pass `pagination` into `manager.search(...)` from the service. Wrap the response with `ListDataResponseSchema.create(list_data=..., pagination=pagination, total=total)` — the method computes `total_pages`, `next_page`, `prev_page` for you.

### Sorting

```python
from src.api.schemes import OrderParams

order_by: OrderParams = Depends()
```

`order_by.model_dump()["order_by"]` is a `list[str]` of field names; a leading `-` means DESC. Pass it into `manager.search(order_by=..., ...)` which forwards to `apply_ordering(...)`.

### Filtering

A dedicated `<Entity>Filters(BaseModel)` in the feature's `schemes.py`:

```python
class BookingFilters(BaseModel):
    project_id: Optional[UUID] = Field(Query(None, description="Filter by project id"))
    status__in: Optional[list[str]] = Field(Query(None, description="Filter by status list"))
    start_at__gte: Optional[str] = Field(Query(None, description="Start date from"))
    start_at__lte: Optional[str] = Field(Query(None, description="Start date to"))
```

Signature: `filters: BookingFilters = Depends()`. In the service pass `filters.model_dump(exclude_none=True)` into `BaseManager.apply_filters(query, **filters)`.

**Supported suffixes** (from `BaseManager`): `__ilike`, `__like`, `__in`, `__notin`, `__gt` / `__gte` / `__lt` / `__lte` / `__ne`, `__is` / `__isnot`, `__isnull` / `__isnotnull`, `__startswith`, `__endswith`. The full list and nuances are in `project-structure`, section "What `BaseManager` already provides".

Reuse the shared FK filter mixins from `src/api/schemes.py` (`ProjectBaseFilters`, `ConstructionObjectBaseFilters`, …) — inherit your `<Entity>Filters` from them whenever the same filter fields show up in multiple endpoints.

------------------------------------------------------------------------

## Step 6 — Error handling

`@catch_all_exceptions` does the heavy lifting: any exception becomes a typed `JSONResponse`. The endpoint only decides **which** error to raise.

### Mapping table

| Scenario | How to raise it in the endpoint | Status | Response body |
| --- | --- | --- | --- |
| Invalid path / query | Wrong type in `Query` / `Path` | 422 | `Response422Schema` (`code`, `message`, `details`) |
| Invalid request body | Pydantic rejected the `CreateRequest` | 400 | `Response400Schema` (`code`, `message`, `details`) |
| Business not-found | Service returned `None` → `HTTPException(404, "<entity> not found")` | 404 | `Response404Schema` |
| Authorization failure | Middleware / `HTTPBearer` rejected the request | 401 / 403 | `Response401Schema` / `Response403Schema` |
| Business rule violated, frontend needs a popup | `HTTPException(400, detail={"message": "...", "show": True})` | 400 | `Response400Schema` with `detail` preserved |
| Rate limit exceeded | `HTTPException(429)` | 429 | `Response429Schema` |
| Unhandled failure | An exception inside the service | 500 | `Response500Schema` |

### Rules

- **Never catch Pydantic validation errors manually** — the decorator handles them.
- **Popup on the frontend:** `HTTPException(status_code=..., detail={"message": "<human text>", "show": True})`. The `show: True` key is the Raport ecosystem convention — the frontend renders the message in a toast / modal.
- **Custom exceptions** from `src/utils/exceptions.py` are wrapped into `HTTPException` at the router boundary, not in the middle of a service.
- **Do not re-log** a caught `HTTPException` — `@catch_all_exceptions` already emits a warning with context.

------------------------------------------------------------------------

## Step 7 — Tests

Rules live in the `backend-testing` skill. Minimum for a generated endpoint:

1. Happy path (integration via `client` against the real test database seeded from dumps).
2. A negative scenario specific to the endpoint (404 for GET/PUT/DELETE on a missing id, 422 for an invalid body, etc.).
3. **For a protected endpoint — a paired test** with the `@pytest.mark.no_auth_mock` marker on the unauthorized scenario (expecting 401/403).
4. For the service method — a dedicated unit test with the `async_session` mock and a mocked manager.

Endpoint test file: `tests/test_api/test_<feature>/test_<endpoint>.py`.
Service test file: `tests/test_services/<feature>/test_<file>.py`.

When the rows needed for a test are missing from `tests/dump_data/dumps/`, either add the minimum set to the dump (see `backend-testing`) or use a local fixture with `add()` + cleanup inside `yield`.

------------------------------------------------------------------------

## Step 8 — Final checks

Mandatory:

```bash
make lint   # ruff + ruff-format + mypy
make test   # pytest with coverage
```

By eye:

- The router is mounted in `src/main.py` (when the feature is new).
- The full URL matches what was agreed (`/api/v1/<feature>/<path>`).
- Swagger strings (`summary`, `description`, query parameter descriptions) are English and imperative.
- All imports are correct; no `from src.api.routes.*` (the legacy path from older projects).
- The handler function name is snake_case and unique within the router.
- The endpoint body is a single service call plus, when needed, a 404 guard.

------------------------------------------------------------------------

## Pre-handoff checklist

1. **Placement**
   - Schemas in `src/api/v1/<feature>/schemes.py`, reusing the base classes from `src/api/schemes.py`.
   - Service in `src/services/<feature>/<file>.py`, with the `get_<feature>_service` factory next to it.
   - Router in `src/api/v1/<feature>/views.py`, mounted in `src/main.py` under `/api/v1`.
2. **Layers**
   - The endpoint does not import managers or models directly.
   - The service does not import `sqlalchemy` (except `AsyncSession`) or FastAPI primitives.
   - The service inherits from `BaseService`.
3. **Response contract**
   - `@catch_all_exceptions` on every endpoint.
   - `responses=` expands `**get_responses(ResponseGroup.<...>)`.
   - The success response is described by its own schema (200 / 201 with `model` / `description`).
   - `summary` + `description` are English, imperative voice.
4. **URL and naming**
   - URLs are kebab-case.
   - Router is named `<feature>_router`; handler function names are snake_case.
   - Schema names follow `<Action><Entity>Request` / `<Entity>Schema` / `<Entity>ListResponseSchema` / `<Entity>Filters`.
5. **Authorization**
   - A protected endpoint uses `Depends(HTTPBearer())`.
   - A paired test with `@pytest.mark.no_auth_mock` is in place.
6. **Pagination / sorting / filtering**
   - List endpoints use `PaginationParams` + `pagination_params`.
   - Sorting via `OrderParams`.
   - Filters live in a dedicated `<Entity>Filters` consumed through `Depends()`; suffixes match `BaseManager.apply_filters`.
7. **Errors**
   - 404 / 400 / 429 / etc. raised through `HTTPException` with a clear `detail`.
   - Popup-style errors use `detail={"message": "...", "show": True}`.
8. **Tests**
   - Happy path + one failure case per endpoint.
   - A unit test for the service method.
   - A paired auth test for protected endpoints.
9. **Checks**
   - `make lint` is green.
   - `make test` is green, coverage ≥ 70%.

------------------------------------------------------------------------

## Output format

The final response to the user contains:

1. Schema code (`src/api/v1/<feature>/schemes.py`) — in full, or as a diff when the file already existed.
2. Service code (`src/services/<feature>/<file>.py`) — the new class or a diff adding the method, plus the factory when it was missing.
3. Endpoint code (`src/api/v1/<feature>/views.py`) — imports plus the new handler.
4. A diff for `src/main.py` when a new router was mounted.
5. Test templates: happy path, negative scenario, paired auth test (when applicable).
6. A list of new and modified files.
7. Results of `make lint` and `make test` — either green, or the list of errors that still need manual fixes.

------------------------------------------------------------------------

## Common mistakes

### An endpoint without `@catch_all_exceptions`

Any non-`HTTPException` failure produces a 500 with an untyped body, and the frontend cannot parse it. The decorator is mandatory.

### The `/api/v1` prefix duplicated

The router is declared with `prefix="/api/v1/bookings"`, but `main.py` still adds `/api/v1`, and the URL becomes `/api/v1/api/v1/bookings`. The router carries only `prefix="/bookings"`; `main.py` adds `prefix="/api/v1"`.

### URLs in snake_case

`/calendar_plans` → `/calendar-plans`. The jsonapi guideline plus ecosystem consistency.

### Business logic inside the endpoint body

Loops, conditional transformations, ORM queries — all of those go into the service. The router stays declarative.

### A service importing `sqlalchemy`

`select(...)` or `session.execute(...)` inside a service is an anti-pattern. Move it to `<Entity>Manager.get_<purpose>_query()`.

### A service without a `get_<feature>_service` factory

The endpoint cannot inject the service through `Depends`, and people start instantiating it by hand, passing `db` around. The factory is mandatory and lives next to the class.

### `responses=` without `get_responses(...)`

Swagger only shows the success code, and the typed error bodies are lost. Always expand `**get_responses(<ResponseGroup>)`.

### Query parameters ending up in the body

Forgetting to wrap a field in an `<Entity>Filters` with `Query(...)` — FastAPI then places the field into the request body and the endpoint fails on GET. Every filter field uses `Query(...)` inside `Field(...)`.

### `HTTPException(detail=<str>)` where the frontend expects a popup

A plain string in `detail` renders as the default error text. When an explicit popup is expected, use `detail={"message": "...", "show": True}`.

### No paired authorization test

`mock_http_bearer` (autouse) makes every test authorized. A regression where `HTTPBearer` is dropped from an endpoint still passes the suite. A test with the `no_auth_mock` marker expecting 401/403 is mandatory.

------------------------------------------------------------------------

## Related skills

- **`project-structure`** — layering, naming, mandatory checks; must be loaded **before** this skill.
- **`create-model`** — the previous step: creating the model and manager the endpoint will work with.
- **`backend-testing`** — the next step: writing tests for the new endpoint and service method.
- **`report-microservice`** — authorization specifics for the Raport ecosystem (Keycloak middleware, `request.user.id`).

End-to-end order for a new feature: `project-structure` → `create-model` → `generate-api-method` → `backend-testing` → `make lint` → `make test`.
