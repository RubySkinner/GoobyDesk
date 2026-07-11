#!/usr/bin/env python3
# Local module for send_email, extract_email_body and fetch_email_replies functions.
from .goobydesk_standard_library import (
    extract_email_body,
    fetch_email_replies,
    send_email,
)
__all__ = ["send_email", "extract_email_body", "fetch_email_replies"]
