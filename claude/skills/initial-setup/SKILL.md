---
name: initial-setup
description: First-time setup of a microservice built from the FastAPI + SQLAlchemy template, plus on-demand extension of an already configured project with new infrastructure blocks (Kafka, Redis, Taskiq, Keycloak authentication). Used once when a new service starts, whenever a new subsystem has to be added, and as a health-check when the project is failing and every initial setting has to be re-verified. Optional configs and middleware live in this skill's assets/ directory and are copied into the project only on request.
---

# Initial Setup (FastAPI + SQLAlchemy)

## Purpose

The skill covers three scenarios:

1. **First-time setup** — take a fresh clone of the template to a working service with a correctly configured PostgreSQL database, `.env`, linters and tests.
2. **Service extension** — plug a new infrastructure service (Kafka, Redis, Taskiq, Keycloak) into an existing project. By default the template ships with PostgreSQL only. Every other config lives in this skill's `assets/` directory and is copied into `src/config/` / `src/middlewares/` **on user request**.
3. **Health-check** — the project is failing and it is unclear where `.env`, `settings.py` and the actual environment disagree. The skill walks through every setting top-down and flags mismatches.

The skill does not rebuild layers of an already working project (models, managers, endpoints) and never produces business logic — that is the job of `create-model` / `generate-api-method`.

## When to activate

- The user cloned the template and wants to "set up a new service".
- The repository still holds the template defaults (`PROJECT_TITLE="Start FastAPI service"`, `DB_NAME=template`, the single `User` model).
- The user asks to "plug in Kafka / Redis / Taskiq / Keycloak".
- The project fails to start, migrate or test and every initial setting has to be re-verified to locate the divergence.
- Direct triggers: "initial-setup", "set up the project", "enable <service>", "verify the project settings".

If none of the modes applies and the user actually needs a new feature or model, hand them off to `create-model` / `generate-api-method`.

------------------------------------------------------------------------

## Step 0 — Pick the mode

Before touching anything, ask the user: is this **first-time setup**, **adding a service**, or **a diagnostic pass**?

- **First-time setup** → walk through Step 1 to Step 7 in order.
- **Adding a service** → jump straight to Step 3 (extra services) or Step 4 (authorization), depending on the request.
- **Health-check** → follow every step as a checklist but do not change files without confirmation: find divergences first, then propose edits as a single list.

------------------------------------------------------------------------

## Step 1 — Core settings (`settings.py` ↔ `.env.example` ↔ `.env`)

The single source of truth for every environment variable is `src/config/settings.py` (class `AppConfig`). `.env.example` must **cover every field** with a short English comment; the developer creates `.env` locally from `.env.example`.

### Current inventory of `AppConfig` fields

| Field | Default | `.env` variable | Purpose |
| --- | --- | --- | --- |
| `project_title` | `"Start FastAPI service"` | `PROJECT_TITLE` | Swagger title |
| `project_host` | `"0.0.0.0"` | `PROJECT_HOST` | uvicorn bind host |
| `project_port` | `8000` | `PROJECT_PORT` | uvicorn bind port |
| `project_docs_version` | `"1.0.0"` | `PROJECT_DOCS_VERSION` | API version in Swagger |
| `project_docs_url` | `"/api/openapi"` | `PROJECT_DOCS_URL` | Swagger UI URL |
| `project_openapi_url` | `"/api/openapi.json"` | `PROJECT_OPENAPI_URL` | OpenAPI schema URL |
| `db_driver_name` | `"postgresql+asyncpg"` | `DB_DRIVER_NAME` | SQLAlchemy driver name |
| `db_host` | `"localhost"` | `DB_HOST` | PostgreSQL host |
| `db_port` | `"5432"` | `DB_PORT` | PostgreSQL port |
| `db_name` | `"template"` | `DB_NAME` | Database name |
| `db_user` | `"demo"` | `DB_USER` | Database user |
| `db_pass` | `"demo"` | `DB_PASS` | Database password |
| `db_show_queries` | `False` | `DB_SHOW_QUERIES` | Echo SQL to stdout (dev only) |
| `db_test_database_name` | `"template_test"` | `DB_TEST_DATABASE_NAME` | Test database name — `tests/conftest.py` reads it via `app_config` |

