#!/usr/bin/env python3
import io
import csv
import logging
from functools import wraps
from flask import Blueprint, render_template, session, Response
from local_handlers.auth_decorators import role_required, ROLE_ITSM_TECH
from local_handlers.local_config_loader import load_core_config
from storage.ticket_store import TicketStore

# CONFIG & LOGGING
core_yaml_config = load_core_config()
LOG_LEVEL = core_yaml_config["logging"]["level"]
LOG_FILE = core_yaml_config["logging"]["file"]

ticket_store = TicketStore.from_config()

logging.basicConfig(filename=LOG_FILE, level=getattr(logging, LOG_LEVEL.upper(), logging.INFO), format="%(asctime)s - %(levelname)s - %(message)s",)

# BLUEPRINT
changes_module_bp = Blueprint("changes_module", __name__, url_prefix="/changes")

# NOTE: use role_required(ROLE_ITSM_TECH) for protected routes

def load_tickets():
    return ticket_store.load_all()

# Dashboard Route
@changes_module_bp.route("/", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def changes_home():
    tickets = load_tickets()
    # Filtering out tickets with the Closed Status on the main Dashboard.
    open_changes = [ticket for ticket in tickets if ticket["request_type"].lower() == "change" and ticket["ticket_status"].lower() != "closed"]
    return render_template("changes/changes_dashboard.html", changes=open_changes,
    loggedInTech=session.get("technician"),
)

# Submit New Change Route
@changes_module_bp.route("/submit-new", methods=["GET", "POST"])
@role_required(ROLE_ITSM_TECH)
def submit_new() -> str:
    """Create new change form.
    Returns:
        Rendered form or redirect on success.
    """

# Edit Change Ticket Route
@changes_module_bp.route("/changes/<change_number>/edit", methods=["POST"])
@role_required(ROLE_ITSM_TECH)
def edit_profile(change_number:str) -> str:
    """Update change profile.
    Args:
        change_number: The change number (CHG-YYYY-NNNN).
    Returns:
        Redirect to profile page.
    """

# Export open change tickets as CSV.
@changes_module_bp.route("/export/csv", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def export_changes_csv():
    tickets = load_tickets()
    open_changes = [ticket for ticket in tickets if ticket["request_type"].lower() == "change" and ticket.get("ticket_status", "").lower() != "closed"]

    output = io.StringIO()
    writer = csv.writer(output)

    # CSV Header
    writer.writerow([
        "Ticket Number",
        "Subject",
        "Status",
        "Submitted By",
        "Submission Date",
        "Assigned To",
    ])

    for t in open_changes:
        writer.writerow([
            t.get("ticket_number"),
            t.get("ticket_subject"),
            t.get("ticket_status"),
            t.get("submitted_by"),
            t.get("submission_date"),
            t.get("assigned_technician"),
        ])

    output.seek(0)

    logging.info(
        f"CHANGES MODULE - Exported {len(open_changes)} change tickets to CSV"
    )

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=open_changes.csv"
        },
    )
