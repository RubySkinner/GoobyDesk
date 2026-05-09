#!/usr/bin/env python3
"""API Ingest blueprint for handling external webhook integrations."""
import json
import logging
from datetime import datetime
from typing import Callable

from flask import Blueprint
from flask import Response
from flask import jsonify
from flask import request

import local_handlers.local_webhook_handler as local_webhook_handler
from local_handlers.local_config_loader import load_core_config

core_yaml_config = load_core_config()
LOG_LEVEL: str = core_yaml_config["logging"]["level"]
LOG_FILE: str = core_yaml_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(module)s/%(funcName)s - %(message)s",
)

api_ingest_bp = Blueprint("api_ingest", __name__, url_prefix="/api")


def get_tickets_functions() -> tuple[
    Callable[[], list[dict]],
    Callable[[list[dict]], None],
    Callable[[], str],
]:
    """Import and return ticket management functions from the main app.

    Returns:
        Tuple of (load_tickets, save_tickets, generate_ticket_number) functions.

    Note:
        Uses delayed import to avoid circular imports with app.py.
    """
    from app import generate_ticket_number
    from app import load_tickets
    from app import save_tickets

    return load_tickets, save_tickets, generate_ticket_number


@api_ingest_bp.route("/status", methods=["GET"])
def api_status() -> tuple[Response, int]:
    """Return the API status and installation information.

    Returns:
        JSON response with status information and HTTP 200.
    """
    return jsonify({
        "is_GoobyDesk": True,
        "installed": True,
        "edition": "community",
        "license_key": None
    }), 200


@api_ingest_bp.route("/tailscale", methods=["POST"])
def tailscale_webhook() -> tuple[Response, int]:
    """Handle incoming Tailscale webhook notifications.

    Creates a new ticket from Tailscale webhook payload and sends
    notifications to configured webhook services.

    Returns:
        JSON response with status and ticket number, or error message.
    """
    load_tickets, save_tickets, generate_ticket_number = get_tickets_functions()
    tailscale_notify_email = api_ingest_bp.config.get(
        "TAILSCALE_NOTIFY_EMAIL", "noreply@tailscale.example.org"
    )

    payload = request.json
    if not payload:
        logging.warning("API INGEST - Tailscale webhook sent an empty payload.")
        return jsonify({"error": "Empty payload"}), 400

    try:
        formatted_ts_webhook_body = json.dumps(payload, indent=4)

        ticket_number = generate_ticket_number()

        new_ticket = {
            "ticket_number": ticket_number,
            "requestor_name": "Tailscale",
            "requestor_email": tailscale_notify_email,
            "ticket_subject": "Tailscale Notification",
            "ticket_message": formatted_ts_webhook_body,
            "request_type": "Change",
            "ticket_impact": "Medium",
            "ticket_urgency": "Medium",
            "ticket_status": "Open",
            "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_notes": []
        }

        tickets = load_tickets()
        tickets.append(new_ticket)
        save_tickets(tickets)
        logging.info(f"Tailscale Notification — {ticket_number} created successfully.")

        try:
            local_webhook_handler.notify_ticket_event(
                ticket_number=ticket_number,
                ticket_status="Open",
                ticket_subject="Tailscale Notification"
            )
            logging.info(
                f"API INGEST - Ticket {ticket_number} status notifications sent successfully."
            )
        except (OSError, ValueError) as e:
            logging.error(
                f"API INGEST - Failed to send ticket status update notifications "
                f"for {ticket_number}: {e}"
            )

        return jsonify({"status": "success", "ticket": ticket_number}), 200

    except json.JSONDecodeError as e:
        logging.error(f"API INGEST - Tailscale webhook JSON decode error: {e}")
        return jsonify({"error": "Invalid JSON payload"}), 400
    except (KeyError, TypeError) as e:
        logging.error(f"API INGEST - Tailscale webhook data error: {e}")
        return jsonify({"error": "Invalid payload structure"}), 400


@api_ingest_bp.route("/uptime-kuma", methods=["POST"])
def uptime_kuma_webhook() -> tuple[Response, int]:
    """Handle incoming Uptime-Kuma webhook notifications.

    Creates tickets for DOWN (status=0) and PENDING (status=2) events.
    Ignores UP and MAINTENANCE status events.

    Returns:
        JSON response with status and ticket number, or error/ignored message.
    """
    load_tickets, save_tickets, generate_ticket_number = get_tickets_functions()

    if not request.is_json:
        logging.warning("API INGEST - Uptime-Kuma webhook sent invalid content type.")
        return jsonify({"error": "Invalid content type"}), 400

    payload = request.json
    if not payload:
        logging.warning("API INGEST - Uptime-Kuma webhook sent empty payload.")
        return jsonify({"error": "Empty payload"}), 400

    try:
        logging.info(f"API INGEST - Uptime Kuma payload received: {payload}")

        heartbeat = payload.get("heartbeat", {})
        monitor = payload.get("monitor", {})

        status = heartbeat.get("status")
        monitor_name = monitor.get("name", "Unknown Monitor")

        status_text = {
            0: "DOWN",
            1: "UP",
            2: "PENDING",
            3: "MAINTENANCE"
        }.get(status, "UNKNOWN")

        if status not in [0, 2]:
            logging.info(
                f"API INGEST - Skipping ticket creation for {monitor_name} "
                f"(status={status_text})."
            )
            return jsonify({
                "status": "ignored",
                "reason": f"status {status_text} not tracked"
            }), 200

        if status == 0:
            ticket_subject = f"Uptime Kuma Alert - {monitor_name} is DOWN"
            ticket_impact = "High"
            ticket_urgency = "High"
            request_type = "Incident"
        else:  # status == 2
            ticket_subject = f"Uptime Kuma Alert - {monitor_name} is PENDING"
            ticket_impact = "Medium"
            ticket_urgency = "Medium"
            request_type = "Incident"

        ticket_message = json.dumps(payload, indent=4)
        ticket_number = generate_ticket_number()

        new_ticket = {
            "ticket_number": ticket_number,
            "requestor_name": "Uptime Kuma",
            "requestor_email": "noreply@uptimekuma.example.org",
            "ticket_subject": ticket_subject,
            "ticket_message": ticket_message,
            "request_type": request_type,
            "ticket_impact": ticket_impact,
            "ticket_urgency": ticket_urgency,
            "ticket_status": "Open",
            "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_notes": []
        }

        tickets = load_tickets()
        tickets.append(new_ticket)
        save_tickets(tickets)

        logging.info(
            f"API INGEST - Uptime-Kuma Notification {ticket_number} created "
            f"successfully (Status: {status_text})."
        )

        try:
            local_webhook_handler.notify_ticket_event(
                ticket_number=ticket_number,
                ticket_status="Open",
                ticket_subject=ticket_subject
            )
            logging.info(
                f"API INGEST - Ticket {ticket_number} status update notifications "
                "sent successfully."
            )
        except (OSError, ValueError) as e:
            logging.error(
                f"API INGEST - Failed to send ticket status update notifications "
                f"for {ticket_number}: {e}"
            )

        return jsonify({"status": "success", "ticket": ticket_number}), 200

    except json.JSONDecodeError as e:
        logging.error(f"API INGEST - Uptime Kuma webhook JSON decode error: {e}")
        return jsonify({"error": "Invalid JSON payload"}), 400
    except (KeyError, TypeError) as e:
        logging.error(f"API INGEST - Uptime Kuma webhook data error: {e}")
        return jsonify({"error": "Invalid payload structure"}), 400
