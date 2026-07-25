# Logging Sensitive Data Remediation Notes

This file is a working list of logging statements that may expose sensitive data or user-derived values. The intent is to remediate these later, not to change behavior now.

## High-risk items

| File | Lines | Why it is sensitive | Remediation target |
| --- | --- | --- | --- |
| `app.py` | 361, 373, 375, 384, 387 | Logs technician usernames during login success and failure paths. | Replace raw usernames with a stable pseudonymous identifier or a hashed/trimmed reference. |
| `app.py` | 439 | Logs the raw exception string for 500 errors, which may include request details or internal state. | Log a generic error plus a correlation ID; keep the exception details out of the user-facing log path. |
| `blueprints/api_module.py` | 96, 203 | Logs the full incoming webhook payload for Uptime Kuma and LibreNMS. | Remove payload dumps; log only a ticket ID, source, and non-sensitive status fields. |
| `blueprints/api_module.py` | 114, 211 | Logs monitor hostnames and status/state values from webhook input. | Truncate or redact hostnames if they are internal; log only an opaque monitor identifier if needed. |
| `blueprints/api_module.py` | 81, 86, 158, 163, 248, 253 | Logs exception strings on webhook failure paths. | Keep exception details in debug-only diagnostics or redact message content. |
| `blueprints/changes_module.py` | 136 | Logs the technician username when a change is created. | Replace the raw username with a non-sensitive actor ID or session reference. |
| `blueprints/crm_module.py` | 111 | Logs the technician username that created a customer record. | Redact or pseudonymize the actor field. |
| `blueprints/hr_module.py` | 224 | Logs the raw certification expiry date value supplied in employee data. | Log only the fact that parsing failed, not the submitted value. |
| `blueprints/hr_module.py` | 332 | Logs who reset an employee password plus the target account identifier and UUID. | Reduce this to a generic audit event with a non-sensitive actor/reference. |
| `blueprints/itsm_module.py` | 95, 140 | Logs the technician username/author when ticket status or notes are updated. | Replace raw usernames with actor IDs or masked identifiers. |
| `local_handlers/local_email_handler.py` | 114, 170 | Logs recipient email addresses and email-reply ticket IDs. | Redact the email address or log a keyed identifier instead. |
| `local_handlers/local_email_handler.py` | 175 | Logs IMAP exceptions that may include mailbox/server details. | Keep exception detail out of routine logs unless explicitly needed for debugging. |

## Lower-risk or excluded items

- `storage/json_store.py` only logs file paths and filesystem errors.
- `local_handlers/local_webhook_handler.py` logs service names and connection outcomes, not payload contents.
- `local_handlers/utils.py` logs generic failure messages without user data.

## Notes

- This is a skim-level inventory, not a formal security audit.
- Re-check these paths after any logging refactor or webhook/auth change.
