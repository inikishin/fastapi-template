---
name: create-model
description: Creates a new domain entity in the FastAPI + SQLAlchemy template — the ORM model, a manager that inherits from BaseManager, optionally an admin view (SQLAdmin) and an Alembic migration. Supports both compact and extended model layouts. Relies on project-structure as the source of layering and naming rules, and requires make lint / make test to pass before handoff.
---

# Create Model (FastAPI + SQLAlchemy)

## Purpose

This skill produces a complete bundle of artefacts for a new entity:

- an ORM model under `src/models/dbo/`;
- a data-access manager under `src/models/managers/` (inheriting from `BaseManager`);
- an SQLAdmin admin view under `src/config/admin/model_admin/` (on request);
- an Alembic migration, generated and verified by the agent;
- updates to the supporting files (`database_models.py`, `managers/__init__.py`, `admin/config.py`).

The skill **does not** create API endpoints, Pydantic request/response schemas or business logic — that is the job of `generate-api-method`. The usual flow is `create-model` first → then `generate-api-method` for the endpoints that work with the new model.

## When to activate

- The user describes a new domain entity ("add a Booking model", "we need a `contract_analytics` table").
- New fields are being added to an existing model (skip the manager / admin steps, only generate the migration).
- An existing model still has no manager, and one is needed.
- An existing model needs an admin view.

**Always** load `project-structure` first — that is where the layer rules, naming conventions, final checklist and file placement come from.

------------------------------------------------------------------------

## What to ask the user

Collect the full list **before** touching files. Offer sensible defaults for missing values in parentheses.

### Required

1. **Entity name** — PascalCase, singular (`Booking`, `ContractAnalytics`).
2. **Table name** — snake_case, usually plural (`bookings`, `contract_analytics`). Default: the plural form of the entity.
3. **Fields** — for each one: name, type (String / Integer / UUID / DateTime / Boolean / Enum / ARRAY / JSON / Numeric / …), `nullable` (default `True` for optional fields), FK (target table and column), uniqueness, index, default value (`default` / `server_default`).
4. **Mixins** — `IDMixin` (default: yes), `TimestampMixin` (default: yes for live business entities, no for dictionaries), `SortOrderMixin` (only when the user needs manual ordering).

### Optional

5. **Model group** (for extended mode) — the target file in `dbo/tables/<group>.py`. Default: a dedicated file for the entity or a suitable existing group.
6. **Relationships** — whether to declare them, to which models, and with what options (`back_populates`, `lazy`, `uselist`).
7. **`text_search_fields`** — columns the manager uses for full-text search, formatted as `{column_name: operator}` (see `BaseManager`).
8. **Admin view** — needed or not (default: no for a fresh service until the admin panel is wired up; yes when `src/config/admin/` is already in place).
9. **Admin category** — the human-readable sidebar group; if the right one is missing in `categories.py`, add it.
10. **Custom manager methods** — non-trivial queries that cannot be expressed through `BaseManager.search` / `apply_filters`. Naming: `get_<entity>_<purpose>_query()` when it returns a `Select`, or `<action>_<entities>()` when it returns final data.
11. **Versioning** (SQLAlchemy-Continuum) — whether this entity needs a `_versions` table.

If the user answers vaguely, lock in the defaults and present the final plan **before** making changes.

------------------------------------------------------------------------

## Step 0 — Inspect the template

Before creating files, confirm the current state:

1. **Model layout:**
   - *Compact*: `src/models/dbo/models.py` holds `Base` and all ORM classes. No `tables/`, no `database_models.py`. This is the default layout in a fresh template.
   - *Extended*: `src/models/dbo/base_model.py` exists alongside `src/models/dbo/tables/` and a public `src/models/dbo/database_models.py` with re-exports. Used once the project has many models.
2. **Mixins shipped in the template:** `IDMixin`, `TimestampMixin`, `SortOrderMixin` live in `src/models/dbo/mixins.py`. Domain-specific mixins (1C integration, lifecycle status, etc.) are **not** shipped. If a field matches a pattern that recurs across entities, agree with the user to add a mixin to `mixins.py` instead of cloning the code.
3. **`BaseManager` is already in place:** `src/models/managers/common.py`. A new manager inherits from it and gets full CRUD + filtering + search + pagination. The method list is documented in `project-structure` under "What `BaseManager` already provides".
4. **Admin:**
   - If `src/config/admin/` does not exist yet and the user wants an admin panel, the **base infrastructure** must be bootstrapped first (`categories.py`, `config.py`, `custom_base.py`, `model_admin/base_admin.py`). The skill creates it as a separate sub-step, only with the user's explicit approval.
   - If `src/config/admin/` is already wired up, just create `model_admin/<entity>.py` and register it in `config.py`.
