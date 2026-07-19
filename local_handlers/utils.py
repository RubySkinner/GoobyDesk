#!/usr/bin/env python3
"""Shared utility helpers for local handlers.

Provides small, pure helpers for authentication and email parsing so
duplicate implementations can be removed from individual modules.
"""
from __future__ import annotations

import logging
import bcrypt

from email import message_from_bytes


__all__ = ["hash_password", "verify_password", "extract_email_body"]


def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt and return the UTF-8 decoded hash.

    Args:
        plain_password: The plain text password to hash.

    Returns:
        The bcrypt hash as a string.
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plain password against a stored bcrypt hash.

    Args:
        plain_password: The plain text password to verify.
        stored_hash: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        logging.exception("Password verification failed due to exception")
        return False


def extract_email_body(msg) -> str:
    """Extract a best-effort email body (prefer plain text, fallback to html).

    Args:
        msg: An email.message.Message instance (or bytes that will be parsed by callers).

    Returns:
        A string with the extracted body (may be empty on failure).
    """
    body = ""
    try:
        # If callers pass raw bytes, convert to Message
        if isinstance(msg, (bytes, bytearray)):
            msg = message_from_bytes(msg)

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdisp = str(part.get("Content-Disposition"))
                if "attachment" in cdisp:
                    continue
                try:
                    if ctype == "text/plain":
                        return part.get_payload(decode=True).decode(errors="ignore").strip()
                    elif ctype == "text/html" and not body:
                        body = part.get_payload(decode=True).decode(errors="ignore").strip()
                except Exception:
                    logging.warning("Failed decoding email part")
        else:
            try:
                body = msg.get_payload(decode=True).decode(errors="ignore").strip()
            except Exception:
                logging.error("Failed decoding email payload")
    except Exception:
        logging.exception("extract_email_body failed")

    return body
