---
name: report-microservice
description: Connects a microservice built from this template to the Raport ecosystem — installs an HTTP client for the main service, wires in Keycloak password-grant authentication via a technical service account (no token caching), and ships a curated reference for 32 GET endpoints grouped into four entity chains (Project→Floor, Contractor→Contract, Work Set→Work, Position). The presence of the src/external/report/ package marks the project as part of the Raport ecosystem. The skill copies the client from assets/report/ into the project only on request.
---

# Report Microservice (Raport ecosystem integration)

## Purpose

The skill solves one task: **plug a microservice into the Raport ecosystem**. After it runs, the project ends up with:

- `src/external/report/` — the HTTP client for the main Raport service;
- a set of environment variables in `AppConfig` / `.env.example` that were not in the bare template;
- an `httpx` dependency in `requirements.txt` when it was not already there;
- a curated API reference — `src/external/report/reference_api.md` (a copy of the asset) kept next to the client.

The skill **does not** write business logic (how the service uses Raport data) and **does not** configure the microservice's own Keycloak authentication — those belong to `initial-setup` and to the business-level skills.

The marker "this project is already plugged into Raport" is **the existence of the `src/external/report/` package** with a non-empty `client.py`. When missing — the skill offers to install it. When present — it switches into "update the reference" / "add a method" / "diagnose" mode.

## When to activate

- The user says "this microservice will live inside Raport" / "plug in Raport" / "I need a client for the main service".
- During `initial-setup` the user answered that the ecosystem is Raport.
- A `reference_api.md` / `client.py` update is needed after changes in the main API.
- A new reference endpoint has to be added to the client (a new handler in Raport).
- Diagnostics: the client crashes, authentication fails, or an unexpected HTTP code comes back.

If the user simply asks to "write logic that pulls projects from Raport" — run this skill first (install the client when it is missing), then go back to regular `generate-api-method` / service work.

------------------------------------------------------------------------

## Step 0 — Pick the mode

1. **Project is not plugged in yet** (no `src/external/report/client.py`): walk through Steps 1–5 in full.
2. **Project is plugged in**, a new endpoint has to be added: jump to Step 4 (updating `client.py` + `reference_api.md`).
3. **Diagnostics**: walk through the final checklist — inspect `.env`, the Keycloak settings, reachability of `REPORT_API_URL`, the behaviour of `get_report_access_token()`.

------------------------------------------------------------------------

## Step 1 — Preliminary checks

Before copying any asset, confirm that the baseline Keycloak block is already configured (`initial-setup`, Step 4), even if the microservice's own API is still public:

- `AppConfig` has `keycloak_server_url`, `keycloak_realm`, `keycloak_verify_ssl`.
- `.env.example` lists these fields.
- The Raport client uses **the same Keycloak `server_url` and `realm`** as the service's own API authentication — that is the ecosystem convention.

If the Keycloak block is missing, **stop** and hand control over to `initial-setup` → Step 4 (Keycloak). Come back here after `KEYCLOAK_SERVER_URL` / `KEYCLOAK_REALM` are set in `.env`.

------------------------------------------------------------------------

## Step 2 — What to ask the user

1. **Base URL of the main Raport service** — without `/api/v1` (the client appends the path itself). Example: `https://raport.example.com`.
2. **Service account client id** — `REPORT_KEYCLOAK_CLIENT_ID` (e.g. `booking-service-sa`).
3. **Service account client secret** — `REPORT_KEYCLOAK_CLIENT_SECRET`. Keep `.env.example` empty; put the real value only into the local `.env`.
4. **Technical user's login** — `REPORT_KEYCLOAK_USERNAME`.
5. **Technical user's password** — `REPORT_KEYCLOAK_PASSWORD`. Only in `.env`, never in `.env.example`.

The Keycloak `server_url` / `realm` used by the service account and by the project's own Keycloak middleware are identical. No separate `REPORT_KEYCLOAK_SERVER_URL` / `REPORT_KEYCLOAK_REALM` variables.

