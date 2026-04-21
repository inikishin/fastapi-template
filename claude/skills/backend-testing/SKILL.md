---
name: backend-testing
description: Writing automated tests for the FastAPI + SQLAlchemy template using pytest, httpx.AsyncClient and a real PostgreSQL test database. The skill describes the fixtures shipped in tests/conftest.py (drop_create_db, async_test_session, client, async_session, mock_http_bearer), the generation and loading pipeline for tests/dump_data/, the tests/test_<layer>/test_<feature>/ folder layout, and the response contract defined in src/api/schemes.py. Coverage target is 70%.
---

# Backend Testing (pytest + FastAPI + PostgreSQL)

## Purpose

This skill helps write automated tests that:

- rely on the fixtures already provided by `tests/conftest.py` and **do not duplicate** them;
- run against a real PostgreSQL test database, which is recreated once per
  session from the Alembic migrations and **seeded from `tests/dump_data/`**;
- verify the typed response bodies guaranteed by the `@catch_all_exceptions`
  decorator and the `ResponseNNNSchema` classes in `src/api/schemes.py`;
- are launched via `make test`, with coverage collected automatically
  (target: 70%).

**Source of truth**: `tests/conftest.py`, `pytest.ini` and `.env.example`.
If the skill diverges from those files, fix the **skill**, not the files.

------------------------------------------------------------------------

## When to activate

- A new feature, endpoint, service, manager or helper → tests needed.
- A bug has been fixed → add a regression test.
- Before a refactor → freeze current behavior.
- Coverage has dropped below 70%.
- The user asks to «add tests», «cover X with tests», «write a test for Y».

------------------------------------------------------------------------

## What to ask the user

1. **Target under test** — endpoint (`GET /api/v1/...`), service (`UserInfoService.get_user_by_id`), manager (`UserManager.get_users_by_filters`), helper.
2. **Test level**:
   - *integration* — through `client` (AsyncClient) against the real test database;
   - *unit* — direct call with `async_session` (MagicMock).
   - If not specified — default: integration for endpoints, unit for services/managers/helpers.
3. **Test data**: is what already lives in `tests/dump_data/dumps/` enough, or is a new row/table required (see «Data dumps»)?
4. **Scenarios**: at least happy path + one negative scenario (404/400/422/500).
5. **Target coverage** — default 70%.

------------------------------------------------------------------------

## Template infrastructure (use, do not duplicate)

### Dependencies

`requirements-dev.txt` contains everything needed for tests and linters: `pytest`, `pytest-asyncio`, `pytest-cov`, `psycopg2-binary`, `httpx`, `pre-commit`. Install both runtime and dev dependencies in a single command:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### `.env` — dedicated test database name

```
DB_TEST_DATABASE_NAME=template_test
```

If the variable is missing, conftest falls back to `<DB_NAME>_test`. **The test database lives on the same PostgreSQL instance as the production one**, under a different name. It is recreated **from scratch** on every `pytest` run.

### `pytest.ini`

- `asyncio_mode = auto` — `async def test_...` works without `@pytest.mark.asyncio`.
- `asyncio_default_fixture_loop_scope = session` — required for session-scoped async fixtures (`async_test_session`, `client`).
- `--strict-markers` — new markers must be registered in `pytest.ini`.
- `--cov=src --cov-report html` — the HTML report is written to `htmlcov/index.html` on every run.
- Marker `smoke` — pre-commit subset.

### Fixtures in `tests/conftest.py`

| Name | Scope | Purpose | Hits DB? |
| --- | --- | --- | --- |
| `drop_create_db` | session | Recreates the test database, runs `alembic upgrade head`, loads dumps from `tests/dump_data/` | Yes |
| `async_test_session` | session | Real `AsyncSession` bound to the test database | Yes |
| `client` | session | `httpx.AsyncClient` wrapping the FastAPI `app`; traffic goes into the real test database | Yes (via app) |
| `async_session` | function | `MagicMock(spec=AsyncSession)` for unit tests | No |
| `mock_http_bearer` | autouse | Patches `HTTPBearer.__call__` to return a fake token. Disabled per-test via the `@pytest.mark.no_auth_mock` marker | — |

