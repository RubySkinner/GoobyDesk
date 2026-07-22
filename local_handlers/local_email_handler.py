#!/usr/bin/env python3
# Local module for send_email, extract_email_body and fetch_email_replies functions.
__all__ = ["send_email", "extract_email_body", "fetch_email_replies"]
import os
import smtplib
import imaplib
import email
import re
import logging

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from dotenv import load_dotenv
from datetime import datetime # Pending removal.

from local_handlers.utils import extract_email_body

from flask import current_app
from local_handlers.local_config_loader import load_core_config
from storage.ticket_store import TicketStore

load_dotenv(".env")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def _get_config():
    cfg = current_app.config.get("LOADED_CONFIG")
    if cfg is None:
        cfg = load_core_config()
    return cfg


def _get_ticket_store():
    cfg = _get_config()
    return TicketStore(cfg["core"]["tickets_file"])


def _get_email_settings():
    cfg = _get_config()
    email_cfg = cfg.get("email", {})
    return {
        "enabled": email_cfg.get("enabled", False),
        "account": email_cfg.get("account"),
        "imap_server": email_cfg.get("imap_server"),
        "smtp_server": email_cfg.get("smtp_server"),
        "smtp_port": email_cfg.get("smtp_port"),
    }

# Helper functions below for loading and saving tickets.
def load_tickets():
    store = _get_ticket_store()
    return store.load_all()

def save_tickets(tickets):
    store = _get_ticket_store()
    store.save_all(tickets)
    logging.debug("EMAIL HANDLER - Ticket database was updated.")

# Helpers functions above only! Core functions below.
# Send an email if EMAIL_ENABLED is True.
def send_email(requestor_email, ticket_subject, ticket_message, html=True):
    settings = _get_email_settings()
    if not settings.get("enabled"):
        logging.info("EMAIL HANDLER - Email skipped; EMAIL_ENABLED=False.")
        return False

    EMAIL_ACCOUNT = settings.get("account")
    SMTP_SERVER = settings.get("smtp_server")
    SMTP_PORT = settings.get("smtp_port")

    if not EMAIL_ACCOUNT or not EMAIL_PASSWORD or not SMTP_SERVER:
        logging.error("EMAIL HANDLER - Email configuration incomplete. Check configuration.yml and .env.")
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

    except Exception as e:
        logging.error(f"EMAIL HANDLER - Email sending failed: {e}")
        return False

# `extract_email_body` is provided by `local_handlers.utils` to avoid duplication.

def fetch_email_replies():
    """Fetch unread IMAP emails and append them as ticket notes."""
    settings = _get_email_settings()
    if not settings.get("enabled"):
        logging.debug("EMAIL HANDLER - Skipping IMAP fetch; EMAIL_ENABLED=False.")
        return
    logging.debug("EMAIL HANDLER - Checking IMAP for new email replies.")

    try:
        IMAP_SERVER = settings.get("imap_server")
        EMAIL_ACCOUNT = settings.get("account")
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
                        t.setdefault("ticket_notes", [])
                        t["ticket_notes"].append({"ticket_message": body})
                        save_tickets(tickets)
                        logging.info(f"EMAIL HANDLER - Email reply added to {ticket_id}.")
                        break
        mail.logout()

    except Exception as e:
        logging.error(f"EMAIL HANDLER - IMAP error: {e}")
