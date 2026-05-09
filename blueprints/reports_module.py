#!/usr/bin/env python3
"""Reports module blueprint for ticket analytics and CSV export."""
import csv
import io
import logging
from datetime import datetime
from datetime import timedelta
from typing import Any

from flask import Blueprint
from flask import Response
from flask import render_template
from flask import session

from local_handlers.local_config_loader import load_core_config

core_yaml_config = load_core_config()
LOG_LEVEL: str = core_yaml_config["logging"]["level"]
LOG_FILE: str = core_yaml_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(module)s/%(funcName)s - %(message)s"
)

reports_module_bp = Blueprint("reports", __name__, url_prefix="/reports")


def get_app_functions() -> tuple[Any, Any]:
    """Import and return functions from the main app module.

    Returns:
        Tuple of (load_tickets function, BUILD_ID constant).

    Note:
        Uses delayed import to avoid circular imports with app.py.
    """
    from app import BUILD_ID
    from app import load_tickets

    return load_tickets, BUILD_ID


@reports_module_bp.route("/", endpoint="reports_home")
def reports_home() -> Response | tuple[str, int]:
    """Render the reports dashboard with ticket statistics.

    Displays ticket counts by status and time-based metrics for
    the last 7, 14, 30, and 60 days.

    Returns:
        Rendered reports home template with statistics, or 403 if unauthorized.
    """
    load_tickets, build_id = get_app_functions()

    if not session.get("technician"):
        return render_template("403.html"), 403

    tickets = load_tickets()
    now = datetime.now()
    total_tickets = len(tickets)

    status_counts: dict[str, int] = {
        "Open": 0,
        "In-Progress": 0,
        "Closed": 0,
    }

    time_buckets: dict[str, int] = {
        "last_60_days": 0,
        "last_30_days": 0,
        "last_14_days": 0,
        "last_7_days": 0,
    }

    for ticket in tickets:
        status = ticket.get("ticket_status")
        if status in status_counts:
            status_counts[status] += 1

        try:
            submitted_at = datetime.strptime(
                ticket["submission_date"], "%Y-%m-%d %H:%M:%S"
            )
            age = now - submitted_at

            if age <= timedelta(days=60):
                time_buckets["last_60_days"] += 1
            if age <= timedelta(days=30):
                time_buckets["last_30_days"] += 1
            if age <= timedelta(days=14):
                time_buckets["last_14_days"] += 1
            if age <= timedelta(days=7):
                time_buckets["last_7_days"] += 1

        except (KeyError, ValueError):
            logging.warning("REPORTING - Invalid submission_date on ticket")

    return render_template(
        "reports_home.html",
        total_tickets=total_tickets,
        open_tickets=status_counts["Open"],
        in_progress_tickets=status_counts["In-Progress"],
        closed_tickets=status_counts["Closed"],
        last_60_days=time_buckets["last_60_days"],
        last_30_days=time_buckets["last_30_days"],
        last_14_days=time_buckets["last_14_days"],
        last_7_days=time_buckets["last_7_days"],
        logged_in_tech=session["technician"],
        BUILDID=build_id
    )


@reports_module_bp.route("/export/csv", endpoint="export_tickets_csv")
def export_tickets_csv() -> Response | tuple[str, int]:
    """Export all tickets as a CSV file.

    Returns:
        CSV file download response containing all tickets, or 403 if unauthorized.
    """
    load_tickets, _ = get_app_functions()

    if not session.get("technician"):
        return render_template("403.html"), 403

    tickets = load_tickets()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Ticket Number",
        "Subject",
        "Status",
        "Submission Date",
        "Closed By",
        "Closure Date"
    ])

    for ticket in tickets:
        writer.writerow([
            ticket.get("ticket_number", ""),
            ticket.get("ticket_subject", ""),
            ticket.get("ticket_status", ""),
            ticket.get("submission_date", ""),
            ticket.get("closed_by", ""),
            ticket.get("closure_date", "")
        ])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=goobydesk_tickets_report_basic.csv"
        }
    )