**Rules:**

- Integration tests do **not** need to pass an `Authorization` header — `mock_http_bearer` handles it automatically.
- `async_test_session` is one session for the whole run. Commits from one test are visible to the next. For isolated data, use a local fixture with `add()` + cleanup in the yield block (template below).
- Nested `conftest.py` files in subdirectories — only when genuinely needed. They may extend the base conftest but must not override the fixtures listed above.

### Commands

```bash
make test                                      # full run with coverage (html)
pytest tests/test_api/test_user/               # a single directory
pytest tests/test_api/test_user/test_user_api.py::test_get_user_by_id_returns_200
pytest -m smoke                                # smoke subset only
pytest --cov=src --cov-report term-missing     # missing lines in the console
```

------------------------------------------------------------------------

## Layout of the `tests/` directory

```
tests/
├── __init__.py
├── conftest.py                  # base fixtures — do not duplicate
├── dump_data/                   # test database seed data
│   ├── dump_data_setup.sql      # DISABLE TRIGGER ALL for every target table
│   ├── dump_data_after.sql      # ENABLE TRIGGER ALL for every target table
│   └── dumps/
│       └── dump_<table>.json    # one file per table
├── test_api/
│   └── test_<feature>/
│       ├── __init__.py
│       └── test_<endpoint>.py
├── test_services/
│   └── <feature>/
│       ├── __init__.py
│       └── test_<file>.py
├── test_managers/
│   ├── __init__.py
│   └── test_<entity>.py
└── test_tasks/                  # background tasks (if any)
    └── test_<task>.py
```

`src/` ↔ `tests/` mapping:

| Artifact in `src/` | Test path |
| --- | --- |
| `src/api/v1/<feature>/views.py` | `tests/test_api/test_<feature>/test_<endpoint>.py` |
| `src/services/<feature>/<file>.py` | `tests/test_services/<feature>/test_<file>.py` |
| `src/models/managers/<entity>.py` | `tests/test_managers/test_<entity>.py` |
| `src/utils/helpers.py` | `tests/test_utils/test_helpers.py` |

**The API version (`v1`) is not repeated in test paths.** Tests are grouped by feature.

Every test directory requires an empty `__init__.py`.

**Reference file**: `tests/test_api/test_user/test_user_api.py`.

------------------------------------------------------------------------

## Data dumps (`tests/dump_data/`)

### Principle: only the minimum data the tests actually need

**Do not** mirror the production database into `tests/dump_data/dumps/`. The dump holds **only the tables and only the rows** the tests reference:

- one or two happy-path rows per table,
- plus targeted rows for edge cases (nullable fields, boundary values, FK relationships that a specific test exercises).

Large dumps slow the suite, leak production data (PII, commercial info) into the repo, and turn debugging a failed test into archaeology. The rule is **every row in the dump must be justified by a specific test**. If you can remove a row and no test breaks — it should not be there.

Before committing new dumps, ask yourself: «which tests break if I delete this file / this row?». If the answer is «none» — delete it.

### How the loading pipeline works

Inside `drop_create_db` (session scope) the following runs:

1. Using `psycopg2`, connect to the `postgres` system database → `DROP DATABASE IF EXISTS` → `CREATE DATABASE` for the test DB.
2. `alembic upgrade head` — the empty database receives the current schema. The database name comes from `app_config.db_name`, which is switched to `_TEST_DB_NAME` at the very top of conftest.
3. `dump_data_setup.sql` → every table listed in the dumps is switched to `DISABLE TRIGGER ALL`.
4. For each `dumps/dump_<table>.json`:
   - read the array of objects;
   - build a TSV stream in `io.StringIO`, `null` → `\N`;
   - load it via `cursor.copy_from(stream, table, columns=fields)`.