### What to verify / fix

1. Every `AppConfig` field appears in `.env.example` with a short English comment (via `#`).
2. `.env.example` holds only **safe placeholders** — no production passwords, no real tokens.
3. The user has a local `.env` with real values. `.env` is git-ignored (see `.gitignore`).
4. Whenever a new environment variable is added in any step, it **immediately** appears in both `AppConfig` and `.env.example` with a comment. Otherwise the next developer will not know it exists.
5. `.env.example` values are plain strings (no quotes); booleans are `true` / `false`.

### What to ask the user during first-time setup

- **Service slug** — Latin, kebab-case or snake_case (e.g. `booking-service`). Used in the Docker image name and in descriptions.
- **Human-readable name** — `PROJECT_TITLE` (e.g. `"Booking Service API"`).
- **API version** — `PROJECT_DOCS_VERSION`, default `1.0.0`.
- **Host / port** — `PROJECT_HOST` / `PROJECT_PORT`. Keep the defaults unless needed.
- **API prefix** — `/api/v1`. Changing it is **not recommended**: `src/main.py` mounts routers under this prefix.

------------------------------------------------------------------------

## Step 2 — PostgreSQL

PostgreSQL is wired up in the template **by default** — no extra setup is required. Verify:

1. `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASS` in `.env` point at a working database.
2. The user has `CREATE DATABASE` privilege (needed for the `drop_create_db` fixture in tests, see `backend-testing`).
3. `DB_TEST_DATABASE_NAME` is set for tests (typically `<DB_NAME>_test`).
4. `alembic upgrade head` runs without errors.

### What to ask the user

- Database connection parameters (host, port, name, user, pass).
- Test database name — default `<DB_NAME>_test`.

### What to do

- Fill `.env` with the user values.
- Run `make upgrade` to apply the initial migrations.
- Run `make test` and confirm the test database is recreated and the dumps load.

------------------------------------------------------------------------

## Step 3 — Extra infrastructure services (Kafka, Redis, Taskiq)

By default the template has **no** Kafka, Redis or Taskiq. Their assets live in `claude/skills/initial-setup/assets/` and are copied into the project **only on request**.

### 3.1 Shared procedure

Every service follows the same sequence:

1. **Ask the user** whether the service is needed and what for (topic consumption, cache, job queue, scheduler).
2. **Add dependencies** to `requirements.txt`.
3. **Add fields** to `AppConfig` (`src/config/settings.py`), list the new variables in `.env.example` with comments.
4. **Copy the assets** into `src/config/<service>/` (or `src/config/<service>.py` for single-file ones).
5. **Wire it into `src/main.py`** when the service must initialise at startup (Kafka consumer, Taskiq broker).
6. **Fill `.env`** with the user values.
7. **Verify** `make lint` and `make test` — existing tests must still pass.

### 3.2 Redis

**When to enable:** a cache, a lightweight shared queue, pub/sub, or Redis as the Taskiq backend.

**`AppConfig` field:**

```python
redis_url: str = "redis://localhost:6379"
```

**`.env.example`:**

```
# Redis
REDIS_URL=redis://localhost:6379  # Async Redis connection URL
```

**Dependencies** (`requirements.txt`):

```
redis==5.0.8
```

**Copy the assets:**

```bash
mkdir -p src/config
cp claude/skills/initial-setup/assets/redis/redis.py src/config/redis.py
```

Import: `from src.config.redis import redis` (the client is `aioredis.from_url(app_config.redis_url)`).

No explicit initialisation in `main.py` is required — the client is lazy and opens the connection on the first call.

### 3.3 Taskiq (distributed jobs + scheduler)

**When to enable:** background jobs (emailed reports, external API sync) or cron-like periodic tasks.

