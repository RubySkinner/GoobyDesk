# New Employee Access Provisioning Plan

## Current Gap

The HR create flow only writes the HR roster through `HrStore` in `blueprints/hr_module.py`.
GoobyDesk login reads a separate auth dataset through `EmployeeStore` in `app.py`.
Result: a new employee exists in HR, but has no login record, so authentication always fails.

## Root Cause

Two different JSON stores represent one person:

- HR profile store: identity, employment, contact, access metadata.
- Auth store: login username, password hash, legacy authcode, role mapping.

The `new_employee()` route creates only the HR record and never provisions the auth record.

## Target Behavior

Creating a new employee from HR should optionally or by default create a matching GoobyDesk login account in the same workflow.

Minimum outcome:

- HR record created.
- Auth record created.
- Shared key links both records.
- Temporary password generated once.
- Username is deterministic and unique.
- Roles in login session match the HR access role.

## Recommended Design

### 1. Define one canonical linkage key

Use `uuid` as the hard link between HR and auth records.

Why:

- `uuid` already exists in HR records.
- password reset already looks up auth users by `uuid` in `reset_employee_password()`.
- usernames and emails can change; `uuid` should not.

Required auth fields for new records:

- `uuid`
- `tech_username`
- `password_hash`
- `roles`
- `tech_type`
- `created`
- `updated`
- optional: `must_change_password`, `account_locked`

### 2. Add a dedicated auth-provisioning helper

Create a small helper near the HR create flow, or in a local handler, such as:

- `_build_employee_auth_record(...)`
- `_derive_auth_username(...)`
- `_map_hr_role_to_auth_roles(...)`
- `_provision_employee_access(...)`

Keep this logic out of the route body.

### 3. Standardize username generation

Pick one rule and enforce uniqueness against `EmployeeStore`.

Recommended order:

1. Accept explicit username from HR form. Add this to the form.



Best fit here: use `employee_id` for login username.

Why:

- login page already labels the field as `Technician ID` / `Employee ID`.
- `employee_id` is already unique by sequence.
- avoids rename churn when names or email change.

### 4. Generate a temporary password at creation time

Provision with a strong random password using `secrets.token_urlsafe(...)` and hash it with `hash_password()`.

Recommended behavior:

- show password once on the post-create profile page
- flash clear warning that it will not be shown again
- set `must_change_password = True`
- later enforce password rotation at next login

Do not store plaintext beyond the immediate response.

### 5. Map HR access role to login roles explicitly

Today HR record uses `employee["access"]["role"]`, while login authorization uses auth-store `roles` plus optional legacy `tech_type` inference.

Add a single mapping table, for example:

- `itsm_technician` -> `roles=["itsm_technician"]`, `tech_type="Technician"`
- `hr_technician` -> `roles=["hr_technician"]`, `tech_type="HR"`
- `manager` -> `roles=["manager"]`, `tech_type="Manager"`
- `admin` -> `roles=["admin"]`, `tech_type="Admin"`

Avoid relying on `tech_type` alone. Treat `roles` as the modern source of truth.

### 6. Handle provisioning as one application transaction

Because this app uses two JSON files, there is no real DB transaction.
So implement an application-level sequence with rollback.

1. Save HR first with `access.account_locked = True` and `access.provisioning_status = "pending"`.
2. Save auth second.
3. On success, update HR to `provisioning_status = "complete"`.
4. On failure, leave a visible pending state for admin repair.

### 7. Expose provisioning state in HR

Extend the HR access block with fields like:

- `provisioning_status`: `pending|complete|failed`
- `login_enabled`: `true|false`
- `auth_username`: stored copy for display

This lets HR see whether GoobyDesk access was actually created.

### 8. Extend the HR create form modestly

Add only the fields needed for provisioning:

- `role` select
- optional `auth_username` override
- `create_login_access` checkbox, default on

### 9. Update the employee profile page

Show access details directly on the HR profile page:

- login enabled
- auth username
- provisioning status
- password reset action
- temporary password only immediately after create or reset

### 10. Add repair and idempotency paths

Add an admin/HR action for existing records:

- `Provision Access`
- visible only if HR record exists without matching auth record

This covers:

- old employees created before the fix
- partial-write failures
- manually imported HR records

Provisioning should be idempotent:

- if auth record already exists for same `uuid`, do not create another
- if username exists for another `uuid`, fail clearly

## Concrete Implementation Steps

### Phase 1. Backend contract

1. Add helper to map HR role to auth roles.
2. Add helper to derive unique username.
3. Add helper to build auth record with hashed temp password.
4. Add helper to find auth records by `uuid` and `tech_username`.

### Phase 2. HR create workflow

1. Update `templates/hr/submit_new.html` to include role and optional username override.
2. Update `_build_employee_record()` to persist `auth_username`, `login_enabled`, and `provisioning_status` in `access`.
3. Update `new_employee()` to:
   - load auth store
   - build auth record
   - validate uniqueness
   - save both records
   - render one-time temporary password after success

### Phase 3. Profile and repair workflow

1. Update `templates/hr/profile.html` to show auth provisioning state.
2. Add `POST /hr/employee/<uuid>/provision-access` for backfill/repair.
3. Reuse same helper used by `new_employee()`.

### Phase 4. Login hardening

1. Optionally enforce `must_change_password` during login.
2. Reject disabled or locked users explicitly.
3. Log provisioning failures and login failures with `uuid` and username.

## Validation Rules

At create time, reject if:

- email invalid
- role invalid
- username format invalid
- username already used by another auth record
- auth record already exists for same `uuid`

Recommended username rules:

- ASCII letters, digits, `_`, `-`
- length 3 to 32
- case-insensitive uniqueness

## Testing Plan

### Manual checks

1. Create employee with default login provisioning enabled.
2. Confirm HR file contains `uuid`, access status, and auth username.
3. Confirm auth file contains matching `uuid`, username, roles, and `password_hash`.
4. Log in with generated username and temporary password.
5. Confirm HR-selected role grants correct blueprint access.
6. Try duplicate username and verify create fails cleanly.
7. Simulate auth-write or HR-write failure and confirm status is recoverable.

### Automated tests worth adding

1. Unit test for username derivation and collision handling.
2. Unit test for role mapping.
3. Unit test for auth record builder.
4. Route test for successful employee + auth provisioning.
5. Route test for duplicate username rejection.
6. Route test for provisioning repair endpoint.

## Migration / Backfill

You likely already have HR employees without auth records.
Add a one-time repair script or admin endpoint that:

1. scans HR records
2. matches existing auth records by `uuid`, then email or username only if needed
3. lists missing accounts
4. provisions missing auth entries safely

Do not try to guess too much during backfill. Wrong account linking is worse than no account.

## Suggested Order Of Work

1. Add helpers and auth schema.
2. Add create-time provisioning.
3. Show temporary password on success.
4. Add profile visibility for auth state.
5. Add repair endpoint for older employees.
6. Add tests.
7. Backfill legacy HR records.

## Recommended First Slice

Smallest useful implementation:

1. Generate auth record during `new_employee()`.
2. Use `employee_id` as `tech_username`.
3. Hash a generated temporary password.
4. Save matching `uuid` into auth store.
5. Show password once after creation.
6. Store `roles` from HR access role mapping.
