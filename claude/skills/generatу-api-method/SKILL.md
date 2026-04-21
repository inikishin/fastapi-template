---
name: generatу-api-method
description: Creates API methods with Pydantic schemas, service layer, and route handlers following project conventions. Triggers on API endpoint specifications with HTTP method, URL path, request/response schemas, and service information.
---

# API Method Generator

## Purpose

This skill enables creation of API methods for Python web services built with **FastAPI, SQLAlchemy, and Alembic**. The agent generates complete API endpoints following a three-step process: Pydantic schemas, service layer methods, and API route handlers.

## When to Activate

Activate when user provides API method specifications including:
- HTTP method (GET, POST, PUT, PATCH, DELETE)
- URL path and prefix
- Request/Response schemas
- Query/Path parameters
- Service layer information
- Authentication requirements

------------------------------------------------------------------------

## Global Instruction

The agent must analyze existing project files (schemas, views, services)
and use them as references when generating new code. Always follow
existing project conventions from [README.md](README.md).

------------------------------------------------------------------------

## Workflow

### Step 1: Create Pydantic Schemas

**Location:** `src/api/routes/{service_name}/schemes.py`

1. **Determine service directory** from "Префикс url" (convert to snake_case)
   - Example: `/calendar-plans` → `calendar_plan`
   - Create directory if it doesn't exist

2. **Analyze existing schemas** in `src/api/schemes.py` for reusable components

3. **Create schemas** for:
   - Request body
   - Response body
   - Query parameters (filters)
   - Path parameters

4. **Schema template:**
```python
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class CheckCalendarPlanRequest(BaseModel):
    id: UUID = Field(..., description="Calendar plan ID")


class CheckCalendarPlanResponse(BaseModel):
    id: UUID = Field(..., description="Calendar plan ID")


class CheckCalendarPlanFilters(BaseModel):
    housing_id: Optional[UUID] = Field(None, description="Housing ID")
    plan_template_id: Optional[UUID] = Field(None, description="Plan template ID")
```

### Step 2: Create/Update Service Layer

**Location**: `src/services/{service_name}/{file_name}.py`

1. Parse service parameter: `{file_path:ServiceClass.method_name}`
2. If file doesn't exist, create:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database_config import get_session
from src.services.common import BaseService
from src.models import managers
from src.services.logger import LoggerProvider

log = LoggerProvider().get_logger(__name__)


class CalendarPlanService(BaseService):  # Всегда наследуем от BaseService
    def __init__(self, db: AsyncSession):  # Всегда передаем db: AsyncSession для менеджеров
        self.db = db  
        self.calendar_plan_manager = managers.CalendarPlanManager(db) # Если понятно для какой модели класс, то сразу добавляем в конструктор его менеджер


async def get_calendar_plan_service(
    db: AsyncSession = Depends(get_session),
) -> CalendarPlanService:
    return CalendarPlanService(db=db)
```

3. If file exists, add method without business logic (return mock data):

```python
async def check_calendar_plans(self, **kwargs):
    # TODO: Implement business logic
    return {"id": "00000000-0000-0000-0000000000"}
```

4. Always create `get_{service_name}_service` dependency function if missing.

### Step 3: Create API Method

**Location**: `src/api/routes/{service_name}/views.py`

1. If views.py doesn't exist, create:

```python
from fastapi import APIRouter, Depends, Query
from src.services.logger import LoggerProvider

log = LoggerProvider().get_logger(__name__)

calendar_plans_router = APIRouter(
    prefix="/calendar-plans",  # Берем из раздела "Префикс url" задания
    tags=["Calendar plans"],  # Берем из раздела "Тэги" задания
)
```

2. Add API method, check necessary imports and add if needed:

```python
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Annotated

from src.api.routes.calendar_plan.schemes import (
    CheckCalendarPlanResponse,
    CheckCalendarPlanFilters,
)
from src.api.schemes import ResponseGroup
from src.services.calendar_plan.calendar_plan import (
    get_calendar_plan_service,
    CalendarPlanService,
)
from src.utils.helpers import get_responses, catch_all_exceptions