5. **Check for collisions:** confirm no model / table / manager with the same name already exists. If there is one, propose a different name or add fields to the existing entity.

**Reference files in the template:**

- `src/models/dbo/models.py` → the `User` class (a minimal model in compact mode).
- `src/models/managers/user.py` → `UserManager(BaseManager)` with `text_search_fields` and one custom method on top of the base class.
- `src/models/managers/common.py` → `BaseManager` itself.
- `src/models/dbo/mixins.py` → available mixins.

------------------------------------------------------------------------

## Step 1 — ORM model

### 1.1 Compact mode (default)

Add the class to `src/models/dbo/models.py`:

```python
import sqlalchemy.orm as orm
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.dbo.mixins import IDMixin, TimestampMixin

Base = orm.declarative_base()


class <Entity>(Base, IDMixin, TimestampMixin):
    """Business description of the entity — what it represents and what rules apply."""

    __tablename__ = "<table_name>"

    name = Column(String, nullable=False, comment="Human-readable name")

    related_id = Column(
        UUID(as_uuid=True),
        ForeignKey("<related_table>.id", name="fk_<table_name>_<related_table>"),
        nullable=False,
        index=True,
    )

    related = relationship("<RelatedEntity>", back_populates="<entities>")

    def __str__(self):
        return self.name
```

- `Base` already exists in `models.py` — do not redeclare it.
- `__tablename__` is snake_case and usually plural.
- Every FK has `index=True` and a named constraint.
- Column `comment=` values are English — they land in PostgreSQL and are visible in Swagger-style tools.

### 1.2 Extended mode

When the project is already split into `tables/` + `database_models.py`:

1. Pick the right group — related models (`project_structure`, `calls`, `checklists`, …) live in one file. For a new domain area, create `tables/<group>.py`.
2. Add the class into that file (same in-file imports as the compact template).
3. Re-export it through `src/models/dbo/database_models.py`:
   ```python
   from src.models.dbo.tables.<group> import <Entity> as <Entity>  # noqa: E402
   ```
   (`noqa` — because module-level `make_versioned` calls may appear above the imports.)

Without an import in `database_models.py` Alembic cannot see the model.

### 1.3 Model rules (summary)

- Every class carries a docstring describing the business entity.
- Column names are snake_case and English.
- **Every column with a `ForeignKey` always has `index=True`**, no exceptions. Pair it with an explicit `name="fk_<table>_<related_table>"` constraint name, otherwise Alembic autogeneration will produce an unreadable one.
- Enum columns use `sqlalchemy.Enum(MyEnum, name="<enum_name>")`. Without `name=` PostgreSQL assigns an autogenerated name and the migration suffers.
- Nullable columns state `nullable=True` explicitly; non-nullable columns use `nullable=False`.
- Arrays: `ARRAY(<type>)`; JSON: `JSONB` (PostgreSQL-specific, imported from `sqlalchemy.dialects.postgresql`).
- Declare `relationship` only when `back_populates` / lazy loads genuinely simplify service code. Bulk joins still happen inside a manager via the ORM, not through lazy relationships.
- Do not duplicate `index=True` in `__table_args__` — pick one place.

### 1.4 Versioning (optional)

When the user asks for a `_versions` table, use `SQLAlchemy-Continuum`:

```python
import sqlalchemy
from sqlalchemy_continuum import make_versioned

make_versioned(user_cls=None)  # at the very top of the file, before any model declarations


class <Entity>(Base, IDMixin, TimestampMixin):
    __versioned__ = {}
    ...


sqlalchemy.orm.configure_mappers()  # at the very bottom of the file
```

------------------------------------------------------------------------

## Step 2 — Manager