**Prerequisite:** Redis is already wired up — Taskiq uses it as broker and result backend.

**`AppConfig` field:**

```python
taskiq_redis_db: str = "0"
```

**`.env.example`:**

```
# Taskiq
TASKIQ_REDIS_DB=0  # Redis database index dedicated to Taskiq broker/results
```

**Dependencies:**

```
taskiq==0.11.8
taskiq-redis==1.0.2
taskiq-fastapi==0.3.2
```

**Copy the assets:**

```bash
mkdir -p src/config/taskiq
cp claude/skills/initial-setup/assets/taskiq/__init__.py src/config/taskiq/__init__.py
cp claude/skills/initial-setup/assets/taskiq/broker.py src/config/taskiq/broker.py
cp claude/skills/initial-setup/assets/taskiq/scheduler.py src/config/taskiq/scheduler.py
```

**The worker and the scheduler** run as separate processes. Typical commands (add them to `Makefile` or `RUN.sh` when needed):

```bash
taskiq worker src.config.taskiq.broker:taskiq_broker --fs-discover
taskiq scheduler src.config.taskiq.scheduler:scheduler
```

User tasks live in `src/tasks/` (the package already exists, empty). Tasks are registered via `@taskiq_broker.task`; imports are picked up by the worker's `--fs-discover` flag.

### 3.4 Kafka (producer + consumer)

**When to enable:** the project participates in an event bus (integration with 1C, ISUP, external partners).

**`AppConfig` fields:**

```python
kafka_addr: Optional[str] = None
kafka_sasl_username: Optional[str] = None
kafka_sasl_password: Optional[str] = None
kafka_security_protocol: Optional[str] = None
kafka_sasl_mechanism: Optional[str] = None
kafka_group_id: Optional[str] = None
```

**`.env.example`:**

```
# Kafka
KAFKA_ADDR=localhost:9092            # Comma-separated bootstrap servers
KAFKA_GROUP_ID=my-service            # Consumer group id
KAFKA_SECURITY_PROTOCOL=PLAINTEXT    # PLAINTEXT / SASL_SSL / SSL
KAFKA_SASL_MECHANISM=                # PLAIN / SCRAM-SHA-256 / SCRAM-SHA-512
KAFKA_SASL_USERNAME=                 # SASL login (empty for PLAINTEXT)
KAFKA_SASL_PASSWORD=                 # SASL password
```

**Dependencies:**

```
aiokafka==0.11.0
```

**Copy the assets:**

```bash
mkdir -p src/config/kafka
cp claude/skills/initial-setup/assets/kafka/__init__.py src/config/kafka/__init__.py
cp claude/skills/initial-setup/assets/kafka/consumer.py src/config/kafka/consumer.py
cp claude/skills/initial-setup/assets/kafka/producer.py src/config/kafka/producer.py
```

**Wire into `src/main.py`** (lifespan handlers for the consumer):

```python
import asyncio
from contextlib import asynccontextmanager

from src.config.kafka.consumer import consume_messages, kafka_consumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    await kafka_consumer.start()
    consumer_task = asyncio.create_task(consume_messages())
    yield
    consumer_task.cancel()
    await kafka_consumer.stop()


app = FastAPI(..., lifespan=lifespan)
```

The list of subscribed topics is `TOPICS_TO_READ` in `src/config/kafka/consumer.py`.

The producer is used through the `get_kafka_producer` FastAPI dependency in endpoints / services that publish events.

------------------------------------------------------------------------

## Step 4 — Authorization (Keycloak)

Authorization is **not** wired up in the template by default. The only variant this skill currently supports is **Keycloak (OIDC)**. Middleware and user-column assets live in `assets/keycloak/`.

### 4.1 What to ask the user

