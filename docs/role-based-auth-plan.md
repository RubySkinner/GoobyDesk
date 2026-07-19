**Role-Based Authentication — Centralization Plan**

**Overview**
- **Goal:** Centralize authentication decorators into one module and introduce role-based checks for a small set of roles: `itsm_technician`, `hr_technician`, `manager`, `admin`.

**Why:**
- **Consistency:** Single place for access rules and logging.
- **Maintainability:** Easier changes and audit.
- **Extensibility:** Add roles or permission checks later.

**Design Summary**
- **New module:** `local_handlers/auth_decorators.py` — hosts decorator factory, helpers, role constants, and unit-test hooks.
- **Session model:** store authenticated user's identifier and `roles` list in session (e.g., `session['user_id']`, `session['roles']`).
- **Employee model change:** employees gain optional `roles: list[str]` property in employee JSON records (backwards-compatible).
- **Decorator factory:** `role_required(*roles, require_all=False)` — supports one-or-many role checks and optional `require_all` semantics.
- **Helper functions:** `get_current_user()`, `get_current_roles()`, `user_has_role(role)`.

**Implementation Steps**
1. **Add module:** create `local_handlers/auth_decorators.py` with:
   - role constants for the four roles.
   - `role_required` decorator factory that reads `session['roles']` and returns 403 or redirects to login when unauthorized.
   - safe defaults and clear logging for failures.
2. **Login changes:** on successful login (in `app.py` login flow), load user's roles from `storage/employee_store.py` and set `session['roles']`.
3. **Employee schema migration:** add `roles` field to example files in `example_data/` and document migration steps for `prod_data/`.
4. **Refactor endpoints:** replace `technician_required` with `@role_required('itsm_technician')` and apply appropriate roles for HR and manager pages.
5. **Blueprint-level guards:** in blueprints where whole blueprint requires a role, apply the decorator to the blueprint's `before_request` or to each route.
6. **Tests:** add unit tests for `auth_decorators` verifying allowed/forbidden flows and session edge cases.
7. **Logging & audit:** emit structured logs on auth success/failure including `user_id`, endpoint, and required role.

**Migration Notes**
- **Backward compatibility:** if `roles` missing, default to empty list; preserve legacy `technician` session behavior until replaced.
- **Data update:** provide a small script or manual step to annotate existing employees with appropriate roles in `prod_data/employee.json`.

**Security Considerations**
- **Never trust client-sent roles.** Roles come from server-side employee store only.
- **Session integrity:** keep `SESSION_COOKIE_HTTPONLY` and `SESSION_COOKIE_SECURE` as configured in `app.py`.
- **Rate-limit / log** repeated auth failures.

**Example usage**
- `@role_required('itsm_technician')` — single-role check.
- `@role_required('manager','admin', require_all=False)` — allow either manager or admin.

**Next steps (small iterations)**
- Implement module and tests.
- Update login flow and wire one blueprint (`itsm`) as proof-of-concept.
- Migrate employees and roll out to other blueprints.

---
Created for review. If approved I will implement the module and update `app.py` and one blueprint as a POC.