File: `src/models/managers/<entity>.py` (file name = the entity's snake_case singular form: `booking.py`, `contract_analytics.py`).

### 2.1 Minimal template

```python
from src.config.logger import LoggerProvider
from src.models.dbo.models import <Entity>
from src.models.managers.common import BaseManager

log = LoggerProvider().get_logger(__name__)


class <Entity>Manager(BaseManager):
    """Data access manager for <Entity>."""

    entity = <Entity>
```

In extended mode import the model from `src.models.dbo.database_models`.

### 2.2 Extended template (search + join fields + special filters)

```python
from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload

from src.config.logger import LoggerProvider
from src.models.dbo.models import <Entity>, <Related>
from src.models.managers.common import BaseManager

log = LoggerProvider().get_logger(__name__)


class <Entity>Manager(BaseManager):
    """Data access manager for <Entity>."""

    entity = <Entity>

    text_search_fields = {
        "name": "ilike",
        "code": "exact",
    }

    join_columns = {
        "related_name": <Related>.name,
    }

    def get_base_query(self) -> Select:
        return select(<Entity>).options(joinedload(<Entity>.related))

    def get_<entity>_by_<purpose>_query(self, <param>) -> Select:
        """
        Returns query for <purpose>.

        SQL:
            SELECT ... FROM <entity>
            JOIN ...
            WHERE ...
        """
        return (
            select(<Entity>)
            .join(<Related>, <Entity>.related_id == <Related>.id)
            .where(<Related>.<field> == <param>)
        )
```

### 2.3 Manager rules

- **Inherits from `BaseManager`**, always declares `entity = <Entity>`. Everything else is optional.
- Baseline CRUD (`create`, `get_by_id`, `update_by_id`, `delete_by_id`, `get_by_ids`, `search`, `count`, bulk operations) is **not reimplemented** — `BaseManager` already provides it. The method list and semantics live in `project-structure` under "What `BaseManager` already provides".
- `text_search_fields` declares the input for `apply_full_text_search`. Key = column name in the `SELECT`, value = operator (`ilike`, `exact`, `startswith`, `endswith`, `gt`/`gte`/`lt`/`lte`, `uuid`, `date`, `in`, `not_in`, `is_null`).
- `join_columns` is used when `apply_filters` / `apply_ordering` needs to look at a column from a joined entity.
- `_special_filters_map` is for query parameters whose names do not match column names (`{"any_tag": {"filter_key": "tags", "filter_type": "contains"}}`).
- Override `get_base_query()` **only** when the baseline always includes a join or a where-clause. Otherwise leave the default from `BaseManager`.
- For complex scenarios (dynamic joins, CTEs, window functions) write `get_<entity>_<purpose>_query()` that returns a `Select`. Quote the equivalent SQL in the docstring — it dramatically helps readers.
- Every public manager method carries an English docstring.
- `log = LoggerProvider().get_logger(__name__)` lives in every manager file; log messages are English.

### 2.4 Registering the manager

Add the import to `src/models/managers/__init__.py`:

```python
from src.models.managers.<entity> import <Entity>Manager
```

After that, the manager is reachable through `from src.models import managers` → `managers.<Entity>Manager(db)`. Services use that path.

------------------------------------------------------------------------

## Step 3 — Admin view (on request)

This step only applies when the user asked for an admin panel AND `src/config/admin/` is already wired up (or the user agreed to sub-step 3.0).

### 3.0 (Conditional) Bootstrapping the admin infrastructure

If `src/config/admin/` is missing, build the minimal skeleton first:

```
src/config/admin/
├── __init__.py
├── categories.py                # group constants
├── config.py                    # creates Admin() and registers views via add_view(...)
├── custom_base.py               # (optional) subclass of sqladmin.Admin
└── model_admin/
    ├── __init__.py
    └── base_admin.py            # BaseAdmin(ModelView) with shared defaults
```

Wire Admin into `src/main.py`:

```python
from src.config.admin.config import init_admin

init_admin(app)
```

Add `sqladmin` to `requirements.txt`. Confirm this sub-step with the user explicitly — it introduces a new mount point at `/admin`, a new dependency and an authentication surface. Never create the admin layer without their approval.

### 3.1 Admin view for a model

File: `src/config/admin/model_admin/<entity>.py`.

```python
from src.config.admin.categories import CATEGORY_<NAME>
from src.config.admin.model_admin.base_admin import BaseAdmin
from src.models.dbo.models import <Entity>


class <Entity>Admin(BaseAdmin, model=<Entity>):
    category = CATEGORY_<NAME>

    name = "<Display Name>"
    name_plural = "<Display Names>"
    icon = "fa-solid fa-database"

    column_list = [
        <Entity>.id,
        <Entity>.name,
        <Entity>.created_at,
        <Entity>.updated_at,
    ]

    column_details_list = column_list

    form_columns = [
        <Entity>.name,
    ]

    column_searchable_list = [
        <Entity>.name,
    ]

    column_sortable_list = [
        <Entity>.created_at,
        <Entity>.updated_at,
    ]
```

### 3.2 Category

Take the constant from `src/config/admin/categories.py`. If no suitable one exists, **add it there** instead of hardcoding the string inside the view.

```python
# categories.py
CATEGORY_<NAME> = "<Human-readable group>"
```

### 3.3 Registration

Update `src/config/admin/config.py`:

```python
from src.config.admin.model_admin.<entity> import <Entity>Admin

admin.add_view(<Entity>Admin)
```

Without this line the view never appears in the UI.

### 3.4 Admin view rules

- One file per model. The file name is the entity's snake_case form.
- Inherits **only** from `BaseAdmin`, never directly from `sqladmin.ModelView`.
- No business logic (validations, cascades) inside the view class. Admin configures **only** display and the form. Complex logic lives in a service; admin can invoke it through BackgroundTask / `Form.on_model_change` hooks.
- `column_list`, `form_columns`, `column_searchable_list`, `column_sortable_list` list the fields that actually matter, not a copy of every column.
- `icon` is a FontAwesome class (`fa-solid fa-*`).

### 3.5 (optional) Actions in the row context menu

The user may ask for actions that apply to **selected rows** — sqladmin renders them in the "Actions" context menu per row or for multi-select. Add them directly to the admin view class via the `sqladmin.action` decorator.

**The admin view still carries no business logic — it only calls a service and shapes the HTTP response.** The action opens an `AsyncSession`, forwards the `pks` (the selected rows' primary keys) to a service method, and either redirects to the referer on success or returns 500 with an error message.

```python
from fastapi import Request
from sqladmin import action
from starlette.responses import RedirectResponse, Response

from src.config.admin.categories import CATEGORY_<NAME>
from src.config.admin.model_admin.base_admin import BaseAdmin
from src.config.postgres.db_config import get_async_session
from src.models.dbo.models import <Entity>
from src.services.<feature>.<module> import <Entity>Service


class <Entity>Admin(BaseAdmin, model=<Entity>):  # type: ignore[call-arg]
    category = CATEGORY_<NAME>
    name = "<Display Name>"
    name_plural = "<Display Names>"
    # ... column_list, form_columns, etc.

    async def _run_<action>(self, request: Request) -> Response:
        pks = request.query_params.get("pks", "").split(",")
        try:
            async with get_async_session() as db:
                service = <Entity>Service(db)
                await service.<action_method>(pks)
        except Exception as err:
            return Response(content=f"Error occurred: {err}", status_code=500)

        referer = request.headers.get("Referer")
        if referer:
            return RedirectResponse(referer, status_code=303)
        return RedirectResponse(
            request.url_for("admin:list", identity=self.identity),
            status_code=303,
        )

    @action(
        name="<action_name>",
        label="<Human-readable label>",
    )
    async def <action_method>(self, request: Request):
        return await self._run_<action>(request)
```

**Action rules:**

- `@action(name=..., label=...)` adds the menu entry. `name` is the technical key, `label` is the text shown to the user.
- The action method receives a `Request`, extracts `pks` from the query string and forwards them **to a service method**. No direct ORM / manager usage.
- Wrap anything that may raise in `try/except`. Return `Response(status_code=500)` with the error text so the admin user sees the reason immediately.
- On success redirect to `Referer` (or to the list view if `Referer` is missing) with `status_code=303`.
- If an action needs parameters (a "fake" mode, extra flags), do not inflate logic inside the admin view — pipe the flag down into the service method (reference: `_sync_isup(is_fake: bool)` in `megashablon/src/config/admin/model_admin/project.py`).
- Every action has a matching service method. The service holds all business logic (validations, cascades, commits) and is covered by automated tests (see `backend-testing`).

### 3.6 (optional) A global button above the model list

The user may ask for a shared button or form above the table that is **not** tied to selected rows. Typical use cases: "Import from Excel", "Export report", "Validate contracts". It takes two artefacts:

1. **A `BaseView` with `@expose` routes** — the HTTP handlers for form submissions. Registered in `admin/config.py` separately from the model view via `admin.add_view(<Extra>Admin)`.
2. **A custom list template** — extends `sqladmin/list.html` and posts forms to the paths declared in the `BaseView`.

#### `BaseView` example

```python
from io import BytesIO

from fastapi import Request
from sqladmin import BaseView, expose
from starlette.responses import HTMLResponse, RedirectResponse, StreamingResponse

from src.config.admin.categories import CATEGORY_<NAME>
from src.config.logger import LoggerProvider
from src.config.postgres.db_config import get_async_session
from src.services.<feature>.<module> import <Feature>Service

log = LoggerProvider().get_logger(__name__)


class <Entity>ExtraActions(BaseView):
    category = CATEGORY_<NAME>
    name = "<Human-readable group>"
    name_plural = "<Human-readable group>"

    @expose(
        path="/<feature-kebab>/action/import",
        methods=["POST"],
    )
    async def import_<entity>(self, request: Request):
        form = await request.form()
        try:
            file = form["upload_file"]
        except KeyError as err:
            log.error("No file in multipart form")
            return HTMLResponse(f"Error: {err}", status_code=408)

        try:
            async with get_async_session() as db:
                service = <Feature>Service(db)
                await service.import_from_file(file)
        except Exception as err:
            log.error(f"Import failed: {err}", exc_info=True)
            return HTMLResponse(f"Error during import: {err}")

        referer = request.headers.get("Referer")
        return RedirectResponse(referer, status_code=303)

    @expose(
        path="/<feature-kebab>/action/export",
        methods=["POST"],
    )
    async def export_<entity>(self, request: Request):
        try:
            async with get_async_session() as db:
                service = <Feature>Service(db)
                df = await service.build_report()

            buffer = BytesIO()
            df.to_csv(buffer)
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=<report>.csv"},
            )
        except Exception as err:
            log.error(f"Export failed: {err}", exc_info=True)
            return HTMLResponse(f"Error: {err}")
```

#### Binding the template to the model view

The admin view itself points at the custom template:

```python
class <Entity>Admin(BaseAdmin, model=<Entity>):
    list_template = "admin/<feature>/<feature>_list_template.html"
    # ...
```

#### Custom HTML template

File: `templates/admin/<feature>/<feature>_list_template.html`. It extends `sqladmin/list.html` and adds the "Extra actions" block **above** the standard list via `{{ super() }}`.

```html
{% extends "sqladmin/list.html" %}
{% block content %}
<div class="col-12">
    <div class="card">
        <div class="card-header">
            <div style="width: 50%">
                <h3 class="card-title">Extra actions</h3>
            </div>
            <div style="width: 50%">
                <div class="ms-auto" style="text-align: end; margin-bottom: 12px;">
                    <form enctype="multipart/form-data"
                          action="action/import"
                          method="POST"
                          id="import-form">
                        <div class="ms-3 d-inline-block">
                            <input type="file" id="upload_file" name="upload_file" />
                        </div>
                        <div class="ms-3 d-inline-block">
                            <input type="submit" class="btn btn-secondary" value="Import" />
                        </div>
                    </form>
                    <script>
                        document.getElementById("import-form")
                            .addEventListener('submit', function (event) {
                                if (document.getElementById("upload_file").files.length === 0) {
                                    alert("Pick a file before submitting!");
                                    event.preventDefault();
                                }
                            });
                    </script>
                </div>
                <div class="ms-auto" style="text-align: end; margin-bottom: 12px;">
                    <form enctype="multipart/form-data"
                          action="action/export"
                          method="POST"
                          id="export-form">
                        <div class="ms-3 d-inline-block">
                            <input type="submit" class="btn btn-secondary" value="Export" />
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{{ super() }}
{% endblock %}
```

**Registration** in `src/config/admin/config.py`:

```python
from src.config.admin.model_admin.<entity> import <Entity>Admin, <Entity>ExtraActions

admin.add_view(<Entity>Admin)
admin.add_view(<Entity>ExtraActions)
```

**Rules for global buttons:**

- `BaseView` is just as "thin" as an action: accept the HTTP request, open a session, call a service, shape the response. No SQL or business rules.
- `@expose` paths are kebab-case and relative to the admin root: `/<feature-kebab>/action/<verb>`. The same paths go into `action="..."` of the template forms.
- File uploads require `enctype="multipart/form-data"` and `method="POST"`.
- On success with no file returned, issue a `RedirectResponse` to `Referer` with status 303.
- When the operation returns a file, use `StreamingResponse` with a proper `Content-Disposition`.
- Log errors through `LoggerProvider` and return an `HTMLResponse` with a human-readable message — the admin user does not need JSON.
- JavaScript in the template handles only lightweight form validation. Everything else happens on the server.
- Button labels, the "Extra actions" heading and any flash text are written in the admin users' locale (they are frequently non-English in real deployments). Only paths, file names and technical identifiers are always English.

------------------------------------------------------------------------

## Step 4 — Alembic migration

1. **Ensure the model is visible:**
   - compact mode: `models.py` already imports it;
   - extended mode: the import is in `database_models.py`.

2. **Generate the revision:**
   ```bash
   make migrate msg="add_<table_name>_table"
   ```
   The message is short, snake_case and describes the change (`add_booking_table`, `add_fk_booking_user`, `rename_booking_status_to_state`).

3. **Read the migration by eye.** Alembic autogeneration routinely:
   - misses `CREATE TYPE` for `sa.Enum` declared without `name=`;
   - skips indexes on FKs (especially when `index=True` sits on a sibling column);
   - forgets `server_default` (`default=func.now()` on an ORM column is a Python default; a database-level default needs `server_default=func.now()`);
   - shuffles the order of operations in `downgrade` (you must drop FKs before the table, otherwise PostgreSQL rejects the drop);
   - **mishandles every change to Enum types** — adding values, removing values, renaming. Details in item 4 below.
   Anything you spot — fix it by hand.

4. **Enum types need manual migration edits.** Alembic sees the Enum on the ORM column, but it does not:
   - issue `CREATE TYPE` before the type is used;
   - issue `DROP TYPE` in `downgrade`;
   - run `ALTER TYPE ... ADD VALUE` when new values appear;
   - reshape the type for a proper downgrade of a value removal.

   The canonical pattern — declare the Enum **at module level** inside the migration and manage its lifecycle explicitly in `upgrade` / `downgrade` (reference: `megashablon/migrations/versions/39345bc15e6b_add_auto_action.py`):

   ```python
   from alembic import op
   import sqlalchemy as sa

   # ... revision identifiers ...

   # Module-level enum declaration — reused in upgrade() and downgrade()
   condition_enum = sa.Enum(
       "GREATER_THAN", "GREATER_THAN_OR_EQUAL",
       "LESS_THAN", "LESS_THAN_OR_EQUAL", "EQUAL",
       name="conditionenum",
   )


   def upgrade() -> None:
       # 1. Create the PostgreSQL type explicitly BEFORE using it in columns
       condition_enum.create(op.get_bind())

       # 2. Add columns that reference the module-level variable, not sa.Enum(...)
       op.add_column(
           "lifecycle_action",
           sa.Column("left_condition", condition_enum, nullable=True),
       )
       op.add_column(
           "lifecycle_action",
           sa.Column("right_condition", condition_enum, nullable=True),
       )


   def downgrade() -> None:
       # 1. Drop columns FIRST
       op.drop_column("lifecycle_action", "right_condition")
       op.drop_column("lifecycle_action", "left_condition")

       # 2. Only then drop the type
       condition_enum.drop(op.get_bind())
   ```

   Key points:
   - The enum is declared **at module level**, not inside `upgrade()` — that way the same variable is reused in both `add_column` and `drop`.
   - `condition_enum.create(op.get_bind())` at the top of `upgrade()` creates the PostgreSQL type. Without it, `add_column(..., condition_enum, ...)` fails with `type "conditionenum" does not exist` (or creates the type implicitly, which later breaks the downgrade).
   - `condition_enum.drop(op.get_bind())` at the end of `downgrade()` is the symmetric removal. Order matters — drop columns first, then the type.
   - When the migration adds **new columns** that reference an existing enum, use the pre-existing type: `sa.Enum(..., name="<existing>", create_type=False)` and **do not** call `.create(...)`. You must never duplicate `CREATE TYPE`.

   **Adding new values to an existing Enum.** Alembic does not generate such migrations at all — write the `upgrade` by hand. The `downgrade` is also doable, but it requires rebuilding the type through a renamed shadow via a `USING` cast, since PostgreSQL cannot remove a single enum value with a single statement.

   ```python
   def upgrade() -> None:
       op.execute("ALTER TYPE conditionenum ADD VALUE IF NOT EXISTS 'BETWEEN'")
       op.execute("ALTER TYPE conditionenum ADD VALUE IF NOT EXISTS 'NOT_EQUAL'")


   def downgrade() -> None:
       # If any rows use the values being removed, normalise them first —
       # otherwise the USING cast below will fail.
       op.execute(
           "UPDATE lifecycle_action "
           "SET left_condition = 'EQUAL' "
           "WHERE left_condition IN ('BETWEEN', 'NOT_EQUAL')"
       )
       op.execute(
           "UPDATE lifecycle_action "
           "SET right_condition = 'EQUAL' "
           "WHERE right_condition IN ('BETWEEN', 'NOT_EQUAL')"
       )

       # Rename the current type, create the old shape, cast columns, drop the rename.
       op.execute("ALTER TYPE conditionenum RENAME TO conditionenum_old")
       op.execute(
           "CREATE TYPE conditionenum AS ENUM ("
           "'GREATER_THAN', 'GREATER_THAN_OR_EQUAL', "
           "'LESS_THAN', 'LESS_THAN_OR_EQUAL', 'EQUAL'"
           ")"
       )
       op.execute(
           "ALTER TABLE lifecycle_action "
           "ALTER COLUMN left_condition TYPE conditionenum "
           "USING left_condition::text::conditionenum"
       )
       op.execute(
           "ALTER TABLE lifecycle_action "
           "ALTER COLUMN right_condition TYPE conditionenum "
           "USING right_condition::text::conditionenum"
       )
       op.execute("DROP TYPE conditionenum_old")
   ```

   Important: the `USING` cast requires normalised data first, otherwise `downgrade` fails on rows that still hold the removed value. The normalisation rule is domain-specific and must be agreed with the reviewer (fall back to a default, map to a neighbour value, delete the rows).

5. **Run it locally** — symmetry is mandatory:
   ```bash
   make upgrade
   make downgrade
   make upgrade
   ```
   If `downgrade` fails, the migration is broken — fix it and retry. A migration with a broken downgrade must not land in main.

6. **Never commit** `__pycache__/*` inside `migrations/versions/`.

------------------------------------------------------------------------

## Step 5 — Tests

Every public manager method needs at least one test (the rule comes from `project-structure`; details live in `backend-testing`).

- Path: `tests/test_managers/test_<entity>.py`.
- Level:
  - *unit* with the `async_session` fixture (a mock) — for thin wrappers on top of `BaseManager`.
  - *integration* with `async_test_session` — for custom `get_<entity>_<purpose>_query()` methods that produce non-trivial SQL. The data comes from `tests/dump_data/dumps/dump_<table_name>.json` or from a local fixture with cleanup.

If the user does not explicitly ask for tests, the skill still writes **a minimum** of a happy path and one failure case for every custom manager method. An empty manager (only `entity = ...`) needs no tests — `BaseManager` is covered where it lives.

If integration tests are needed for a brand-new table, create `dump_<table_name>.json` with the minimum number of rows. Do not import data from the production database (see `backend-testing`).

Add the new table name to `tests/dump_data/dump_data_setup.sql` and `dump_data_after.sql`:

```sql
-- dump_data_setup.sql
ALTER TABLE "public"."<table_name>" DISABLE TRIGGER ALL;

-- dump_data_after.sql
ALTER TABLE "public"."<table_name>" ENABLE TRIGGER ALL;
```

------------------------------------------------------------------------

## Step 6 — Final checks

Mandatory, in this order:

```bash
make lint   # ruff + ruff-format + mypy
make test   # pytest with coverage
```

Other things to verify by hand:

- No circular imports between `models/`, `managers/` and `services/`.
- The new model is reachable via `from src.models.dbo.models import <Entity>` (compact) or `from src.models.dbo.database_models import <Entity>` (extended).
- The new manager is reachable via `from src.models import managers` → `managers.<Entity>Manager`.
- The admin view (if created) is registered in `config.py`.
- The migration runs forward and backward locally.
- Coverage has not dropped below 70%.

------------------------------------------------------------------------

## Pre-handoff checklist

1. **Model**
   - Placed in `src/models/dbo/models.py` (compact) or in `dbo/tables/<group>.py` with an import in `database_models.py` (extended).
   - Has a docstring describing the business entity.
   - `__tablename__` is snake_case, usually plural.
   - Only the necessary mixins from `dbo/mixins.py` are applied.
   - Every FK carries `index=True` plus a named constraint.
   - Enums declare `name=`.
2. **Manager**
   - Lives in `src/models/managers/<entity>.py`, inherits from `BaseManager`, declares `entity`.
   - Re-exported through `managers/__init__.py`.
   - No duplication of the baseline CRUD.
   - Public methods carry docstrings.
   - Logger is acquired through `LoggerProvider`.
3. **Admin view** (if created)
   - Placed in `src/config/admin/model_admin/<entity>.py`, inherits from `BaseAdmin`.
   - Category comes from `categories.py`.
   - Registered in `admin/config.py`.
   - No business logic inside the view class.
4. **Migration**
   - Generated via `make migrate msg="..."`.
   - Reviewed by eye; manual fixes for enums, `server_default`, downgrade order applied.
   - Ran locally: `upgrade` → `downgrade` → `upgrade`.
5. **Tests**
   - Every custom manager method has at least a happy path (plus a failure case for `get_*_query`).
   - New tables (when integration tests are needed) have `dump_<table>.json` plus entries in `dump_data_setup.sql` / `dump_data_after.sql`.
6. **Docs and style**
   - Every docstring and comment in `.py` files is English-only.
   - No TODO / FIXME.
7. **Checks**
   - `make lint` is green.
   - `make test` is green, coverage ≥ 70%.

------------------------------------------------------------------------

## Output format

The final response to the user contains:

1. Model code (with all imports).
2. Manager code.
3. Admin view code (when created).
4. Diff fragments for the supporting files: `database_models.py`, `managers/__init__.py`, `admin/config.py`, `categories.py`.
5. The generated migration file name and a short summary of what `upgrade` / `downgrade` do.
6. A list of new and modified files.
7. Results of `make lint` and `make test` — either green, or the list of errors that need manual fixing.

------------------------------------------------------------------------

## Common mistakes

### The model exists but the migration cannot see it

In compact mode make sure the class is really in `dbo/models.py`. In extended mode check the import in `database_models.py`. Alembic `env.py` sees only the metadata exported through that module.

### `sa.Enum(MyEnum)` without `name=`

The migration creates an unnamed PostgreSQL type, and things start breaking on `downgrade` / re-`upgrade`. Always `sa.Enum(MyEnum, name="my_enum")`.

### `default=func.now()` instead of `server_default=func.now()`

A Python-level default only applies to ORM inserts. A database-level default (SQL, admin view, raw INSERTs) needs `server_default=func.now()`.

### Re-implementing the baseline CRUD

Writing `async def get_by_id(...)` or `async def create(...)` on top of `BaseManager` breaks the shared contract. If you genuinely need a different API, pick a different method name or have the service wrap the base call.

### The manager is imported but not available as `managers.<Name>`

The `from .<entity> import <Entity>Manager` line is missing from `managers/__init__.py`. Services cannot reach the class through `from src.models import managers`.

### An admin view is created but never shows up in the UI

The `admin.add_view(<Entity>Admin)` call in `config.py` was not added.

### Business logic inside an admin view

`on_model_change` hooks or validations that query other tables are a classic sign of logic leaking into admin. Move it to a service and have the admin view call the service instead.

### The downgrade is broken

Always run `upgrade → downgrade → upgrade` before handing off. When the downgrade breaks it is usually because drop order is wrong (FKs must be dropped before the table, and the enum type after the columns).

------------------------------------------------------------------------

## Related skills

- **`project-structure`** — the layering, naming and file-placement rules; **must** be loaded before this skill.
- **`generate-api-method`** — the next step: API endpoints on top of the new model.
- **`backend-testing`** — how to test the manager and the integration scenarios around the model.
- **`initial-setup`** — the first-time template setup, if `create-model` runs on a fresh service.

For any code task: `project-structure` → `create-model` → (when needed) `generate-api-method` → `backend-testing` → `make lint` → `make test`.