1. **Is authorization needed** on the project (yes / no). If no, skip Step 4.
2. **Auth provider** — Keycloak is the only supported option in this skill. Other variants (Basic, raw Bearer without a provider, a custom JWT factory) are out of scope here.
3. **Keycloak parameters:**
   - `KEYCLOAK_SERVER_URL` — Keycloak base URL (e.g. `https://sso.example.com/auth/`).
   - `KEYCLOAK_REALM` — realm name.
   - `KEYCLOAK_CLIENT_ID` — client id.
   - `KEYCLOAK_CLIENT_SECRET` — client secret.
   - `KEYCLOAK_VERIFY_SSL` — `true` / `false` (`false` for a dev instance with a self-signed certificate).

### 4.2 Add to `AppConfig`

```python
keycloak_server_url: Optional[str] = None
keycloak_realm: Optional[str] = None
keycloak_client_id: Optional[str] = None
keycloak_client_secret: Optional[str] = None
keycloak_verify_ssl: bool = True
```

### 4.3 Add to `.env.example`

```
# Keycloak authentication (optional — enable only when auth is required)
KEYCLOAK_SERVER_URL=https://sso.example.com/auth/  # Keycloak base URL
KEYCLOAK_REALM=my-realm                             # Keycloak realm name
KEYCLOAK_CLIENT_ID=my-service                       # Keycloak client id
KEYCLOAK_CLIENT_SECRET=                             # Keycloak client secret
KEYCLOAK_VERIFY_SSL=true                            # Disable for dev Keycloak with self-signed cert
```

### 4.4 Dependencies

```
python-keycloak==4.2.0
jwcrypto==1.5.6
```

### 4.5 Extend the `User` model

The middleware looks up a user by `keycloak_id`. Before copying the middleware into the project:

1. **Add the columns** to the `User` model using `assets/keycloak/user_columns_snippet.py` as the reference:
   - `keycloak_id: str | None` (unique, indexed) — identifier from the token's `sub` claim;
   - `first_name`, `last_name` — filled from the token on every login;
   - `is_admin`, `is_active` — local flags;
   - `last_login: datetime | None` — timestamp of the last successful sign-in.
2. **Add a method to `UserManager`:**
   ```python
   async def get_user_by_keycloak_id(
       self,
       keycloak_id: str,
       username: str | None = None,
       first_name: str | None = None,
       last_name: str | None = None,
       email: str | None = None,
       last_login: datetime | None = None,
   ) -> User | None:
       """Look up a user by keycloak_id and refresh profile fields from the token."""
       user = await self.db.scalar(
           select(User).where(User.keycloak_id == keycloak_id)
       )
       if user is None:
           return None
       # Soft-disabled accounts are rejected.
       if user.is_active is False:
           return None
       for field, value in (
           ("username", username),
           ("first_name", first_name),
           ("last_name", last_name),
           ("email", email),
           ("last_login", last_login),
       ):
           if value is not None:
               setattr(user, field, value)
       await self.db.commit()
       return user
   ```
3. **Generate a migration:**
   ```bash
   make migrate msg="add_keycloak_fields"
   ```
   Cross-check it against `assets/keycloak/migration_example.py`. Make sure indexes and `server_default` are in the migration (see `create-model`, section "Enum types need manual migration edits" — the same rules about `server_default` and index naming apply here).
4. **Run `upgrade → downgrade → upgrade`** locally to confirm the migration is symmetric.

### 4.6 Copy the middleware

```bash
cp claude/skills/initial-setup/assets/keycloak/keycloak_middleware.py src/middlewares/keycloak_middleware.py
```

The middleware ships in a **minimal** form: token validation, user load, profile refresh. The role model, default role assignment and contractor binding are Raport-ecosystem specifics that live in the `report-microservice` skill — they are **not** included here.

### 4.7 Wire the middleware into `src/main.py`

```python
from starlette.middleware.authentication import AuthenticationMiddleware

from src.middlewares.keycloak_middleware import KeycloakMiddleware

app.add_middleware(AuthenticationMiddleware, backend=KeycloakMiddleware())
```

After that every protected endpoint (`Depends(HTTPBearer())`) receives `request.user.id` pointing at the local `User` instance that the middleware loaded.

