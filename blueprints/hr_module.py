#!/usr/bin/env python3
"""HR module blueprint for GoobyDesk.
Provides the HR dashboard and its supporting employee-data helpers.
"""
import logging
import secrets
import uuid
import hashlib
import os
from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from local_handlers.auth_decorators import ROLE_ADMIN, ROLE_HR_TECH, role_required
from local_handlers.local_config_loader import load_core_config
from local_handlers.utils import hash_password
from local_handlers.validation import is_valid_email, require_fields
from storage.employee_store import EmployeeStore
from storage.hr_store import HrStore

def _get_config():
    cfg = current_app.config.get("LOADED_CONFIG")
    if cfg is None:
        cfg = load_core_config()
    return cfg

def _get_hr_store():
    cfg = _get_config()
    return HrStore(cfg["core"]["hr_file"])

def _get_employee_store():
    cfg = _get_config()
    return EmployeeStore(cfg["core"]["employee_auth_file"])

def _build_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

def _next_employee_sequence(employees: list[dict], year: int) -> int:
    existing_ids = [
        employee.get("employee_id", "")
        for employee in employees
        if isinstance(employee.get("employee_id", ""), str)
        and employee.get("employee_id", "").startswith(f"EMP-{year}-")
    ]
    sequence_numbers = []
    for employee_id in existing_ids:
        suffix = employee_id.rsplit("-", maxsplit=1)[-1]
        if suffix.isdigit():
            sequence_numbers.append(int(suffix))

    if not sequence_numbers:
        return 1
    return max(sequence_numbers) + 1

def _build_employment_details(form: dict, created_date: str) -> dict:
    return {
        "hire_date": created_date,
        "termination_date": None,
        "status": "active",
        "rehire_eligible": True,
        "title": form.get("title") or "",
        "business_unit": form.get("business_unit") or "",
        "department": form.get("department") or "",
        "reports_to": None,
        "employment_type": form.get("employment_type") or "full_time",
        "compensation_type": form.get("compensation_type") or "salary",
        "salary": form.get("salary") or None,
        "hourly_rate": form.get("hourly_rate") or None,
        "pay_frequency": form.get("pay_frequency") or None,
        "direct_deposit_info": form.get("direct_deposit_info") or None,
        "equity": {"notes": form.get("equity")} if form.get("equity") else {},
        "bonus_history": [],
        "raise_history": [],
        "salary_exempt": True,
        "bonus_eligible": False,
        "bonus_rate": 0.0,
        "pto_available_hours": 0,
        "pto_used_hours": 0,
    }

def _build_employee_record(form: dict, employees: list[dict]) -> tuple[dict, str]:
    now = _build_timestamp()
    current_year = datetime.now().year
    employee_sequence = _next_employee_sequence(employees, current_year)
    employee_id = f"EMP-{current_year}-{employee_sequence:04d}"

    new_record = {
        "uuid": str(uuid.uuid4()),
        "employee_id": employee_id,
        "first_name": form.get("first_name"),
        "last_name": form.get("last_name"),
        "preferred_name": form.get("preferred_name") or form.get("first_name"),
        "email": form.get("email"),
        "date_of_birth": form.get("date_of_birth"),
        "work_authorization": form.get("work_authorization"),
        "address": {
            "street": form.get("street") or None,
            "city": form.get("city") or None,
            "state": form.get("state") or None,
            "postal_code": form.get("postal_code") or None,
            "country": form.get("country") or None,
        },
        "phone": form.get("phone"),
        "timezone": form.get("timezone") or "UTC",
        "employment": _build_employment_details(form, now.split("T")[0]),
        "access": {
            "role": form.get("role") or "itsm_technician",
            "assignment_queue": form.get("assignment_queue") or "support",
            "account_locked": False,
            "mfa_enabled": False,
            "last_login": None,
            "password_last_changed": None,
            "failed_login_attempts": 0,
        },
        "applications": {},
        "contact_preferences": {
            "preferred_contact": "email",
            "maintenance_notifications": True,
        },
        "emergency_contact": {"name": None, "relationship": None, "phone": None},
        "certifications": [],
        "skills": [],
        "created": now,
        "updated": now,
    }
    return new_record, employee_id

def _append_initial_compensation_history(employee_record: dict, form: dict, created_at: str) -> None:
    created_date = created_at.split("T")[0]
    initial_bonus = form.get("initial_bonus")
    if initial_bonus:
        employee_record["employment"]["bonus_history"].append(
            {"date": created_date, "note": initial_bonus}
        )

    initial_raise = form.get("initial_raise")
    if initial_raise:
        employee_record["employment"]["raise_history"].append(
            {"date": created_date, "note": initial_raise})

def _find_employee_by_uuid(employees: list[dict], employee_uuid: str) -> dict | None:
    for employee in employees:
        if employee.get("uuid") == employee_uuid:
            return employee
    return None

