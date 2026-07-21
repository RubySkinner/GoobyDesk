# Change Management Implementation Plan

## Overview
Implement a change-management workflow in GoobyDesk that allows authorized users to submit new changes, keeps change records separate from ticket records, and lays the groundwork for future change review and lifecycle management.

## Goals
- Allow `itsm_technician`, `manager`, and `admin` users to submit new changes.
- Add a `Create New Change` entry point on the changes dashboard.
- Implement a `/changes/submit-new` route that accepts change details and stores them as a new change record.
- Move change data out of `tickets.json` into a dedicated `changes.json` storage model to avoid field conflicts with ticket workflows.

## Scope
### In scope
- Change submission UI and backend flow.
- Role-based access control for the change submission route.
- New change storage abstraction and migration path.
- Basic dashboard integration.

### Out of scope for this phase
- Full change approval workflow.
- Change calendar or scheduling automation.
- Advanced change reporting beyond the existing dashboard experience.

## Existing Codebase Notes
- The changes blueprint already contains a `/submit-new` route stub in `blueprints/changes_module.py`.
- The template directory already has `templates/changes/submit_new.html`, but it is currently empty.
- The changes dashboard is rendered from `templates/changes/changes_dashboard.html`.
- Role checks already exist through `local_handlers/auth_decorators.py` and should be reused for this feature.
- The repository already uses storage wrappers such as `TicketStore`, so the change store should follow the same pattern.

## Implementation Steps

### 1. Access Control
- Protect the change submission route with the existing RBAC decorator system.
- Allow access for:
  - `itsm_technician`
  - `manager`
  - `admin`
- Apply the same guard pattern to any future change-management routes that should be restricted to these roles.

### 2. Add a Dedicated Change Store
- Introduce a new storage abstraction for change records, similar to `TicketStore`.
- Use a dedicated data file such as `changes.json`.
- Keep the change schema distinct from the ticket schema to avoid conflicts between:
  - ticket fields such as `ticket_subject` and `ticket_status`
  - change fields such as `change_short_description`, `implement_plan`, `rollback_plan`, and `test_accept_plan`
- The change store should support basic CRUD-style operations for the initial implementation.

### 3. Define the Change Record Schema
Use a dedicated schema for change records with fields such as:
- `uuid`
- `change_created_timestamp`
- `change_number`
- `change_risk`
- `change_status`
- `change_updated_timestamp`
- `impacted_service_id`
- `impacted_service_uuid`
- `implement_plan`
- `implementor_id`
- `implementor_uuid`
- `planned_end_timestamp`
- `planned_start_timestamp`
- `requestor_id`
- `requestor_uuid`
- `rollback_plan`
- `test_accept_plan`
- `change_short_description`

The initial implementation can store a minimal subset of these fields while preserving the full field list for future expansion.

### 4. Implement the Submit-New Backend Flow
- Complete the `submit_new()` handler in `blueprints/changes_module.py`.
- Support both `GET` and `POST` methods.
- On `GET`, render the change submission form.
- On `POST`, validate required input values before creating a record.
- Required fields for the first implementation should include:
  - change subject / description
  - implement plan
  - test plan
  - rollback plan
  - planned start timestamp
  - planned end timestamp
- Set the initial change status to `pending`.
- Generate a unique change number, ideally using a helper similar to `TicketStore.next_change_number()`.
- Persist the new record to the new change store.

### 5. Implement the Submit-New UI
- Populate `templates/changes/submit_new.html` with a form for change submission.
- Include fields for:
  - subject / short description
  - description or detailed summary
  - implement plan
  - test plan
  - rollback plan
  - risk selection
  - planned start date/time
  - planned end date/time
- Keep the form simple, readable, and consistent with the existing Flask/Jinja templates in the project.
- On successful submission, redirect the user back to the changes dashboard or a future change detail page.

### 6. Add the Dashboard Action
- Update `templates/changes/changes_dashboard.html` with a `Create New Change` button.
- Link the button to `/changes/submit-new`.
- Preserve the existing dashboard listing for current change records.

### 7. Split Change Data from Ticket Data
- Do not continue storing change records inside `tickets.json` as a workaround.
- Introduce a dedicated `changes.json` storage file and use it as the source of truth for change records.
- Keep tickets for incident/request workflows only.
- This separation prevents schema conflicts and makes future change-specific workflows easier to maintain.

### 8. Migration Strategy for Existing Data
- Add a migration path for any records that already resemble changes and are stored in `tickets.json`.
- The migration should:
  - read existing ticket records that represent changes
  - map the relevant fields into the new change schema
  - write them to `changes.json`
  - preserve the original ticket record until the migration is confirmed safe
- Prefer an explicit migration function or one-time import script rather than a silent merge inside the runtime logic.
- Once the migration is validated, the old change-like records can be retired from the ticket store if desired.

## Suggested Implementation Order
1. Add the new change storage abstraction and configuration path.
2. Implement RBAC for the change submission route.
3. Implement the POST handler and persistence logic.
4. Build the submit form UI.
5. Add the dashboard button.
6. Add migration support for existing change-like records.
7. Validate the happy path with a test submission.

## Validation Checklist
- Authorized users can open `/changes/submit-new`.
- Unauthorized users receive a 403 response.
- A submitted change is saved in `changes.json`.
- The change appears on the change dashboard.
- The stored change uses the expected pending status and generated change number.
- Existing ticket functionality remains intact after the storage split.

## Notes for Future Work
- Once the storage split is complete, follow-on work can add:
  - change detail views
  - change approval and rejection flows
  - status transition handling
  - richer dashboards and reporting