### 4.8 Public routes

At the very start add at least the following to `PUBLIC_ROUTES` inside `src/middlewares/keycloak_middleware.py`:

- `/api/v1/healthcheck`
- `/api/openapi`, `/api/openapi.json`, `/docs`, `/favicon.ico`

Extend the list as more public endpoints appear.

### 4.9 Tests

`tests/conftest.py` already provides `mock_http_bearer` with support for the `no_auth_mock` marker. To confirm the middleware is really enabled and guards the route:

1. Follow the standard paired test pattern for protected endpoints (see `backend-testing`).
2. Add a row with `keycloak_id="fake-keycloak-id"` to the local `dump_users.json` fixture so `UserManager.get_user_by_keycloak_id(...)` returns a user in integration tests.

------------------------------------------------------------------------

## Step 5 — Admin panel (SQLAdmin)

The admin panel is optional. Enable it only when the user **explicitly requests it**.

### 5.1 What to ask the user

1. **Is an admin panel needed** (yes / no)? If no, skip this step.
2. **Authentication method**: simple username + password from `.env` (default, no Keycloak required) or Keycloak `is_admin` flag (only when Keycloak is already configured in Step 4)?

### 5.2 Dependencies

Add to `requirements.txt`:

```
sqladmin==0.19.0
openpyxl==3.1.3
```

### 5.3 Bootstrap the skeleton

Create the following structure (empty `__init__.py` files where listed):

```
src/config/admin/
├── __init__.py
├── categories.py
├── config.py
├── custom_base.py
└── model_admin/
    ├── __init__.py
    └── base_admin.py
```

### 5.4 `categories.py`

Start with one constant per logical group; add more as models are created.

```python
USER_CATEGORY = "Users"
```

Category strings are **never** hardcoded inside a view class — always reference this module.

### 5.5 `model_admin/base_admin.py`

Copy this as-is. The search overrides support searching through related-model fields via dot notation (`"related.field"`) and multi-word search via `split_search_query`.

```python
from io import BytesIO
from re import compile, MULTILINE
from typing import Any, AsyncGenerator, List, Union

from openpyxl import Workbook
from openpyxl.styles import Font
from sqladmin import ModelView
from sqladmin.helpers import Writer, secure_filename, stream_to_csv
from sqlalchemy import Select, String, cast, or_
from starlette.responses import StreamingResponse
from urllib.parse import quote


class BaseAdmin(ModelView):
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    export_types = ["csv", "xlsx"]

    def _get_export_labels(self, export_prop_names: List[str]) -> List[str]:
        return [
            self.column_labels[item] if item in self.column_labels else item
            for item in export_prop_names
        ]

    async def export_data(self, data: List[Any], export_type: str = "csv") -> StreamingResponse:
        if export_type == "xlsx":
            return await self._export_xlsx(data)
        return await self._export_csv(data)

    async def _export_xlsx(self, data: List[Any]) -> StreamingResponse:
        wb = Workbook()
        ws = wb.active
        headers = self._get_export_labels(self._export_prop_names)
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in data:
            vals = [str(await self.get_prop_value(row, name)) for name in self._export_prop_names]
            ws.append(vals)
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        filename = quote(self.get_export_name(export_type="xlsx"))
        return StreamingResponse(
            content=buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )

    async def _export_csv(self, data: List[Any]) -> StreamingResponse:
        async def generate(writer: Writer) -> AsyncGenerator[Any, None]:
            yield writer.writerow(self._get_export_labels(self._export_prop_names))
            for row in data:
                vals = [str(await self.get_prop_value(row, name)) for name in self._export_prop_names]
                yield writer.writerow(vals)

        filename = secure_filename(self.get_export_name(export_type="csv"))
        return StreamingResponse(
            content=stream_to_csv(generate),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )

    trim_spaces_regex = compile(r"^\s+|\s+$", MULTILINE)
    column_search_outer_joins: List[str] = []

    def search_query(self, stmt: Select, term: str) -> Select:
        return self.search_query_custom(stmt, term, None)

    def search_query_custom(self, stmt: Select, term: str, joined: Union[set, None]) -> Select:
        if joined is None:
            joined = set()
        term = self.trim_spaces_regex.sub("", term)
        expressions = []
        for field in self._search_fields:
            model = self.model
            parts = field.split(".")
            for part in parts[:-1]:
                rel_class = getattr(model, part)
                model = rel_class.mapper.class_
                if part not in joined:
                    if part in self.column_search_outer_joins:
                        stmt = stmt.outerjoin(model)
                    else:
                        stmt = stmt.join(model)
                    joined.add(part)
            field = getattr(model, parts[-1])
            expressions.append(cast(field, String).ilike(f"%{term}%"))
        return stmt.filter(or_(*expressions))

    def split_search_query(self, stmt: Select, term: str) -> Select:
        terms = self.trim_spaces_regex.sub("", term).split(" ")
        joined: set = set()
        for term in terms:
            stmt = self.search_query_custom(stmt, term, joined)
        return stmt
```

