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
from storage.hr_store import HrStore

core_yaml_config = load_core_config()
LOG_LEVEL = core_yaml_config["logging"]["level"]
LOG_FILE = core_yaml_config["logging"]["file"]
HR_FILE = core_yaml_config["core"]["hr_file"]

hr_store = HrStore(HR_FILE)

logging.basicConfig(filename=LOG_FILE, level=getattr(logging, LOG_LEVEL.upper(), logging.INFO), format="%(asctime)s - %(levelname)s - %(message)s",)

hr_module_bp = Blueprint("hr_module", __name__, url_prefix="/hr")

CERT_EXPIRY_WARNING_DAYS = 90  # Certifications expiring within this window are flagged.

# Helpers
def technician_required(func):
    """Restrict a route to authenticated technicians.

    Args:
        func: The view function to wrap.

    Returns:
        The wrapped view function. Unauthenticated sessions receive an
        HTTP 403 response instead of invoking ``func``.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("technician"):
            return render_template("errors/403.html"), 403
        return func(*args, **kwargs)
    return wrapper

def load_hr_employees() -> list[dict]:
    """Load the employee roster from the HR JSON database.

    Returns:
        A list of employee records.

    Raises:
        SystemExit: If the HR database file cannot be found. This
            mirrors the fail-fast behavior used for other core data
            files (e.g. ``load_tickets`` in app.py).
    """
    return hr_store.load_all()

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
@technician_required
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
        loggedInTech=session["technician"],
    )

# View Employee Details Route
@hr_module_bp.route("/employee/<uuid>", methods=["GET"])
@technician_required
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
    return render_template("under_construction.html")


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
