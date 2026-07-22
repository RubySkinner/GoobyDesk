# Audit Resolution Plan

**Summary**

This document lists concrete steps to resolve findings from docs/audit.md, with file targets and example code. Follow steps in order: centralize config/logging, extract helpers, add validation, add type hints, add tests, and roll out.

**Plan**

1. Centralize logging and config
   - **Goal:** Single source of truth for logging and config, avoid repeated calls to `load_core_config()` and multiple `logging.basicConfig()` uses.
   - **Action:** Load core config in `app.py` and configure logging there. Remove logging setup from blueprints.
   - **Files:** [app.py](app.py), [blueprints/__init__.py](blueprints/__init__.py)

   Example (add to `app.py` startup):

   ```python
   import logging
   import logging.config
   from local_handlers.local_config_loader import load_core_config

   core_cfg = load_core_config()  # returns dict
   LOG_CFG = core_cfg.get("logging", {
	   "version": 1,
	   "formatters": {"default": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
	   "handlers": {"console": {"class": "logging.StreamHandler","formatter": "default"}},
	   "root": {"level": "INFO", "handlers": ["console"]},
   })

   logging.config.dictConfig(LOG_CFG)
   # make config available to blueprints
   app.config.update(core_cfg)
   ```

2. Extract large helpers (CRM record builder)
   - **Goal:** Remove large inline dict construction from `blueprints.crm_module.new_customer()`.
   - **Action:** Create `local_handlers/crm_helpers.py` with small testable functions.
   - **Files:** [local_handlers/crm_helpers.py](local_handlers/crm_helpers.py), [blueprints/crm_module.py](blueprints/crm_module.py)

   Example `local_handlers/crm_helpers.py`:

   ```python
   from typing import Dict, Any

   def build_customer_record(form: Dict[str, Any]) -> Dict[str, Any]:
	   """Return CRM customer dict from validated form data."""
	   record = {
		   "first_name": form.get("first_name", "").strip(),
		   "last_name": form.get("last_name", "").strip(),
		   "email": form.get("email", "").lower().strip(),
		   "meta": {"source": "web"},
	   }
	   return record
   ```

   Replace inline builder in `blueprints/crm_module.py` with:

   ```python
   from local_handlers.crm_helpers import build_customer_record

   @bp.route('/crm/new', methods=['POST'])
   def new_customer():
	   form = request.form.to_dict()
	   record = build_customer_record(form)
	   storage.save_customer(record)
	   return redirect(url_for('crm.dashboard'))
   ```

3. Harden input validation
   - **Goal:** Validate and sanitize inputs consistently across blueprints.
   - **Action:** Add a small validation helper module `local_handlers/validation.py` and call it in endpoints.
   - **Files:** [local_handlers/validation.py](local_handlers/validation.py), example usages in blueprints.

   Example `local_handlers/validation.py`:

   ```python
   import re
   from typing import Dict, Tuple, List

   EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

   def require_fields(data: Dict[str, str], fields: List[str]) -> Tuple[bool, str]:
	   for f in fields:
		   if not data.get(f):
			   return False, f"missing:{f}"
	   return True, ""

   def is_valid_email(email: str) -> bool:
	   return bool(EMAIL_RE.match(email or ""))
   ```

   Example blueprint usage:

   ```python
   from local_handlers.validation import require_fields, is_valid_email

   ok, reason = require_fields(form, ["first_name", "last_name", "email"]) 
   if not ok or not is_valid_email(form.get("email")):
	   abort(400, description=f"invalid input: {reason}")
   ```

4. Reduce repeated config loading
   - **Goal:** Avoid calling `load_core_config()` in every blueprint.
   - **Action:** Load once in `app.py` and expose through `app.config` or dependency injection on blueprint registration.
   - **Files:** [app.py](app.py), [blueprints/*](blueprints/)

   Example (in `app.py`):

   ```python
   core_cfg = load_core_config()
   app.config['CORE_CFG'] = core_cfg
   # in blueprint
   from flask import current_app
   cfg = current_app.config['CORE_CFG']
   ```

5. Add simple type hints and docstrings
   - **Goal:** Improve readability and static analysis.
   - **Action:** Add typing to public functions/helpers and short Google-style docstrings.
   - **Files:** touched helpers and blueprint functions.

   Example:

   ```python
   def get_user_name(user_id: int) -> str | None:
	   """Return username or None if not found.

	   Args:
		   user_id: integer id

	   Returns:
		   str or None
	   """
	   user = db.get(user_id)
	   if user is None:
		   return None
	   return user.name
   ```

6. Tests and rollout
   - **Goal:** Verify correctness before deploy.
   - **Action:** Add unit tests for `crm_helpers.build_customer_record`, `validation` functions, and a small integration test for the `new_customer` endpoint using Flask test client.

   Example test (pytest):

   ```python
   def test_build_customer_record():
	   form = {"first_name": "A ", "last_name": "B", "email": "A@B.COM"}
	   rec = build_customer_record(form)
	   assert rec['first_name'] == 'A'
	   assert rec['email'] == 'a@b.com'
   ```

7. Rollout checklist
   - Remove ad-hoc logging calls from blueprints.
   - Run tests: `pytest -q`.

**Notes & Priorities**

- Low friction: centralize config/logging, extract CRM helper, add validation.
- Medium: add type hints and tests.
- Track changes in a short changelog entry.

If you want, I can implement `local_handlers/crm_helpers.py` and `local_handlers/validation.py` now and update a sample blueprint call.
