#!/usr/bin/env python3
import logging

from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session
from local_handlers.auth_decorators import role_required, ROLE_ITSM_TECH

import local_handlers.local_webhook_handler as local_webhook_handler
from local_handlers.local_config_loader import load_core_config
from storage.service_appid_store import ServiceAppIdStore
from storage.ticket_store import TicketStore

core_yaml_config = load_core_config()
LOG_LEVEL = core_yaml_config["logging"]["level"]
LOG_FILE = core_yaml_config["logging"]["file"]

ticket_store = TicketStore.from_config()
service_appid_store = ServiceAppIdStore.from_config()

itsm_module_bp = Blueprint('itsm', __name__, url_prefix='/itsm')

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
""" Above is the default logging configuration.
Debug - Detailed information
Info - Successes
Warning - Unexpected events
Error - Function failures
Critical - Serious application failures
"""
def load_tickets():
    """Read/load the ticket JSON database into memory.
    Returns:
        list[dict]: All tickets currently on file.
    Raises:
        SystemExit: If the ticket database file cannot be located.
    """
    return ticket_store.load_all()

def save_tickets(tickets):
    """Write the given tickets back to the ticket JSON database.
    Args:
        tickets (list[dict]): The full set of tickets to persist.
    """
    ticket_store.save_all(tickets)
    logging.debug("The Ticket JSON Database file was modified.")


def load_service_appids():
    """Read/load service/app ID records into memory."""
    return service_appid_store.load_all()


@itsm_module_bp.route("/", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def dashboard():
    tickets = load_tickets()
    open_tickets = [t for t in tickets if t["ticket_status"].lower() != "closed"]
    return render_template("itsm/dashboard.html", tickets=open_tickets, loggedInTech=session.get("technician"))

@itsm_module_bp.route("/services-appid", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def services_appid_dashboard():
    services = load_service_appids()
    return render_template(
        "services-appid/dashboard.html",
        services=services,
        loggedInTech=session["technician"],
    )


@itsm_module_bp.route("/ticket/<ticket_number>")
@role_required(ROLE_ITSM_TECH)
def ticket_detail(ticket_number):
    tickets = load_tickets()
    ticket = next((t for t in tickets if t["ticket_number"] == ticket_number), None)
    if ticket:
        return render_template("itsm/console.html", ticket=ticket, loggedInTech=session["technician"],)
    return render_template("errors/404.html"), 404

@itsm_module_bp.route("/ticket/<ticket_number>/update_status/<ticket_status>", methods=["POST"])
@role_required(ROLE_ITSM_TECH)
def update_ticket_status(ticket_number, ticket_status):
    """Update a ticket's status. Called from the Dashboard and Ticket Commander.
    Args:
        ticket_number (str): The ticket number to update.
        ticket_status (str): The new status. Must be one of "Open",
            "In-Progress", or "Closed".
    Returns:
        JSON confirmation on success, or 400/404 on invalid input.
    """
    logging.info(f"{ticket_number} status has been changed to {ticket_status}.")

    valid_statuses = ["Open", "In-Progress", "Closed"]
    if ticket_status not in valid_statuses:
        return render_template("errors/400.html"), 400

    logged_in_tech = session.get("technician")
    tickets = load_tickets()

    for ticket in tickets:
        if ticket["ticket_number"] != ticket_number:
            continue

        ticket_subject = ticket.get("ticket_subject", "No Subject Provided")
        ticket["ticket_status"] = ticket_status

        if ticket_status == "Closed":
            ticket["closed_by"] = logged_in_tech
            ticket["closure_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        save_tickets(tickets)
        logging.info(f"Ticket {ticket_number} status updated to {ticket_status} by {logged_in_tech}.")

        try:
            local_webhook_handler.notify_ticket_event(
                ticket_number=ticket_number,
                ticket_status=ticket_status,
                ticket_subject=ticket_subject,
            )
            logging.info(f"Ticket {ticket_number} status update notifications sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send ticket status update notifications for {ticket_number}: {str(e)}")

        return jsonify({"message": f"Ticket {ticket_number} updated to {ticket_status}."})

    return render_template("errors/404.html"), 404

@itsm_module_bp.route("/ticket/<ticket_number>/append_note", methods=["POST"])
@role_required(ROLE_ITSM_TECH)
def add_ticket_note(ticket_number):
    """Append a technician note to a ticket.

    Args:
        ticket_number (str): The ticket number to annotate.

    Returns:
        JSON confirmation on success, or an error message on failure.
    """
    new_tkt_note = request.form.get("note_content")

    if not new_tkt_note:
        return jsonify({"message": "Note Contents cannot be empty!"}), 400

    tickets = load_tickets()

    for ticket in tickets:
        if ticket["ticket_number"] == ticket_number:
            ticket.setdefault("ticket_worknotes", [])
            ticket["ticket_worknotes"].append(new_tkt_note)
            save_tickets(tickets)
            logging.info(f"Note successfully appended to {ticket_number}.")
            return jsonify({"message": "Note added successfully."}), 200
        
    return jsonify({"message": "Ticket not found."}), 404
