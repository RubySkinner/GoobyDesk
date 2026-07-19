**Blueprints Audit — Findings & Recommended Fixes**

Scope: quick audit of blueprint modules for conformance with AGENTS.md coding standards and security guidelines.

Summary (high priority)
- Centralized logging: many blueprints call `logging.basicConfig(...)`. Configure logging once in `app.py` and remove duplicates from blueprints.
- Duplicate auth helper: removed leftover `technician_required` from `blueprints/itsm_module.py` (centralized decorators now used).
- Broken reference removed: `get_app_functions()` in `blueprints/reports_module.py` referred to `technician_required` in `app` and has been removed.
- Unsafe session indexing: replaced `session["technician"]` with `session.get("technician")` across blueprints to avoid KeyError on anonymous requests.
- RBAC centralization: `local_handlers/auth_decorators.py` added; blueprints now use `@role_required(...)` where appropriate.

Findings (medium priority)
- Large inline record construction: `crm_module.new_customer()` builds a big dict inline; extract to helper to improve readability and unit-testing.
- Input validation: several endpoints accept form data with minimal validation. Recommend explicit validation and sanitization.
- Repeated config loading: each blueprint calls `load_core_config()`; consider loading once in `app.py` and passing required values to blueprints.
- Logging practices: prefer structured logs and include contextual identifiers; avoid calling `basicConfig` multiple times.
- Missing docstrings: many public route handlers lack Google-style docstrings; add brief docstrings for clarity and API docs.
- Type hints: add simple type hints on public functions and helpers for readability and static analysis.

Risk / Security notes
- Never trust client-supplied session content; roles are populated server-side from employee store.
- Ensure session cookie protections (HTTPOnly, Secure, SameSite) remain configured in `app.py` — these are set already.

Recommended next steps (small, ordered)
1. Centralize logging in `app.py`: set format, level, and file from `core_yaml_config`, remove `logging.basicConfig` calls from blueprints.
2. Extract large helpers: move CRM record builder to `local_handlers/crm_helpers.py` or similar.
3. Harden input validation: add small validation helpers and reuse across blueprints.
4. Add docstrings + type hints to public blueprint functions (gradual PRs).
5. Optionally add a small migration script to annotate `prod_data/employee.json` with `roles`.

Files changed during this session
- Added: `local_handlers/auth_decorators.py`
- Edited: `app.py`, `blueprints/itsm_module.py`, `blueprints/changes_module.py`, `blueprints/crm_module.py`, `blueprints/hr_module.py`, `blueprints/reports_module.py`, `blueprints/serviceid_module.py`, `example_data/example_employee.json`, `docs/role-based-auth-plan.md`

If you want, I can implement step 1 (centralize logging) next — quick change with low risk. Proceed?