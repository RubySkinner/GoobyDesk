#!/usr/bin/env python3
"""Local module for sending webhook notifications to Discord and Slack."""
import logging
from typing import Any

import requests

import local_handlers.local_config_loader as local_config_loader

__all__ = ["notify_ticket_event", "send_webhook"]


def load_webhook_config() -> dict[str, Any]:
    """Load webhook configuration from the core configuration file.

    Returns:
        Configuration dictionary or empty dict if loading fails.
    """
    return local_config_loader.load_core_config() or {}


def is_enabled(service_name: str) -> bool:
    """Check if a webhook service is enabled in configuration.

    Args:
        service_name: Name of the service (e.g., 'discord', 'slack').

    Returns:
        True if the service is enabled, False otherwise.
    """
    webhook_service_status = load_webhook_config()
    webhook_service_cfg = webhook_service_status.get(service_name.lower(), {})
    return bool(webhook_service_cfg.get("enabled", False))


def get_webhook_urls() -> tuple[str | None, str | None]:
    """Retrieve webhook URLs for Discord and Slack from configuration.

    Returns:
        Tuple of (discord_url, slack_url), either may be None if not configured.
    """
    webhook_url_check = load_webhook_config()
    discord_url = webhook_url_check.get("discord", {}).get("webhook_url")
    slack_url = webhook_url_check.get("slack", {}).get("webhook_url")

    return discord_url, slack_url


def notify_ticket_event(
    ticket_number: str, ticket_subject: str, ticket_status: str
) -> dict[str, bool]:
    """Send ticket event notifications to all enabled webhook services.

    Args:
        ticket_number: The ticket identifier (e.g., 'TKT-2024-0001').
        ticket_subject: The subject line of the ticket.
        ticket_status: Current status of the ticket (e.g., 'Open', 'Closed').

    Returns:
        Dictionary mapping service names to success status.
    """
    results: dict[str, bool] = {}

    if is_enabled("discord"):
        results["discord"] = send_discord_notification(
            ticket_number, ticket_subject, ticket_status
        )
    else:
        logging.debug("WEBHOOK HANDLER - Discord disabled; skipping.")

    if is_enabled("slack"):
        results["slack"] = send_slack_notification(
            ticket_number, ticket_subject, ticket_status
        )
    else:
        logging.debug("WEBHOOK HANDLER - Slack disabled; skipping.")

    return results


def send_webhook(url: str | None, payload: dict[str, Any], service_name: str) -> bool:
    """Send a webhook notification to a specified service.

    Args:
        url: The webhook URL to send to.
        payload: The JSON payload to send.
        service_name: Name of the service for logging purposes.

    Returns:
        True if the webhook was sent successfully, False otherwise.
    """
    enabled_service_key = service_name.lower()

    if not is_enabled(enabled_service_key):
        logging.info(f"WEBHOOK HANDLER - {service_name} disabled. Skipping.")
        return False

    if not url:
        logging.warning(
            f"WEBHOOK HANDLER - {service_name} webhook URL missing in core_configuration.yml"
        )
        return False

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logging.info(f"WEBHOOK HANDLER - Successfully sent notification to {service_name}.")
        return True

    except requests.exceptions.Timeout:
        logging.error(f"WEBHOOK HANDLER - {service_name} request timed out.")
    except requests.exceptions.ConnectionError:
        logging.error(f"WEBHOOK HANDLER - Failed to connect to {service_name}.")
    except requests.exceptions.HTTPError as e:
        logging.error(f"WEBHOOK HANDLER - {service_name} HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"WEBHOOK HANDLER - {service_name} unexpected error: {e}")

    return False


def send_discord_notification(
    ticket_number: str, ticket_subject: str, ticket_status: str
) -> bool:
    """Send a ticket notification to Discord.

    Args:
        ticket_number: The ticket identifier.
        ticket_subject: The subject line of the ticket.
        ticket_status: Current status of the ticket.

    Returns:
        True if the notification was sent successfully, False otherwise.
    """
    discord_url, _ = get_webhook_urls()
    new_ticket_status = ticket_status.lower() == "open"
    title = (
        f"New Ticket: {ticket_number} - Subject: {ticket_subject}"
        if new_ticket_status
        else f"Ticket: {ticket_number} updated — Status: {ticket_status}"
    )
    payload: dict[str, Any] = {
        "username": "GoobyDesk",
        "embeds": [
            {
                "title": title,
                "color": 0x58B9FF if new_ticket_status else 0xFFFF00,
            }
        ],
    }

    return send_webhook(discord_url, payload, "Discord")


def send_slack_notification(
    ticket_number: str, ticket_subject: str, ticket_status: str
) -> bool:
    """Send a ticket notification to Slack.

    Args:
        ticket_number: The ticket identifier.
        ticket_subject: The subject line of the ticket.
        ticket_status: Current status of the ticket.

    Returns:
        True if the notification was sent successfully, False otherwise.
    """
    _, slack_url = get_webhook_urls()

    ticket_status_new = ticket_status.lower() == "open"
    title = (
        f"New Ticket: {ticket_number} - Subject: {ticket_subject}"
        if ticket_status_new
        else f"Ticket: {ticket_number} updated — Status: {ticket_status}"
    )
    payload: dict[str, Any] = {
        "username": "GoobyDesk",
        "attachments": [
            {
                "title": title,
                "color": "#58B9FF" if ticket_status_new else "#FFFF00",
            }
        ],
    }

    return send_webhook(slack_url, payload, "Slack")
