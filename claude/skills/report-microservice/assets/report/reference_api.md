# Raport Reference API

Curated list of GET endpoints exposed by the main Raport service. This document
is a **map**, not a contract: when field-level detail is needed, fetch the live
OpenAPI schema from `{app_config.report_api_url}/api/openapi.json` and look up
the referenced response model there.

## Base

- **Base URL** — `app_config.report_api_url` (env: `REPORT_API_URL`).
- **Auth** — password grant via `src/external/report/auth.py::get_report_access_token()`.
  Every request fetches a fresh token (no caching).
- **Common envelope** — every endpoint in this document returns a
  `ListDataResponseSchema`-style body: `{ "data": [...], "pagination": {...}, "code": "200", "message": "..." }`.
  Exceptions are marked explicitly.
- **Shared query parameters** — most endpoints accept:
  - `search` — case-insensitive substring over a set of fields declared on the server;
  - `page`, `per_page` — pagination (defaults: `page=1`, `per_page=100`);
  - `order_by` — list of fields; a leading `-` reverses the order (e.g. `-name`).
  Endpoints that do **not** support one of these parameters list it explicitly.

Last sync with the live OpenAPI: see `client.py` commit history. When in doubt,
compare against `/api/openapi.json` again.

------------------------------------------------------------------------

## Chain 1 — Project → Queue → Construction Object → Housing → Section → Floor

| Client method | GET path | Path params | Extra query params | Response schema |
| --- | --- | --- | --- | --- |
| `list_projects()` | `/api/v1/projects` | — | — | `ProjectListResponseSchema` |
| `get_project_structure(project_id)` | `/api/v1/projects/{project_id}/structure` | `project_id` | — | `ProjectStructureListResponseSchema` |
| `list_project_queues(project_id)` | `/api/v1/projects/{project_id}/queues` | `project_id` | — | `QueuesListResponseSchema` |
| `list_queue_construction_objects(queue_id)` | `/api/v1/queues/{queue_id}/construction-objects` | `queue_id` | — | `ConstructionObjectListResponseSchema` |
| `list_queue_housings(queue_id)` | `/api/v1/queues/{queue_id}/housings` | `queue_id` | — | `QueueHousingListResponseSchema` |
| `list_construction_object_housings(construction_object_id)` | `/api/v1/construction-objects/{construction_object_id}/housings` | `construction_object_id` | — | `HousingListResponseSchema` |
| `get_housing_structure(housing_id)` | `/api/v1/housings/{housing_id}/structure` | `housing_id` | `is_labor`, `is_work`, `contractor_id`, `contractor_id__in`, `work_id`, `work_id__in`. **No pagination.** | `StructureListResponseSchema` |
| `get_housing_structure_with_contractors(housing_id)` | `/api/v1/housings/{housing_id}/structure-with-contractors` | `housing_id` | `contractor_id`, `contractor_id__in`, `work_id`, `work_id__in`. **No pagination.** | `StructureListResponseSchema` |
| `list_housing_sections(housing_id)` | `/api/v1/housings/{housing_id}/sections` | `housing_id` | `work_id__in`, `work_type_id__in`, `work_group_id__in`, `work_set_id__in` | `FloorListResponseSchema` |
| `list_section_floors(section_id)` | `/api/v1/sections/{section_id}/floors` | `section_id` | `work_id__in`, `work_type_id__in`, `work_group_id__in`, `work_set_id__in` | `FloorWithSortOrderListResponseSchema` |

------------------------------------------------------------------------

## Chain 2 — Contractor → Contract

| Client method | GET path | Path params | Extra query params | Response schema |
| --- | --- | --- | --- | --- |
| `list_contractors()` | `/api/v1/contractors` | — | `search_inn`, `is_active` | `ContractorsListResponseSchema` |
| `list_project_contractors(project_id)` | `/api/v1/contractors/project/{project_id}` | `project_id` | — | `ContractorsListResponseSchema` |
| `list_queue_contractors(queue_id)` | `/api/v1/queues/{queue_id}/contractors` | `queue_id` | `is_active` | `ContractorsListResponseSchema` |
| `list_construction_object_contractors(construction_object_id)` | `/api/v1/construction-objects/{construction_object_id}/contractors` | `construction_object_id` | `is_active` | `ContractorsListResponseSchema` |
| `list_housing_contractors(housing_id)` | `/api/v1/housings/{housing_id}/contractors` | `housing_id` | `is_active` | `ContractorsListResponseSchema` |
| `list_section_contractors(section_id)` | `/api/v1/sections/{section_id}/contractors` | `section_id` | `is_active` | `ContractorsListResponseSchema` |
| `list_floor_contractors(floor_id)` | `/api/v1/floors/{floor_id}/contractors` | `floor_id` | `is_active` | `ContractorsListResponseSchema` |
| `list_contractor_contracts(contractor_id)` | `/api/v1/contractors/{contractor_id}/contracts/` | `contractor_id` | — (no pagination, search, or ordering) | `ContractsListResponseSchema` |
| `list_project_contractor_contracts(project_id, contractor_id)` | `/api/v1/contracts/project/{project_id}/contractor/{contractor_id}` | `project_id`, `contractor_id` | `is_warranty_letter` | `ListContractorContractsSchema` |