def _clean_form_value(form: dict, field_name: str) -> str | None:
    value = form.get(field_name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None

def _update_employee_record(employee: dict, form: dict) -> None:
    now = _build_timestamp()
    address = employee.setdefault("address", {})
    employment = employee.setdefault("employment", {})

    first_name = _clean_form_value(form, "first_name")
    last_name = _clean_form_value(form, "last_name")
    preferred_name = _clean_form_value(form, "preferred_name")
    email = _clean_form_value(form, "email")

    employee["first_name"] = first_name
    employee["last_name"] = last_name
    employee["preferred_name"] = preferred_name or first_name
    employee["email"] = email
    employee["date_of_birth"] = _clean_form_value(form, "date_of_birth")
    employee["work_authorization"] = _clean_form_value(form, "work_authorization")
    employee["phone"] = _clean_form_value(form, "phone")
    employee["timezone"] = _clean_form_value(form, "timezone") or "UTC"

    address["street"] = _clean_form_value(form, "street")
    address["city"] = _clean_form_value(form, "city")
    address["state"] = _clean_form_value(form, "state")
    address["postal_code"] = _clean_form_value(form, "postal_code")
    address["country"] = _clean_form_value(form, "country")

    employment["title"] = _clean_form_value(form, "title") or ""
    employment["business_unit"] = _clean_form_value(form, "business_unit") or ""
    employment["department"] = _clean_form_value(form, "department") or ""
    employment["employment_type"] = _clean_form_value(form, "employment_type") or "full_time"
    employment["compensation_type"] = _clean_form_value(form, "compensation_type") or "salary"
    employment["salary"] = _clean_form_value(form, "salary")
    employment["hourly_rate"] = _clean_form_value(form, "hourly_rate")
    employment["pay_frequency"] = _clean_form_value(form, "pay_frequency")
    employment["direct_deposit_info"] = _clean_form_value(form, "direct_deposit_info")

    equity_notes = _clean_form_value(form, "equity")
    employment["equity"] = {"notes": equity_notes} if equity_notes else {}
    employee["updated"] = now

hr_module_bp = Blueprint("hr_module", __name__, url_prefix="/hr")

CERT_EXPIRY_WARNING_DAYS = 90  # Certifications expiring within this window are flagged.

# NOTE: HR routes should require HR technician role; use `@role_required(ROLE_HR_TECH)`

def load_hr_employees() -> list[dict]:
    """Load the employee roster from the HR JSON database.
    Returns:
        A list of employee records.
    Raises:
        SystemExit: If the HR database file cannot be found. This
            mirrors the fail-fast behavior used for other core data
            files (e.g. ``load_tickets`` in app.py).
    """
    store = _get_hr_store()
    return store.load_all()

def _is_cert_expiring(expires: str | None, within_days: int) -> bool:
    """Check whether a certification expiry date falls within a window.
    Args:
        expires: An ISO ``YYYY-MM-DD`` date string, or None.
        within_days: How many days out from today counts as "soon".
    Returns:
        True if the certification expires between now and the given
        number of days from now. Malformed or missing dates are
        treated as not expiring, with a warning logged for the former.
    """
    if not expires:
        return False
    try:
        expiry_date = datetime.strptime(expires, "%Y-%m-%d")
    except ValueError:
        logging.warning("Unparseable certification expiry date provided; parsing failed.")
        return False
    return datetime.now() <= expiry_date <= datetime.now() + timedelta(days=within_days)

def build_hr_stats(employees: list[dict]) -> dict:
    """Compute summary statistics for the HR dashboard.
    Args:
        employees: The full employee roster.
    Returns:
        A dictionary of aggregate counts consumed by the dashboard
        template's stat cards.
    """
    active_employees = sum( 1 for emp in employees if emp.get("employment", {}).get("status") == "active" )
    locked_accounts = sum( 1 for emp in employees if emp.get("access", {}).get("account_locked"))
    expiring_certs = sum( 1 for emp in employees
        for cert in emp.get("certifications", [])
        if _is_cert_expiring(cert.get("expires"), CERT_EXPIRY_WARNING_DAYS))
    return {
        "total_employees": len(employees),
        "active_employees": active_employees,
        "locked_accounts": locked_accounts,
        "expiring_certs": expiring_certs,
    }

def _pseudonymize_actor(name: str) -> str:
    """Create a short, stable actor id for logs instead of raw usernames."""
    if not name:
        return "actor_unknown"
    salt = os.getenv("LOG_SALT", "")
    h = hashlib.sha256((str(name) + salt).encode()).hexdigest()[:8]
    return f"actor_{h}"
# Dashboard Route
@hr_module_bp.route("/", methods=["GET"])
@role_required(ROLE_HR_TECH)
def hr_dashboard():
    """Render the HR dashboard listing all employees and summary stats.
    Returns:
        The rendered HR dashboard template.
    """
    employees = load_hr_employees()
    stats = build_hr_stats(employees)
    return render_template("hr/hr_dashboard.html", employees=employees, stats=stats, loggedInTech=session.get("technician"))

# View Employee Details Route
@hr_module_bp.route("/employee/<uuid>", methods=["GET"])
@role_required(ROLE_HR_TECH)
def employee_profile(uuid: str):
    """Render a single employee's profile page.
    Args:
        uuid: The employee's unique identifier.
    Returns:
        The rendered employee profile page, or a 404 error page if no
        employee matches the given uuid.
    Note:
        The profile template itself hasn't been built yet, so this
        currently falls back to under_construction.html once the
        employee is found. Swap in "hr/employee_profile.html" when
        that template exists.
    """
    employees = load_hr_employees()
    employee = _find_employee_by_uuid(employees, uuid)
    if employee is None:
        return render_template("errors/404.html"), 404
    return render_template("hr/profile.html", employee=employee, loggedInTech=session.get("technician"))

@hr_module_bp.route("/employee/<uuid>/edit", methods=["GET", "POST"])
@role_required(ROLE_HR_TECH)
def edit_employee(uuid: str):
    """Render and process edits for an existing employee record."""
    store = _get_hr_store()
    employees = store.load_all()
    employee = _find_employee_by_uuid(employees, uuid)
    if employee is None:
        return render_template("errors/404.html"), 404

    if request.method == "GET":
        return render_template("hr/submit_new.html", employee=employee, loggedInTech=session.get("technician"))

    form = {k: v for k, v in request.form.items()}
    ok, _missing = require_fields(form, ["first_name", "last_name", "email"])
    if not ok or not is_valid_email(form.get("email")):
        return render_template(
            "hr/submit_new.html",
            employee=employee,
            error="First Name, Last Name, and a valid Email are required.",
            loggedInTech=session.get("technician"),
        ), 400

    _update_employee_record(employee, form)
    store.save_all(employees)
    flash(f"Employee {employee.get('employee_id', uuid)} updated.", "success")
    return redirect(url_for("hr_module.employee_profile", uuid=employee["uuid"]))

@hr_module_bp.route("/employee/<uuid>/reset-password", methods=["POST"])
@role_required(ROLE_ADMIN)
def reset_employee_password(uuid: str):
    """Admin action: reset an employee's password and return the new password once."""
    store = _get_employee_store()
    employees = store.load_all()
    employee = next((e for e in employees if e.get("uuid") == uuid), None)
    if employee is None:
        return render_template("errors/404.html"), 404

    # Generate a short-lived one-time password to show to the admin
    new_password = secrets.token_urlsafe(9)  # ~12 chars, URL-safe
    # Hash the password for storage
    hashed = hash_password(new_password)

    # Update the employee record
    employee["password_hash"] = hashed
    if "tech_authcode" in employee:
        del employee["tech_authcode"]
    employee["password_reset_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    store.save_all(employees)
    actor = _pseudonymize_actor(session.get("technician"))
    logging.warning(
        "HR MODULE - Password reset performed; actor=%s target_employee_id=%s",
        actor, employee.get("employee_id")
    )

    # Show password once to admin via template variable and flash
    flash("Password reset successful - show it once below.", "success")
    return render_template("hr/profile.html", employee=employee, reset_password=new_password, loggedInTech=session.get("technician"))

# Create New Employee Route
@hr_module_bp.route("/employee/submit-new", methods=["GET", "POST"])
@role_required(ROLE_HR_TECH)
def new_employee():
    """Render form to create a new employee and handle submissions.
    GET: render the `hr/submit_new.html` form.
    POST: validate input, append record to HR store, redirect to profile.
    """
    if request.method == "GET":
        return render_template("hr/submit_new.html")

    form = {k: v for k, v in request.form.items()}
    ok, _missing = require_fields(form, ["first_name", "last_name", "email"])
    if not ok or not is_valid_email(form.get("email")):
        return render_template("hr/submit_new.html",
            error="First Name, Last Name, and a valid Email are required.",), 400

    employees = load_hr_employees()
    new_record, employee_id = _build_employee_record(form, employees)

    # Persist
    store = _get_hr_store()
    employees.append(new_record)
    _append_initial_compensation_history(new_record, form, new_record["created"])

    store.save_all(employees)
    flash(f"Employee {employee_id} created.", "success")
    return redirect(url_for("hr_module.employee_profile", uuid=new_record["uuid"]))

# Edit Employee Details Route
# Implemented via edit_employee(uuid) using HrStore load/save.

# Export Employee Data Route
# TODO: implement export_employees() (CSV/JSON), technician_required.
# Export Employee Data Route