5. `dump_data_after.sql` → `ENABLE TRIGGER ALL` is restored.

**JSON filename = table name**: `dump_<tablename>.json`. The table must exist in `src/models/dbo/models.py` (otherwise the migration will not create it and `copy_from` will fail).

### Format of `dump_<table>.json`

An array of objects; **every value is a string** (as it would appear after `COPY ... TO stdout`). NULL is written either as `null` (JSON) or `"\\N"` (string). Example for the `users` table:

```json
[
  {
    "id": "1",
    "username": "admin",
    "email": "admin@example.com",
    "phone": null
  }
]
```

The keys of the first object define the column list used by `COPY` — **every object in the file must share the exact same key set**. Key order = column order.

### How to generate a dump from a real database

A one-off procedure. The converter script **is not stored in the project**, it lives in this skill: `claude/skills/backend-testing/prepare_sample_dump_for_tests.py`. Copy it **temporarily** into `tests/dump_data/`, run it, then delete it.

```bash
# 1. Temporarily place the utility into tests/dump_data/
cp claude/skills/backend-testing/prepare_sample_dump_for_tests.py tests/dump_data/

# 2. Take a data-only dump of ONLY the required tables (narrow -t list).
#    Do not run pg_dump without -t — it would pull the whole database.
pg_dump -h HOST -U USER -d DB --data-only \
  -t users -t <other_table> \
  -f tests/dump_data/dump_data.sql

# 3. Convert into JSON + trigger SQL files
cd tests/dump_data
python prepare_sample_dump_for_tests.py

# 4. Trim the generated dumps/dump_<table>.json files by hand:
#    keep only the rows the tests actually need.

# 5. Remove temporary artefacts
rm dump_data.sql prepare_sample_dump_for_tests.py
```

Only `dumps/dump_<table>.json`, `dump_data_setup.sql` and `dump_data_after.sql` get committed. Neither the source `dump_data.sql` nor the script itself belong in `tests/dump_data/`.

### Adding a tiny dump by hand (without pg_dump)

When a test only needs a row or two and running pg_dump would be overkill:

1. Add the table name to `dump_data_setup.sql` and `dump_data_after.sql`:
   ```sql
   -- dump_data_setup.sql
   ALTER TABLE "public"."<table>" DISABLE TRIGGER ALL;
   -- dump_data_after.sql
   ALTER TABLE "public"."<table>" ENABLE TRIGGER ALL;
   ```
2. Create `dumps/dump_<table>.json` with rows (every value as a string, `null` for NULL).
3. Run `pytest` — the new dump is picked up on the next `drop_create_db`.

### Reference file

`tests/dump_data/dumps/dump_users.json` — minimal one-row example.

------------------------------------------------------------------------

## API integration tests (`client`)

Use the async `client` fixture from conftest; traffic reaches the real FastAPI `app` and the seeded test database.

### Template — happy path

```python
async def test_get_user_by_id_returns_200(client):
    response = await client.get("/api/v1/user/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
    }
```

### Template — negative scenario

```python
async def test_get_user_by_id_not_found(client):
    response = await client.get("/api/v1/user/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "404"
    assert "User not found" in body["message"]
```

### Rules

- Test is `async def`, no `@pytest.mark.asyncio`.
- Request is `await client.<method>(...)`.
- Assert both `status_code` and the response body. For 4xx/5xx always check the `code` and `message` fields — they are guaranteed by `@catch_all_exceptions` from `src/utils/helpers.py`.
- Do not pass an `Authorization` header — `mock_http_bearer` is autouse.
- Pull test data from the dumps; if what you need is missing, see the local-fixture section below.

### Local fixture with create + cleanup

When a needed row is not in the dumps and you would rather not bloat the global dump:

```python
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.dbo.models import User


@pytest.fixture
async def extra_user(async_test_session: AsyncSession):
    user = User(id=42, username="temp", email="temp@example.com")
    async_test_session.add(user)
    await async_test_session.commit()

    yield user

    await async_test_session.delete(user)
    await async_test_session.commit()


async def test_returns_temp_user(client, extra_user):
    response = await client.get(f"/api/v1/user/{extra_user.id}")

    assert response.status_code == 200
    assert response.json()["username"] == "temp"
```

Rationale: `async_test_session` is session-scoped, so changes are visible to every subsequent test. The local cleanup after `yield` guarantees that inserted rows do not leak into neighbouring tests.

------------------------------------------------------------------------

## Service unit tests

A service composes managers. In unit tests the manager is replaced with an `AsyncMock`.

```python
from unittest.mock import AsyncMock

from src.models.dbo.models import User
from src.services.user.info import UserInfoService


async def test_get_user_by_tg_chat_id_returns_first(async_session):
    service = UserInfoService(db=async_session)
    service.user_manager = AsyncMock()
    service.user_manager.get_users_by_filters.return_value = [
        User(id=1, username="a", email="a@a"),
        User(id=2, username="b", email="b@b"),
    ]

    result = await service.get_user_by_tg_chat_id("12345")

    assert result.id == 1
    service.user_manager.get_users_by_filters.assert_awaited_once_with(tg_chat_id="12345")


async def test_get_user_by_tg_chat_id_returns_none_when_empty(async_session):
    service = UserInfoService(db=async_session)
    service.user_manager = AsyncMock()
    service.user_manager.get_users_by_filters.return_value = []

    assert await service.get_user_by_tg_chat_id("12345") is None
```

Rules:

- Instantiate the service directly; `async_session` from conftest is a mock and never hits the database.
- Replace the manager by attribute assignment: `service.<name>_manager = AsyncMock()`.
- Assert both the result and the manager call (`assert_awaited_once_with(...)`).
- Tests are `async def`, no decorators.

------------------------------------------------------------------------

## Manager unit tests

Tested with the `async_session` fixture.

### Method using `session.get`

```python
from unittest.mock import AsyncMock

from src.models.dbo.models import User
from src.models.managers.user import UserManager


async def test_get_user_by_id_found(async_session):
    expected = User(id=1, username="x", email="x@x")
    async_session.get = AsyncMock(return_value=expected)

    manager = UserManager(db=async_session)
    result = await manager.get_user_by_id(1)

    assert result is expected
    async_session.get.assert_awaited_once_with(User, 1)
```

### Method using `session.execute` + `scalars().all()`

```python
from unittest.mock import MagicMock


async def test_get_users_by_filters(async_session):
    users = [User(id=1, username="x", email="x@x")]

    scalars = MagicMock()
    scalars.all.return_value = users
    result_proxy = MagicMock()
    result_proxy.scalars.return_value = scalars
    async_session.execute.return_value = result_proxy

    manager = UserManager(db=async_session)
    found = await manager.get_users_by_filters(username="x")

    assert found == users
    async_session.execute.assert_awaited_once()
```

### When a manager must be tested against the real database

If a method relies on non-trivial SQL, relationship filtering, `joinedload`, etc. — write an integration test with `async_test_session`:

```python
async def test_get_user_by_id_from_real_db(async_test_session):
    manager = UserManager(db=async_test_session)

    user = await manager.get_user_by_id(1)

    assert user is not None
    assert user.username == "admin"
```

Such a test relies on the data from `dump_users.json`.

------------------------------------------------------------------------

## Errors and `@catch_all_exceptions`

The decorator in `src/utils/helpers.py` catches `RequestValidationError`, `ValidationError`, `HTTPException`, `ClientDisconnect` and any unexpected exception, turning them into a `JSONResponse` with a `ResponseNNNSchema` body. Tests exploit this:

| Scenario | How to trigger | Status | Body fields |
| --- | --- | --- | --- |
| Invalid path/query | `str` instead of `int` | 422 | `code`, `message`, `details` |
| Invalid request body | Miss a required field | 400 | `code`, `message`, `details` |
| Business not-found | Service returns `None` → `HTTPException(404)` | 404 | `code`, `message` |
| Unexpected failure | Service raises an exception | 500 | `code`, `message` |

------------------------------------------------------------------------

## Authorization

By default `mock_http_bearer` (autouse) feeds every test a fake Bearer token, so protected endpoints are reachable without a real `Authorization` header. To verify that authorization is **actually enabled** on an endpoint, the mock has to be disabled per-test.

### Rule: a paired test for every protected endpoint

If an endpoint requires authorization (declares `Depends(HTTPBearer())` or relies on an auth middleware), it **must ship with two tests**:

1. **Authorized scenario** → `200` (or another success code).
2. **Unauthorized scenario** → `401` (or `403`) with a typed body.

This guards against a regression where, during a refactor, the `HTTPBearer()` dependency is inadvertently dropped from the endpoint — without the paired test, such a change would slip through unnoticed.

For endpoints that are **deliberately open** (healthcheck, public dictionaries), the pair is not required — a single positive test is enough.

### Template — authorized scenario

Nothing extra is required, `mock_http_bearer` autouse already supplies the token:

```python
async def test_get_user_by_id_authenticated(client):
    response = await client.get("/api/v1/user/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
```

### Template — unauthorized scenario

Tag the test with the `no_auth_mock` marker — the `mock_http_bearer` fixture skips the patch and the real `HTTPBearer` runs:

```python
import pytest


@pytest.mark.no_auth_mock
async def test_get_user_by_id_unauthenticated(client):
    response = await client.get("/api/v1/user/1")

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "401"
```

The marker is registered in `pytest.ini` (`no_auth_mock: disable autouse HTTPBearer mock ...`). Use it only for tests that check the unauthenticated flow.

### What we do NOT check here

- **Token validity** (signature, expiry, issuer, roles) — that is the responsibility of the security module / middleware of the service. These checks do not belong in the template layer; they will appear in the `report-microservice` skill and live alongside the auth module.
- **Roles / permissions** — likewise, tested on the module that implements the role check, not on every endpoint.

### When an endpoint uses data from the token in business logic

If the endpoint extracts `user_id` from `HTTPAuthorizationCredentials` and feeds it into the logic, mock the **token-parsing dependency** (via `app.dependency_overrides`), not `HTTPBearer` itself. Keep `mock_http_bearer` enabled and inject the desired user through a dependency override.

------------------------------------------------------------------------

## Requirements and conventions

- **Isolation.** Tests must not depend on execution order. Any writes into `async_test_session` go through a local fixture with cleanup.
- **AAA.** Arrange / Act / Assert — the sections are explicitly visible.
- **Test names.** `test_<subject>_<scenario>_<expected>` (e.g. `test_get_user_by_id_not_found`).
- **One test = one behavior.** Three unrelated assertions → three tests.
- **Happy path + negative scenario** — minimum per public method/endpoint.
- **Async tests** — `async def`, no `@pytest.mark.asyncio`.
- **Fixtures from conftest** — use them; do not duplicate or override.
- **Service/manager tests** run against `async_session` (mock) — never touch the real database.
- **Integration tests** use `client` and/or `async_test_session` — dumps provide the data.
- **New dumps** — only for data actually required by a test; do not commit the raw `dump_data.sql`.
- **Secrets and tokens** — never hardcoded.
- **`smoke` marker** — reserved for critical happy paths of key endpoints.

------------------------------------------------------------------------

## Coverage

- **Project-wide target**: 70% (lines and branches).
- Report — `htmlcov/index.html` after `make test`.
- Console report with uncovered lines: `pytest --cov=src --cov-report term-missing`.
- If a module drops below 70% — add tests or justify it in the PR.
- For new code the same 70% baseline applies. Higher is welcome.

------------------------------------------------------------------------

