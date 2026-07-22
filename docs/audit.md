**Blueprints Audit — Findings & Recommended Fixes**

Findings (medium priority)
- Large inline record construction: `crm_module.new_customer()` builds a big dict inline; extract to helper to improve readability and unit-testing.
- Input validation: several endpoints accept form data with minimal validation. Recommend explicit validation and sanitization.
- Repeated config loading: each blueprint calls `load_core_config()`; consider loading once in `app.py` and passing required values to blueprints.
- Type hints: add simple type hints on public functions and helpers for readability and static analysis.

Recommended next steps (small, ordered)
1. Centralize logging in `app.py`: set format, level, and file from `core_yaml_config`, remove `logging.basicConfig` calls from blueprints.
2. Extract large helpers: move CRM record builder to `local_handlers/crm_helpers.py` or similar.
3. Harden input validation: add small validation helpers and reuse across blueprints.