------------------------------------------------------------------------

## Chain 3 — Work Set → Work Group → Work Type → Work

| Client method | GET path | Path params | Extra query params | Response schema |
| --- | --- | --- | --- | --- |
| `list_construction_object_work_sets(construction_object_id)` | `/api/v1/construction-objects/{construction_object_id}/work-sets` | `construction_object_id` | — | `WorkSetListResponseSchema` |
| `list_work_set_work_groups(work_set_id)` | `/api/v1/work-sets/{work_set_id}/work-groups` | `work_set_id` | `is_labor`, `is_work`, `section_id`, `section_id__in`, `floor_id`, `floor_id__in` | `WorkGroupListResponseSchema` |
| `list_work_groups()` | `/api/v1/work-groups` | — | `is_labor`, `is_work` | `WorkGroupListResponseSchema` |
| `list_housing_work_groups(housing_id)` | `/api/v1/housings/{housing_id}/work-groups` | `housing_id` | — | `HousingWorkGroupListResponseSchema` |
| `list_contractor_work_groups(contractor_id)` | `/api/v1/contractors/{contractor_id}/work-groups/` | `contractor_id` | `housing_id`, `is_labor` | `WorkGroupListResponseSchema` |
| `list_work_group_work_types(work_group_id)` | `/api/v1/work-groups/{work_group_id}/work-types` | `work_group_id` | `section_id`, `section_id__in`, `floor_id`, `floor_id__in` | `WorkTypeListResponseSchema` |
| `list_work_type_works(work_type_id)` | `/api/v1/work-types/{work_type_id}/works` | `work_type_id` | `section_id`, `section_id__in`, `floor_id`, `floor_id__in` | `WorkTypeListResponseForWorkSchema` |
| `get_works_structure()` | `/api/v1/works/structure` | — | `is_labor`, `is_work`, `housing_id`, `work_id`, `work_id__in`. **No pagination.** | `WorkHierarchyResponseSchema` |

------------------------------------------------------------------------

## Chain 4 — Position

| Client method | GET path | Path params | Extra query params | Response schema |
| --- | --- | --- | --- | --- |
| `list_positions()` | `/api/v1/positions/` | — | `position_id`, `position_id__in`, `work_group_id`, `work_group_id__in`, `work_group_is_labor`, `work_group_is_work`. **No `search`.** | `PositionListResponseSchema` |
| `list_work_set_positions(work_set_id)` | `/api/v1/work-sets/{work_set_id}/positions` | `work_set_id` | — | `PositionListResponseSchema` |
| `list_work_group_positions(work_group_id)` | `/api/v1/work-groups/{work_group_id}/positions` | `work_group_id` | — | `PositionListResponseSchema` |
| `list_work_type_positions(work_type_id)` | `/api/v1/work-types/{work_type_id}/positions` | `work_type_id` | — | `PositionListResponseSchema` |
| `list_work_positions(work_id)` | `/api/v1/works/{work_id}/positions` | `work_id` | — | `PositionListResponseSchema` |

------------------------------------------------------------------------

## How to add or update an entry

1. Pull the live OpenAPI: `WebFetch {report_api_url}/api/openapi.json`.
2. Find the endpoint by path and HTTP method.
3. Add a new row to the matching chain table with: client method name, path, path params, extra (non-shared) query params, the referenced response schema name.
4. If a new top-level resource appears (another chain), introduce a new section rather than overloading an existing one.
5. Add the matching method in `client.py` and keep its name aligned with the column "Client method".
6. Do **not** inline full response schemas here — resolve them against the live OpenAPI when implementing consumers.