## Pre-PR checklist

1. Path and file name: `tests/test_<layer>/test_<feature>/test_<source_stem>.py`.
2. Fixtures from `tests/conftest.py` are reused, not duplicated.
3. Async tests are `async def` without decorators.
4. Each endpoint has at least one happy path and one failure case.
5. If the endpoint is protected by authorization — it has **both** an authorized test **and** an unauthorized one (the latter with `@pytest.mark.no_auth_mock` → expected 401/403).
6. Response body is asserted (not only `status_code`); for 4xx/5xx — `code` / `message` fields.
7. New database rows are created either through a local fixture with cleanup **or** by extending `tests/dump_data/dumps/`.
8. The raw `dump_data.sql` is not committed; `dump_data_setup.sql` and `dump_data_after.sql` cover every target table.
9. `make test` is green, coverage ≥ 70%.
10. `make lint` passes.

------------------------------------------------------------------------

## Common issues

### A test only fails when run with others

Residual changes in `async_test_session` from a neighbour test. Use a local fixture with cleanup in the `yield` block.

### `RuntimeError: Event loop is closed`

Fixture scopes mismatch. `pytest.ini` must set `asyncio_default_fixture_loop_scope = session`. Do not call `asyncio.run()` from inside a test.

### `psycopg2.OperationalError: database "template_test" does not exist`

`drop_create_db` did not run. Check: PostgreSQL is up, the user has `CREATE DATABASE` permission, `.env` has `DB_HOST/DB_PORT/DB_USER/DB_PASS` and `DB_TEST_DATABASE_NAME`.

### `psycopg2.errors.UndefinedTable: relation "<table>" does not exist`

`dump_<table>.json` exists but the model/migration does not. First create the ORM model, generate a migration, make sure `alembic upgrade head` succeeds on an empty database, then rerun the tests.

### `psycopg2.errors.InvalidTextRepresentation: invalid input syntax for type ...`

The string representation in `dump_<table>.json` does not match the column type (e.g. `"true"` for a `boolean` should be `"t"` or `"true"`; timestamps must be `YYYY-MM-DD HH:MM:SS+03`). The easiest fix is to sample a valid representation via `pg_dump --data-only` on a working database.

### An endpoint test returns 500 instead of the expected 4xx

Verify that the endpoint is wrapped with `@catch_all_exceptions` and that `get_responses(ResponseGroup.ALL_ERRORS)` is spread into the `responses=` mapping.

### `401 / 403` on a protected endpoint

`mock_http_bearer` did not apply. Common causes: a nested `conftest.py` overrode the fixture; `autouse=False` was set by mistake.

### `AttributeError: 'coroutine' object has no attribute ...`

A plain `MagicMock` was used where `AsyncMock` is required. For awaitables use `AsyncMock`; return a plain `MagicMock` representing the result object via `.return_value`.

------------------------------------------------------------------------

## Reference files in the template

- `tests/conftest.py` — all base fixtures and the `app_config.db_name` override.
- `tests/dump_data/dump_data_setup.sql` / `dump_data_after.sql` — DISABLE/ENABLE TRIGGER ALL.
- `tests/dump_data/dumps/dump_users.json` — minimal dump example.
- `claude/skills/backend-testing/prepare_sample_dump_for_tests.py` — one-off `pg_dump → JSON` converter. Not stored in the project; copied into `tests/dump_data/` only while preparing a dump.
- `tests/test_api/test_user/test_user_api.py` — endpoint integration test.
- `src/api/v1/user/views.py` — endpoint using `@catch_all_exceptions` + `get_responses`.
- `src/services/user/info.py` — service composing a manager.
- `src/models/managers/user.py` — CRUD manager.
- `src/utils/helpers.py` — `catch_all_exceptions`, `get_responses`, `get_pagination_info`.
- `src/api/schemes.py` — `ResponseNNNSchema`, `ResponseGroup`, `RESPONSE_SCHEMAS`.