### 5.6 `custom_base.py`

A `sqladmin.Admin` subclass with per-object delete-error handling. Start with this; extend later as needed.

```python
from typing import Any
from typing_extensions import override
from urllib.parse import parse_qsl

from fastapi import Response
from sqladmin import Admin
from sqladmin.authentication import login_required
from starlette.datastructures import MultiDict, URL
from starlette.exceptions import HTTPException
from starlette.requests import Request


class MyAdmin(Admin):
    @override
    @login_required
    async def delete(self, request: Request) -> Response:  # type: ignore[misc]
        """Delete route with per-object error handling."""
        await self._delete(request)

        referer_url = URL(request.headers.get("referer", ""))
        referer_params = MultiDict(parse_qsl(referer_url.query))

        identity = request.path_params["identity"]
        model_view = self._find_model_view(identity)

        params = request.query_params.get("pks", "")
        pks = params.split(",") if params else []
        for pk in pks:
            model = await model_view.get_object_for_delete(pk)
            if not model:
                raise HTTPException(status_code=404)
            try:
                await model_view.delete_model(request, pk)
            except Exception as exc:
                return Response(
                    content=f"Error during deletion of {model_view.name}: {exc}",
                    status_code=500,
                )

        url = URL(str(request.url_for("admin:list", identity=identity)))
        url = url.include_query_params(**referer_params)
        return Response(content=str(url))
```

### 5.7 Authentication

Pick one variant based on the answer in 5.1.

#### Variant A — simple username / password (no Keycloak)

**Add to `AppConfig`** (`src/config/settings.py`):

```python
from typing import Optional

admin_secret_key: str = "change-me-in-production"
admin_username: Optional[str] = None
admin_password: Optional[str] = None
```

**Add to `.env.example`:**

```
# Admin panel — simple auth (only when Keycloak is NOT used)
ADMIN_SECRET_KEY=change-me-in-production  # Secret key for session signing; must be changed before deploy
ADMIN_USERNAME=admin                       # Admin panel login
ADMIN_PASSWORD=change-me-in-production    # Admin panel password; must be changed before deploy
```

**`config.py`:**

```python
from fastapi import FastAPI
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src.config.admin.custom_base import MyAdmin
from src.config.postgres.db_config import async_engine
from src.config.settings import app_config

# Import and register views here as they are added — see the create-model skill.
# from src.config.admin.model_admin.user import UserAdmin


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if form["username"] == app_config.admin_username and form["password"] == app_config.admin_password:
            request.session.update({"token": "authenticated"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("token") == "authenticated"


def init_admin(app: FastAPI) -> None:
    auth_backend = AdminAuth(secret_key=app_config.admin_secret_key)
    admin = MyAdmin(app, async_engine, authentication_backend=auth_backend)
    # admin.add_view(UserAdmin)
```

#### Variant B — Keycloak `is_admin` flag