@calendar_plans_router.get(
    "/check",  # Берем из раздела "Путь url" задания
    responses={
        200: {
            "model": CheckCalendarPlanResponse,  # Модель для ответа генерируется в виде pydantic модели на основании раздела "Ответ" задания
            "description": "Check results either calendar plan exists or not",  # Берем из раздела "Описание" задания, но переводим на английский в утвердительном наклонении
        },
        **get_responses(ResponseGroup.ALL_ERRORS),
    },
    summary="Check if calendar plan exists",  # Берем из раздела "Описание" задания, но переводим на английский
)
@catch_all_exceptions
async def is_calendar_plans_exists(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],  # Если в разделе "Требуется авторизация" стоит "Да", то добаляем эту строку
    filters: CheckCalendarPlanFilters = Depends(),  # Если в разделе "Query параметры" перечислены через запятую значения с типами в скобках, то создаем отдельную pydantic схему, дополняем ее этими полями и добавляем параметр filters к методу запроса
    service: CalendarPlanService = Depends(get_calendar_plan_service),  # Получаем тип на основании раздела "Сервис" задания. Метод получения сервиса находится в том же файле, что и сервис. Если раздел "Сервис" задания не заполнен, то придумываем свой с аналогичным неймингом и создаем его
):
    return await service.check_calendar_plans(**filters.model_dump())
```

Лишние комментарии и инструкции удали.

## Step 4 --- Final check

-   Validate imports
-   Ensure no errors
-   Check circular dependencies
-   Run script `make lint` for lint errors and warnings. If it will not fix automatically, fix it by yourself.

### Input Data Format

```
- Описание: [Method description in Russian]
- Метод: [GET|POST|PUT|PATCH|DELETE]
- Префикс url: [URL prefix]
- Путь url: [URL path]
- Теги: [Tags for OpenAPI]
- Требуется авторизация: [Да|Нет]
- Сервис: [file_path:ServiceClass.method_name]
- Миксины/шаблоны: [Pagination, sorting, etc.]
- Query параметры: [param_name (Type), ...]
- Request type: [json|form|etc.]
- Request body: {JSON schema}
- Response type: [json|etc.]
- Response body: {JSON schema}
```

### Rules & Conventions

#### Code Standards

* Always use async/await for database operations
* Use Depends() for dependency injection
* Import from src.api.schemes for common response types
* Use @catch_all_exceptions decorator on all endpoints
* Add logger to each file
* Use UUID type for ID fields
* Use Optional[] for nullable fields

#### Authentication

If "Требуется авторизация: Да", add HTTPBearer credentials parameter, If "Нет", omit this parameter

#### Response Handling

Use get_responses(ResponseGroup.ALL_ERRORS) for standard errors
Response description must be in English, affirmative tense
Summary must be in English, concise action description

### File Structure

src/
├── api/
│   ├── schemes.py              # Common reusable schemas
│   └── routes/
│       └── {service_name}/
│           ├── schemes.py      # Service-specific schemas
│           └── views.py        # API route handlers
├── services/
│   └── {service_name}/
│       └── {file_name}.py      # Business logic services
├── config/
│   └── database_config.py      # Database session provider
└── utils/
    └── helpers.py              # Common utilities

### Quality Checks

Before completing, verify:

* Schemas in correct location (src/api/routes/{service}/schemes.py)
* Service file exists with dependency function
* Service method returns mock data (no business logic)
* Router prefix matches input "Префикс url"
* Router tags match input "Теги"
* HTTP method matches input "Метод"
* Authorization parameter added if required
* All imports are correct and complete
* Response model matches schema definition
* Function name is descriptive and in snake_case
* Existing project conventions followed (check README.md)

### Best Practices

1. Analyze existing code first - Check existing views, schemes, services 
3. Keep under 500 lines - Reference external files for details 
5. Use progressive disclosure - Show essential info first 
7. Follow project README.md - Adhere to existing conventions
8. Mock data only - Service methods return mock data
9. English descriptions - All OpenAPI docs in English
10. Type hints - Always use proper type annotations

### Error Handling

If information is missing:

* Ask clarifying questions before proceeding
* Make reasonable defaults for optional parameters
* Document assumptions in comments

Common issues:

* Missing service dependency function
* Incorrect import paths
* Schema name mismatches
* Missing authentication decorators
* Inconsistent naming conventions
