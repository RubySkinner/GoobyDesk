#!/usr/bin/env python3
# Singular standard library module for GoobyDesk to prevent circular imports and maintain a single source of truth for standard library imports.
from __future__ import annotations

import email
import imaplib
import json
import logging
import os
import re
import smtplib
import bcrypt
import requests
import yaml
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
load_dotenv(".env")
CONFIG_PATH = "./my_data/configuration.yml"

def load_core_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"configuration.yml missing at {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))

def send_email(requestor_email, ticket_subject, ticket_message, html=True):
    config = load_core_config()
    email_config = config.get("email", {})
    enabled = email_config.get("enabled", False)
    account = email_config.get("account", "")
    smtp_server = email_config.get("smtp_server", "")
    smtp_port = email_config.get("smtp_port", 587)

    if not enabled:
        return False

    if not account or not os.getenv("EMAIL_PASSWORD") or not smtp_server:
        return False

    msg = MIMEMultipart()
    msg["Subject"] = ticket_subject
    msg["From"] = account
    msg["To"] = requestor_email
    msg.attach(MIMEText(ticket_message, "html" if html else "plain"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(account, os.getenv("EMAIL_PASSWORD"))
        server.sendmail(account, requestor_email, msg.as_string())

    return True
