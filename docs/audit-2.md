Updated todo list

I'll scan app.py and itsm_module.py for issues and suggest fixes. I'll read both files now.

Read [](file:///c%3A/Users/faulk/Documents/GitHub/GoobyDesk/app.py#1-1), lines 1 to 400

Read [](file:///c%3A/Users/faulk/Documents/GitHub/GoobyDesk/blueprints/itsm_module.py)

**Plan**
- Scan app.py and itsm_module.py.  
- Report issues by severity.  
- Propose minimal fixes.  
- Ask if you want me to apply fixes.

**Findings (critical → low)**

- **Auth bug (Critical):** `login` loop in app.py sets `session["technician"]` for non-matching users and continues — allows session leakage and breaks auth logic. See app.py.  
  - Fix: stop setting session on non-matches; only set after successful auth; rewrite loop to find user then validate.

- **Hard exit on missing CAPTCHA keys (Critical):** `if not CF_TURNSTILE_SITE_KEY ... exit(1)` — kills app if keys absent. See app.py.  
  - Fix: make CAPTCHA optional via config flag; log error and disable CAPTCHA instead of exiting.

- **Ticket status KeyError (High):** `open_tickets = [t for t in tickets if t["ticket_status"].lower() != "closed"]` will KeyError if `ticket_status` missing. See itsm_module.py.  
  - Fix: use `t.get("ticket_status","").lower()`.

- **Session access KeyError (High):** templates/controllers use `session["technician"]` directly (e.g., services_appid_dashboard). Use `session.get(...)`. See itsm_module.py.  
  - Fix: `session.get("technician")` with fallback.

- **Full-file save race (High):** `save_tickets` writes full list; concurrent requests may clobber changes. See app.py + json_store.py.  
  - Fix: prefer store.update/delete/append helpers or add file-level locking/atomic operations for multi-step modifications.

- **Inconsistent error responses (Medium):** Views return HTML error pages for API-like endpoints and JSON for others. See `update_ticket_status`/`add_ticket_note`.  
  - Fix: return JSON for XHR/POST endpoints; keep HTML for browser navigations.

- **Notes lack metadata & validation (Medium):** `add_ticket_note` appends raw text with no author/timestamp and no length/sanitization. See itsm_module.py.  
  - Fix: store `{author, ts, note}`; validate length; escape when rendering.

- **Status normalization (Medium):** `update_ticket_status` compares case-sensitive values. Use normalized checks and constants. See itsm_module.py.  
  - Fix: normalize input (e.g., `ticket_status.title()` or map).

- **Logging/config resilience (Medium):** `logging.config.dictConfig(LOG_CFG)` can raise; no fallback. See app.py.  
  - Fix: wrap in try/except and fallback to basicConfig.

- **Background thread fragility (Low):** `background_email_monitor` has no try/except inside loop. Any exception stops thread. See app.py.  
  - Fix: catch exceptions inside loop and continue.

- **CSP / headers (Low):** CSP currently allows `'unsafe-inline'` for scripts/styles and `X-XSS-Protection` header is deprecated. See app.py.  
  - Fix: remove `unsafe-inline` if possible; remove `X-XSS-Protection` or document browser-target tradeoffs.

- **Global store instances at import (Low):** `ticket_store`, `change_store` created at module import complicates tests and import-time errors.  
  - Fix: lazily initialize or use factory pattern.

**Suggested immediate priorities**
1. Fix `login` bug (auth broken).  
2. Replace `exit(1)` on missing CAPTCHA with safe fallback.  
3. Fix KeyError usages in `itsm_module` (`ticket_status`, session access).  
4. Add note metadata and validate `add_ticket_note`.  
5. Wrap logging config in try/except.

Do you want me to open PR-style patches and apply these fixes now?
