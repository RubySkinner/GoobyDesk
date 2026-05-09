#!/usr/bin/env python3
"""Local module for email handling via IMAP and SMTP."""
import email
import email.message
import imaplib
import json
import logging
import os
import re
import smtplib
from datetime import datetime
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from dotenv import load_dotenv

from local_handlers.local_config_loader import load_core_config

__all__ = ["send_email", "extract_email_body", "fetch_email_replies"]

load_dotenv(dotenv_path=".env")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

core_yaml_config = load_core_config()
EMAIL_ENABLED: bool = core_yaml_config["email"]["enabled"]
EMAIL_ACCOUNT: str = core_yaml_config["email"]["account"]
IMAP_SERVER: str = core_yaml_config["email"]["imap_server"]
SMTP_SERVER: str = core_yaml_config["email"]["smtp_server"]
SMTP_PORT: int = core_yaml_config["email"]["smtp_port"]
TICKETS_FILE: str = core_yaml_config["tickets_file"]
LOG_LEVEL: str = core_yaml_config["logging"]["level"]
LOG_FILE: str = core_yaml_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(module)s/%(funcName)s - %(message)s"
)


def load_tickets() -> list[dict[str, Any]]:
    """Load tickets from the JSON database file.

    Returns:
        List of ticket dictionaries, or empty list if file not found.
    """
    try:
        with open(TICKETS_FILE, "r") as tkt_file:
            return json.load(tkt_file)
    except FileNotFoundError:
        return []


def save_tickets(tickets: list[dict[str, Any]]) -> None:
    """Save tickets to the JSON database file.

    Args:
        tickets: List of ticket dictionaries to save.
    """
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=4)
    logging.debug("EMAIL HANDLER - Ticket database was updated.")


def send_email(
    requestor_email: str, ticket_subject: str, ticket_message: str, html: bool = True
) -> bool:
    """Send an email notification to a requestor.

    Args:
        requestor_email: Recipient email address.
        ticket_subject: Email subject line.
        ticket_message: Email body content.
        html: If True, send as HTML email; otherwise plain text.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if not EMAIL_ENABLED:
        logging.info("EMAIL HANDLER - Email skipped; EMAIL_ENABLED=False.")
        return False

    if not EMAIL_ACCOUNT or not EMAIL_PASSWORD or not SMTP_SERVER:
        logging.error(
            "EMAIL HANDLER - Email configuration incomplete. "
            "Check core_configuration.yml and .env."
        )
        return False

    msg = MIMEMultipart()
    msg["Subject"] = ticket_subject
    msg["From"] = EMAIL_ACCOUNT
    msg["To"] = requestor_email
    msg.attach(MIMEText(ticket_message, "html" if html else "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ACCOUNT, requestor_email, msg.as_string())

        logging.info(f"EMAIL HANDLER - Email sent to {requestor_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"EMAIL HANDLER - SMTP authentication failed: {e}")
    except smtplib.SMTPRecipientsRefused as e:
        logging.error(f"EMAIL HANDLER - Recipient refused: {e}")
    except smtplib.SMTPException as e:
        logging.error(f"EMAIL HANDLER - SMTP error: {e}")
    except OSError as e:
        logging.error(f"EMAIL HANDLER - Network error sending email: {e}")

    return False


def extract_email_body(msg: email.message.Message) -> str:
    """Extract the plain text or HTML body from an email message.

    Args:
        msg: The email message object to extract body from.

    Returns:
        The extracted email body as a string.
    """
    logging.debug("EMAIL HANDLER - Extracting email body.")
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition"))
            if "attachment" in cdisp:
                continue
            try:
                if ctype == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(errors="ignore").strip()
                elif ctype == "text/html" and not body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore").strip()
            except (UnicodeDecodeError, AttributeError) as e:
                logging.warning(f"EMAIL HANDLER - Failed decoding email part: {e}")
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors="ignore").strip()
        except (UnicodeDecodeError, AttributeError) as e:
            logging.error(f"EMAIL HANDLER - Failed decoding email: {e}")

    return body


def fetch_email_replies() -> None:
    """Fetch unread IMAP emails and append them as ticket notes.

    Connects to the configured IMAP server, searches for unread emails
    with ticket numbers in the subject line, and appends their content
    as notes to the corresponding tickets.
    """
    if not EMAIL_ENABLED:
        logging.debug("EMAIL HANDLER - Skipping IMAP fetch; EMAIL_ENABLED=False.")
        return

    logging.debug("EMAIL HANDLER - Checking IMAP for new email replies.")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, "UNSEEN")

        if status != "OK":
            logging.error("EMAIL HANDLER - IMAP search failed.")
            return

        email_ids = messages[0].split()
        tickets = load_tickets()

        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status != "OK":
                continue

            for part in msg_data:
                if not isinstance(part, tuple):
                    continue

                msg = email.message_from_bytes(part[1])
                subject_raw, encoding = decode_header(msg["Subject"])[0]

                if isinstance(subject_raw, bytes):
                    subject = subject_raw.decode(encoding or "utf-8")
                else:
                    subject = subject_raw

                ticket_match = re.search(r"TKT-\d{4}-\d+", subject)
                if not ticket_match:
                    continue

                ticket_id = ticket_match.group(0)
                body = extract_email_body(msg)

                for t in tickets:
                    if t["ticket_number"] == ticket_id:
                        t["ticket_notes"].append({"ticket_message": body})
                        save_tickets(tickets)
                        logging.info(f"EMAIL HANDLER - Email reply added to {ticket_id}.")
                        break

        mail.logout()

    except imaplib.IMAP4.error as e:
        logging.error(f"EMAIL HANDLER - IMAP protocol error: {e}")
    except OSError as e:
        logging.error(f"EMAIL HANDLER - Network error during IMAP fetch: {e}")
