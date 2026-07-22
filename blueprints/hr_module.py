#!/usr/bin/env python3
"""HR module blueprint for GoobyDesk.
Provides the HR dashboard and its supporting employee-data helpers.
Config is loaded locally in this blueprint (rather than relying on
values set in app.py) to avoid the cross-module NameError pattern
already fixed in itsm_module.
"""
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, render_template, session

from local_handlers.local_config_loader import load_core_config
from flask import current_app
from local_handlers.auth_decorators import role_required, ROLE_HR_TECH
from storage.hr_store import HrStore
from storage.employee_store import EmployeeStore
from local_handlers.local_authentication_handler import hash_password
import secrets
from flask import flash, request

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
        logging.warning(f"Unparseable certification expiry date: {expires}")
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
    active_employees = sum(
        1 for emp in employees if emp.get("employment", {}).get("status") == "active"
    )
    locked_accounts = sum(
        1 for emp in employees if emp.get("access", {}).get("account_locked")
    )
    expiring_certs = sum(
        1
        for emp in employees
        for cert in emp.get("certifications", [])
        if _is_cert_expiring(cert.get("expires"), CERT_EXPIRY_WARNING_DAYS)
    )
    return {
        "total_employees": len(employees),
        "active_employees": active_employees,
        "locked_accounts": locked_accounts,
        "expiring_certs": expiring_certs,
    }

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
    return render_template(
        "hr/hr_dashboard.html",
        employees=employees,
        stats=stats,
        loggedInTech=session.get("technician"),
    )

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
    employee = next((emp for emp in employees if emp.get("uuid") == uuid), None)
    if employee is None:
        return render_template("errors/404.html"), 404
    return render_template("hr/profile.html", employee=employee, loggedInTech=session.get("technician"))


@hr_module_bp.route("/employee/<uuid>/reset-password", methods=["POST"])
@role_required("admin")
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
    logging.warning(
        "HR MODULE - Password reset performed by %s for account %s (uuid=%s)",
        session.get("technician"),
        employee.get("tech_username") or employee.get("username"),
        employee.get("uuid"),
    )

    # Show password once to admin via template variable and flash
    flash("Password reset successful — show it once below.", "success")
    return render_template("hr/profile.html", employee=employee, reset_password=new_password, loggedInTech=session.get("technician"))


# Create New Employee Route
# TODO: implement new_employee() at POST /hr/employee/submit-new, mirroring
# crm_module.new_customer. The dashboard's "+ New Employee" button
# already points at this literal path ahead of the route existing.

# Edit Employee Details Route
# TODO: implement edit_employee(uuid), form pre-populated via
# load_hr_employees() + a save_hr_employees() write-back helper.

# Export Employee Data Route
# TODO: implement export_employees() (CSV/JSON), technician_required.
# Export Employee Data Route