When the user does not yet know a value, record it as an open question but **still** copy the assets and bring the setup to the state "only `.env` is left to fill in".

------------------------------------------------------------------------

## Step 3 — Plugging the client in

### 3.1 Add fields to `AppConfig` (`src/config/settings.py`)

```python
# Raport ecosystem — external data source
report_api_url: Optional[str] = None
report_keycloak_client_id: Optional[str] = None
report_keycloak_client_secret: Optional[str] = None
report_keycloak_username: Optional[str] = None
report_keycloak_password: Optional[str] = None
```

### 3.2 Add a block to `.env.example`

```
# Raport ecosystem (external data source)
REPORT_API_URL=https://raport.example.com              # Base URL of the main Raport service (no /api/v1)
REPORT_KEYCLOAK_CLIENT_ID=my-service-sa                # Keycloak client id for the service account
REPORT_KEYCLOAK_CLIENT_SECRET=                         # Keycloak client secret (fill in .env, not here)
REPORT_KEYCLOAK_USERNAME=my_service_technical_user     # Technical Keycloak user for password-grant auth
REPORT_KEYCLOAK_PASSWORD=                              # Technical user's password (fill in .env, not here)
```

Every line has an English comment (the general `.env.example` rule from `initial-setup`).

### 3.3 Add the dependency

If `httpx` is not yet in `requirements.txt`, add it. It already lives in `requirements-dev.txt`, but production needs a separate line:

```
httpx==0.28.1
```

### 3.4 Copy the client assets

```bash
mkdir -p src/external/report
cp claude/skills/report-microservice/assets/report/__init__.py src/external/report/__init__.py
cp claude/skills/report-microservice/assets/report/auth.py      src/external/report/auth.py
cp claude/skills/report-microservice/assets/report/client.py    src/external/report/client.py
cp claude/skills/report-microservice/assets/report/reference_api.md src/external/report/reference_api.md
```

What lands in the project:

- **`auth.py`** — the `get_report_access_token()` function. It sends `POST {keycloak_server_url}/realms/{realm}/protocol/openid-connect/token` with `grant_type=password`, returns the `access_token`. **No caching** — every client call hits Keycloak again. Errors surface as the dedicated `ReportAuthError` exception.
- **`client.py`** — the `ReportClient` class. The constructor reads `report_api_url` from `AppConfig`. The low-level `_request(method, path, params=None)` obtains a token, sets the `Authorization: Bearer ...` header, sends the request via `httpx.AsyncClient`, and raises `ReportApiError(status, body)` on non-2xx responses. On top of `_request` there are **32 methods** covering the entity chains (see Step 4).
- **`reference_api.md`** — a short reference covering all 32 endpoints. Think of it as the cheat-sheet: client method name, path, path parameters, non-obvious query parameters, response schema name.
- **`__init__.py`** — re-exports `ReportClient` so consumers write `from src.external.report import ReportClient`.

### 3.5 Verify

```bash
make lint
make test
```

If `mypy` complains about missing fields in `AppConfig`, the Step 3.1 changes were probably skipped.

Manual smoke test — start the service and, inside any service, run:
```python
from src.external.report import ReportClient
client = ReportClient()
print(await client.list_projects(per_page=1))
```
and confirm the token is obtained, the request goes out, and the response is `{"data": [...], "pagination": {...}}`.

------------------------------------------------------------------------

## Step 4 — Adding a new endpoint

When the main Raport API exposes a new handler that the project wants to consume:

1. **Pin the contract:** `WebFetch {report_api_url}/api/openapi.json`. Find the path and HTTP method, note the path / query parameters and the response schema name (`$ref` in `responses.200`).
2. **Pick the chain** the new entity belongs to (Project chain, Contractor chain, Work chain, Position) — or introduce a new one when it really is new.
3. **Add a method to `client.py`:**
   - name: `<verb>_<entity>[_<by_parent>]`. Prefixes: `list_` for list endpoints, `get_` for single objects / structural views;
   - body: a single `await self._request("GET", "/api/v1/...", params=params)`;
   - required path parameters go into the signature as typed `UUID` arguments;
   - everything else is passed through `**params: Any`.
