---
name: create-model
description: Use when user needs to create a new database model, admin
  panel integration, and manager in a FastAPI project using SQLAlchemy,
  Alembic, and SQLAdmin based on structured model description input.
---

# Create Model (FastAPI + SQLAlchemy)

## Overview

This skill generates a complete backend entity:

-   SQLAlchemy model
-   Admin panel registration (SQLAdmin)
-   Data access manager
-   Updates related project files

------------------------------------------------------------------------

## Global Instruction

The agent must analyze existing project files (models, admin, managers)
and use them as references when generating new code. Always follow
existing project conventions from [README.md](README.md).

------------------------------------------------------------------------

## Step 0 --- Analyze mixins

File: `src/models/dbo/mixins.py`

### Usage rules:

- **IDMixin** → default primary key (almost always required)
- **TimestampMixin** → when audit fields are needed
- **Code1cMixin** → for external system integration (1C)
- **SortOrderMixin** → when ordering is required
- **ModelLinkMixin** → when using ModelEnum
- **LifeCycleModelMixin** → when lifecycle/status is needed

### Agent must:

- Analyze input fields
- Select only relevant mixins
- Avoid unnecessary mixins

------------------------------------------------------------------------

## Step 1 --- Create SQLAlchemy model

### Template

```python
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.dbo.base import Base
from src.models.dbo.mixins import IDMixin, TimestampMixin


class ModelName(Base, IDMixin, TimestampMixin):
    __tablename__ = "model_name"

    # Basic fields
    name = Column(String, nullable=False, comment="Translated description")

    # Foreign key field
    related_id = Column(
        UUID(as_uuid=True),
        ForeignKey("related.id"),
        nullable=False,
        index=True,
    )

    # Relationship for FK
    related = relationship("RelatedModel")

    def __str__(self):
        return self.name
```

Rules: - Class name from input - **tablename** = snake_case - Columns
based on input - FK → ForeignKey + relationship - comment → English.
Add all necessary relationships based on FK fields to a new model and all linked models.

File: `src/models/dbo/tables/`

After: Add import to `src/models/dbo/database_models.py`

------------------------------------------------------------------------

## Step 2 --- Admin

### Template

```python
from src.config.admin.categories import CATEGORY_NAME
from src.config.admin.model_admin.base_admin import BaseAdmin
from src.models.dbo.database_models import ModelName


class ModelNameAdmin(BaseAdmin, model=ModelName):
    category = CATEGORY_NAME

    name = "Display Name"
    name_plural = "Display Name"
    icon = "fa-solid fa-database"

    column_list = [
        ModelName.id,
        ModelName.name,
        ModelName.created_at,
        ModelName.updated_at,
    ]

    column_details_list = column_list

    form_columns = [
        ModelName.name,
    ]

    column_searchable_list = [
        ModelName.name,
    ]

    column_sortable_list = [
        ModelName.created_at,
        ModelName.updated_at,
    ]
```

File: src/config/admin/model_admin/`<model>`{=html}.py

Rules: - One file per model - Use categories from
src/config/admin/categories.py - If missing → create

After: Register in src/config/admin/config.py:

```
admin.add_view(model_admin.ModelName)
```

------------------------------------------------------------------------

## Step 3 --- Manager

### Template

```python
from src.services.logger import LoggerProvider
from src.models.dbo.database_models import ModelName

from .common import BaseManager

log = LoggerProvider().get_logger(__name__)


class ModelNameManager(BaseManager):
    entity = ModelName
```

File: src/models/managers/`<model>`{=html}\_manager.py

After: Add import to src/models/managers/**init**.py

------------------------------------------------------------------------

## Step 4 --- Final check

-   Validate imports
-   Ensure no errors
-   Check circular dependencies
-   Run script `make lint` for lint errors and warnings. If it will not fix automatically, fix it by yourself.

------------------------------------------------------------------------

## Output format

1.  Model code
2.  Admin code
3.  Manager code
4.  Additional updates