When Keycloak is already configured (Step 4), sqladmin's built-in auth is replaced by `AdminAccessMiddleware`. The full middleware implementation belongs to the `report-microservice` skill. Two mandatory adjustments here:

1. **Bypass Keycloak for admin routes** — add this check inside `authenticate` in `src/middlewares/keycloak_middleware.py` so the Keycloak backend does not intercept admin traffic (admin has its own auth flow):

```python
if conn.url.path.startswith("/admin"):
    return None
```

2. **`config.py` — omit the authentication backend:**

```python
from fastapi import FastAPI

from src.config.admin.custom_base import MyAdmin
from src.config.postgres.db_config import async_engine

# from src.config.admin.model_admin.user import UserAdmin


def init_admin(app: FastAPI) -> None:
    admin = MyAdmin(app, async_engine)  # Keycloak AdminAccessMiddleware handles auth
    # admin.add_view(UserAdmin)
```

### 5.8 Wire into `src/main.py`

Add **after** all `app.add_middleware(...)` and `app.include_router(...)` calls:

```python
from src.config.admin.config import init_admin

init_admin(app)
```

SQLAdmin mounts as a separate ASGI sub-application. Calling `init_admin` before middleware or routers causes ordering issues.

### 5.9 Verify

Open `http://<PROJECT_HOST>:<PROJECT_PORT>/admin`:
- **Variant A**: the sqladmin login page appears; sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
- **Variant B**: Keycloak redirects the browser; signing in as a user with `is_admin = true` opens the admin dashboard.

The sidebar is empty until the first `admin.add_view(...)` call is added in `config.py` (via the `create-model` skill). This is expected.

------------------------------------------------------------------------

## Step 6 — Developer environment

1. **Python 3.12+** installed; the virtual environment is ready:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. **Dependencies** installed:
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```
3. **pre-commit** activated:
   ```bash
   pre-commit install
   ```
4. **Docker / Docker Compose** — when the user runs the stack locally via compose.
5. **PostgreSQL** is up and reachable at the coordinates from `.env`.
6. (Optional) **Redis / Kafka / Keycloak** are up when the matching services were enabled in Steps 3–4.

For every missing piece give the user a concrete command — do not just say "install it".

------------------------------------------------------------------------

## Step 7 — Final verification

Run in this order:

```bash
make lint     # ruff + ruff-format + mypy
make upgrade  # alembic upgrade head
make test     # pytest with coverage
make run      # dev server via uvicorn
```

Then open `http://<PROJECT_HOST>:<PROJECT_PORT>/api/openapi` and confirm that:

- Swagger shows the correct `PROJECT_TITLE` and `PROJECT_DOCS_VERSION`.
- Every mounted router is listed.
- Protected endpoints (if Keycloak was configured) show the lock icon.

For a basic API smoke test, hit `GET /api/v1/healthcheck` (when it exists) or `GET /api/v1/user/1` (if the `User` example was kept).

------------------------------------------------------------------------

## Pre-handoff checklist

1. **`AppConfig`** lists every current field; each field has a default or is explicitly marked `Optional[...] = None`.
2. **`.env.example`** covers **every** field in `AppConfig` with a short English comment. `.env` exists locally and carries real values.
3. **PostgreSQL** is reachable, migrations applied, `make test` green.
4. **Redis / Kafka / Taskiq** are enabled when the user asked for them; configs are copied from `assets/`, fields are added to `AppConfig` and `.env.example`, dependencies are in `requirements.txt`.
5. **Keycloak** (when required): columns added to `User`, migration applied, middleware copied and wired into `src/main.py`, public routes listed in `PUBLIC_ROUTES`.
6. **SQLAdmin** (when requested): `src/config/admin/` skeleton is in place, `init_admin(app)` called last in `src/main.py`. Dependencies `sqladmin==0.19.0` and `openpyxl==3.1.3` in `requirements.txt`. For Variant A: `ADMIN_SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` in `AppConfig` and `.env.example`. For Variant B: `/admin` path excluded from Keycloak middleware.
7. **`requirements.txt`** reflects every new dependency.
7. **`make lint`** green.
8. **`make test`** green, coverage ≥ 70%.
9. **`make run`** brings the service up; Swagger opens and shows the correct title / version / routes.