4. **Add a row to `reference_api.md`** under the matching chain table:
   - `client method`, `GET path`, path params, extra query params (anything that is **not** `search`/`page`/`per_page`/`order_by`), response schema name.
   - If the endpoint deviates from the standard envelope (no pagination, different shape), call it out in the "Extra query params" column or as a plain-text remark.
5. **Tests** (per `backend-testing`): a unit test on the consumer service with `AsyncMock` covering `ReportClient.<new_method>`. No integration test against the live Raport — that is out of our area of responsibility.
6. `make lint` and `make test`.

**Do not** try to autogenerate the whole client from `openapi.json` — methods are added one at a time, as demand arises.

------------------------------------------------------------------------

## Step 5 — Picking the data strategy

Before writing the service, the developer **explicitly** picks one of two strategies (or a combination) for every entity pulled from Raport. The decision is the feature author's, not the agent's. The skill must surface the question and capture the answer before any code is generated.

### Strategy A — on-demand proxy

The service reacts to the user's request by `await`-ing a call on `ReportClient` and returning whatever comes back.

- **Pros:** always-fresh data, no local tables, no Taskiq, no background jobs.
- **Cons:** response time grows by the round-trip to Raport plus fetching a Keycloak token (no cache — every call). The service is only as available as Raport is. No SQL joins against local tables are possible.
- **Good for:** rarely used reference endpoints, UI lookups, one-off checks, anything where "liveness" of data is critical (status polling, for example).

**Template-level requirements:**
- `ReportClient` (already plugged in).
- A new service / method that calls the relevant client method.
- A Pydantic schema for the response on the consumer side, when typing is desired.
- No local tables, no Taskiq.

### Strategy B — scheduled synchronisation (pull into local tables)

A scheduled background job uses `ReportClient` to pull entities from Raport, stores them in the microservice's own tables, and from then on API endpoints operate against the local database.

- **Pros:** fast responses, resilience against Raport outages, SQL joins with local tables, room for local enrichment (computed columns, flags).
- **Cons:** a sync lag — new data arrives with a delay roughly equal to the job interval. Deletions / renames / soft-delete must be designed. The microservice's DB grows.
- **Good for:** frequently requested reference data, entities that take part in SQL joins, data that must remain available during Raport outages.

**Template-level requirements:**
- `create-model` → local table for the entity plus `<Entity>Manager` (usually a `raport_id: str` unique-indexed column as the remote identifier, plus whatever business-specific fields).
- `initial-setup` (Steps 3.2–3.3) — when missing, plug in **Redis** and **Taskiq** (broker + scheduler).
- `src/tasks/sync_<entity>.py` — a Taskiq job that paginates through `ReportClient.list_*` and calls `<Entity>Manager.bulk_upsert(data, key_field="raport_id", update_fields=[...])` into the local table.
- A **soft-delete policy:** either an `is_active` flag on the local model (set to `False` when a `raport_id` disappears from the Raport feed), or hard deletion. The choice is domain-specific and must be discussed explicitly.
- **Schedule:** a label such as `@taskiq_broker.task(schedule=[{"cron": "*/15 * * * *"}])` (or equivalent). The interval is business-driven — frequently used references every 15 minutes, heavy ones once a day at night.
- **Monitoring:** log every run, the upsert count, and errors. On failure — raise an alert (Sentry / Telegram when configured).

### Hybrid

Some references are cached locally (hot entities involved in joins), others are pulled on demand (rare, large, or real-time-sensitive). Inside the service both paths are visible in the method layout.

### Strategy selection checklist

The agent asks these questions the first time it touches an entity and records the answers in the plan before generating code.

1. **How often** will the service fetch this data? Rarely → proxy. Frequently → sync.
2. **How critical is freshness?** Real-time is required → proxy. An X-minute / X-hour lag is acceptable → sync with an interval ≤ X.
3. **Are joins with local tables required?** Yes → sync (a SQL join is impossible without the local copy). No → proxy is fine.
4. **What happens when Raport is down?** A 503 is acceptable → proxy. The service must stay up on stale data → sync.
5. **What volume of data is involved?** A huge rarely used dataset → proxy (syncing is expensive). Moderate and frequently used → sync.

