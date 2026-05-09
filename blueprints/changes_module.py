#!/usr/bin/env python3
"""Changes module blueprint for tracking and exporting change requests."""
import csv
import io
import json
import logging
from functools import wraps
from typing import Any
from typing import Callable

from flask import Blueprint
from flask import Response
from flask import render_template
from flask import session

from local_handlers.local_config_loader import load_core_config

core_yaml_config = load_core_config()
LOG_LEVEL: str = core_yaml_config["logging"]["level"]
LOG_FILE: str = core_yaml_config["logging"]["file"]
TICKETS_FILE: str = core_yaml_config["tickets_file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(module)s/%(funcName)s - %(message)s",
)

changes_module_bp = Blueprint("changes", __name__, url_prefix="/changes")


def technician_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to require technician authentication for a route.

    Args:
        func: The route function to wrap.

    Returns:
        Wrapped function that checks for technician session.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Response | tuple[str, int]:
        if not session.get("technician"):
            return render_template("403.html"), 403
        return func(*args, **kwargs)
    return wrapper


def load_tickets() -> list[dict[str, Any]]:
    """Load tickets from the JSON database file.

    Returns:
        List of ticket dictionaries.

    Raises:
        SystemExit: If the ticket database file cannot be found.
    """
    try:
        with open(TICKETS_FILE, "r") as tkt_file:
            return json.load(tkt_file)
    except FileNotFoundError:
        logging.critical("Ticket JSON Database file could not be located.")
        exit(1)


@changes_module_bp.route("/", methods=["GET"])
@technician_required
def changes_home() -> Response | tuple[str, int]:
    """Render the changes module home page.

    Returns:
        Rendered under construction template.
    """
    return render_template("under_construction.html")


@changes_module_bp.route("/export/csv", methods=["GET"])
@technician_required
def export_changes_csv() -> Response:
    """Export open change tickets as a CSV file.

    Returns:
        CSV file download response containing open change tickets.
    """
    tickets = load_tickets()

    open_changes = [
        t for t in tickets
        if t.get("ticket_type") == "Change"
        and t.get("ticket_status", "").lower() != "closed"
    ]

    output = io.StringIO()
    writer = csv.writer(output)

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