------------------------------------------------------------------------

## Common mistakes

### `.env` and `.env.example` drift apart

A field was added to `AppConfig` but forgotten in `.env.example` — the next developer cloning the repo will not realise the value needs to be set. Rule: every change to `AppConfig` is accompanied by a line in `.env.example` with a comment.

### Secrets in `.env.example`

`.env.example` holds only placeholders (`KEYCLOAK_CLIENT_SECRET=`) or safe values (`DB_NAME=template`). Real passwords and tokens live only in the local `.env`, which is git-ignored.

### Taskiq enabled without Redis

The Taskiq broker and scheduler use Redis as their backend. Until Redis is up and `REDIS_URL` is filled in, the broker crashes on startup.

### Keycloak middleware enabled without extending the `User` model

`UserManager.get_user_by_keycloak_id(...)` fails with `AttributeError` — the `keycloak_id` column does not exist. Before enabling the middleware, **always** extend the model and apply the migration.

### A public endpoint still requires a token

The Keycloak middleware applies to every route, including Swagger and healthcheck. Add them to `PUBLIC_ROUTES` / `PUBLIC_ROUTE_PREFIXES` inside `src/middlewares/keycloak_middleware.py`.

### `init_admin` called before middleware or routers

SQLAdmin mounts as a separate ASGI sub-application. If `init_admin(app)` is called before `app.add_middleware(...)` or `app.include_router(...)`, the admin sub-app may not see the main app's middleware. Always call `init_admin(app)` **last** in `src/main.py`.

### Simple-auth credentials unchanged before deploy

The defaults `change-me-in-production` for `ADMIN_SECRET_KEY` and `ADMIN_PASSWORD` are placeholders. Deploying without changing them is a security risk. Always set real values in `.env` before the first deploy.

### Keycloak middleware intercepting admin routes (Variant B)

When Keycloak middleware is enabled and the `/admin` path prefix is not excluded, every admin request gets rejected with 401. Add `if conn.url.path.startswith("/admin"): return None` to the `authenticate` method in `src/middlewares/keycloak_middleware.py`.

### Editing skill assets directly

The files in `claude/skills/initial-setup/assets/` are **templates**, not runtime code. They are copied into the project and then edited inside `src/config/` / `src/middlewares/`. Change an asset itself only when the standard pattern for all future services on the template has to change.

------------------------------------------------------------------------

## Output format

The final response to the user contains:

1. The detected mode (first-time setup / adding a service / health-check) and the list of steps to walk through.
2. Step-by-step diffs for the affected files:
   - `src/config/settings.py` — new `AppConfig` fields;
   - `.env.example` — new lines with comments;
   - `requirements.txt` — new dependencies;
   - `src/config/<service>/` or `src/middlewares/` — the list of files copied from `assets/`;
   - `src/main.py` — lifespan and middleware wiring.
3. Commands the user has to run themselves:
   - dependency install;
   - `make migrate` + `make upgrade` when models changed;
   - `make lint` / `make test` / `make run` at the end.
4. Any outstanding questions to the user (e.g. waiting for the Keycloak realm / client secret).

------------------------------------------------------------------------

## Related skills

- **`project-structure`** — the layout of `src/config/`, `src/middlewares/`, `src/main.py`; loaded **before** this skill.
- **`create-model`** — when authorization requires adding or changing columns on the `User` model.
- **`backend-testing`** — tests after every new subsystem is enabled.
- **`report-microservice`** — the extended Keycloak flow for the Raport ecosystem (role model, contractor_code_1c, user upsert on first sign-in).

End-to-end order for launching a new service: `project-structure` → `initial-setup` → `create-model` → `generate-api-method` → `backend-testing` → `make lint` → `make test`.