When three out of five answers point at sync, pick strategy B; otherwise pick A. Ties resolve in favour of proxy — it is simpler and cheaper to maintain.

### Recording the decision in code

Regardless of the outcome, capture it **in the service docstring**:

```python
class ContractorsService(BaseService):
    """
    Data strategy: on-demand proxy via ReportClient.

    Contractors are fetched from Raport on every user request. No local mirror.
    Rationale: endpoint is rarely used, freshness matters, join with local tables
    is not required.
    """
```

or

```python
class ProjectsService(BaseService):
    """
    Data strategy: scheduled sync into the `projects` table.

    A Taskiq job `src/tasks/sync_projects.py` runs every 15 minutes and upserts
    the full Raport project list. Lag tolerance: 15 minutes.
    """
```

That way the next developer understands, from a single docstring, where the data comes from and what surprises to expect.

------------------------------------------------------------------------

## Step 6 — Using the client in services

The client is consumed by **services** (`src/services/<feature>/<file>.py`), never by routers directly. The standard pattern:

```python
from src.external.report import ReportClient
from src.services.common import BaseService


class SomeService(BaseService):
    def __init__(self, db, report_client: ReportClient | None = None):
        self.db = db
        self.report_client = report_client or ReportClient()

    async def collect_project_contractors(self, project_id):
        """Combine a local query with a fresh contractor list from Raport."""
        remote = await self.report_client.list_project_contractors(project_id)
        # ... merge with local data via self.<something>_manager ...
        return remote
```

Rules:

- Create the client **once**, in the service constructor (default argument `ReportClient()` or proper DI). Do not instantiate it per call — `httpx.AsyncClient` is already short-lived inside `_request`, and the `ReportClient` object itself is stateless and cheap.
- In tests, replace `report_client` with `AsyncMock(spec=ReportClient)` — see `backend-testing`.
- The response type is currently `dict`. When typing is needed, the consumer service defines its own Pydantic schema (in `src/api/v1/<feature>/schemes.py` or `src/services/<feature>/schemes.py`) and calls `.model_validate(raw)`. Pydantic models do not belong to the shared client so that the client is not tied to a specific Raport revision.
- The service **does not catch** `ReportApiError` for no reason — let it bubble up to the router where `@catch_all_exceptions` will handle it. Catch it only when a meaningful fallback exists.

------------------------------------------------------------------------

## Pre-handoff checklist

1. **Marker.** `src/external/report/` contains `__init__.py`, `auth.py`, `client.py`, `reference_api.md`.
2. **Configuration.** `AppConfig` carries five `report_*` fields. `.env.example` describes all five with comments. `.env` holds real values.
3. **Keycloak base.** `keycloak_server_url`, `keycloak_realm`, `keycloak_verify_ssl` are already set (from `initial-setup` → Step 4). No separate `REPORT_KEYCLOAK_SERVER_URL` / `REPORT_KEYCLOAK_REALM` variables exist.
4. **Dependencies.** `httpx` is in `requirements.txt`. Other libraries (`keycloak`, `python-keycloak`) are **not needed** — auth works through `httpx` directly.
5. **Client.** `ReportClient` is imported from `src.external.report`. Every one of the 32 methods is present; no duplicates. Method names match the "Client method" column in `reference_api.md`.
6. **Reference.** `src/external/report/reference_api.md` is in sync with `client.py`: every table row maps to a client method and every client method shows up in the table.
7. **No token cache.** `auth.py` does not keep the `access_token` between calls.
8. **Explicit strategy.** For every entity pulled from Raport the proxy / sync / hybrid choice is captured in the service docstring, so it does not get lost during review.
9. **Sync strategy, when picked,** is backed by concrete artefacts: a local table and manager via `create-model`; Redis + Taskiq enabled via `initial-setup`; a Taskiq job in `src/tasks/sync_<entity>.py` with an explicit schedule; a soft-delete policy agreed with the user.
10. **Tests.** Services using `ReportClient` are covered by unit tests with a mocked client. Sync jobs have their own tests (mapping Raport response → upsert).
11. `make lint` green.
12. `make test` green, coverage ≥ 70%.

------------------------------------------------------------------------

## Common mistakes

### 401 from Keycloak

`get_report_access_token()` raises `ReportAuthError`. Usual causes: wrong `client_secret`, disabled technical user, `grant_type=password` forbidden at the realm level. Check the Keycloak admin console: confidential client, service account enabled, password policy not blocking the user.

### 403 from Raport on a specific endpoint

The client obtained a token, but the main Raport service refused access. The technical user lacks the required role or is not attached to the project. The fix is not in code — it is on the Keycloak admin side: grant the user a role that allows `read` on the needed references.

### `ConnectTimeout` / `ReadTimeout`

Either `REPORT_API_URL` points at the wrong place, or the main service is down. Check with `curl -s -o /dev/null -w "%{http_code}\n" {REPORT_API_URL}/api/openapi.json`.

### Someone introduced a token cache "to make it faster"

That is a separate design decision, not a template standard. By default there is no cache — every call fetches a fresh token. If the Keycloak rate limit truly becomes a bottleneck, reconsider the decision explicitly and add a cache through a review, not silently in `auth.py`.

### `reference_api.md` drifts from `client.py`

After adding or renaming a method, **always** keep both sides in sync. A mismatch is a bug: the developer looks for `list_project_contractors` in the reference, but the client renamed it to `fetch_project_contractors`.

### Pydantic schemas leak into the client

The client returns `dict` by default. Coupling it to concrete Raport schemas causes a cascade failure on every minor contract change at the source. Schema validation lives in the consuming service, in its own context.

### Attempting to autogenerate the whole client

`client.py` does not hold "every one of Raport's 500 endpoints" — only the 32 reference ones, plus whatever was added on demand. The skill does not propose autogeneration via `datamodel-code-generator` or similar tools. When that becomes a real need, it is a separate decision outside this template.

------------------------------------------------------------------------

## Output format

The final response to the user contains:

1. The detected mode (install / add endpoint / diagnose).
2. Diff fragments for the affected files:
   - `src/config/settings.py` — new `AppConfig` fields;
   - `.env.example` — new lines;
   - `requirements.txt` — `httpx==...`;
   - `src/external/report/` — the list of copied files.
3. Commands the user runs themselves:
   - `pip install -r requirements.txt -r requirements-dev.txt`;
   - `make lint`, `make test`.
4. Open questions (usually — waiting for `REPORT_KEYCLOAK_CLIENT_SECRET` and `REPORT_KEYCLOAK_PASSWORD` from the admins).

------------------------------------------------------------------------

## Related skills

- **`project-structure`** — where exactly `src/external/`, `src/config/`, `src/middlewares/`, `src/tasks/` live. Loaded **before** this skill.
- **`initial-setup`** — baseline Keycloak setup for the microservice's own API (`KEYCLOAK_SERVER_URL`, `KEYCLOAK_REALM`), `middlewares/keycloak_middleware.py`. Must complete before Step 1 of this skill. Plus Steps 3.2–3.3 (Redis + Taskiq) when the sync strategy is selected.
- **`create-model`** — required for the sync strategy: a local mirror table for the Raport entity (with a unique `raport_id`) and its manager. Not required for the proxy strategy.
- **`generate-api-method`** — endpoints that either call `ReportClient` directly (proxy) or use the local mirror manager (sync).
- **`backend-testing`** — mocking `ReportClient` in service unit tests; dedicated tests for Taskiq sync jobs.

End-to-end order for wiring into Raport: `project-structure` → `initial-setup` (Keycloak included) → `report-microservice` → `create-model` / `generate-api-method` → `backend-testing` → `make lint` → `make test`.
