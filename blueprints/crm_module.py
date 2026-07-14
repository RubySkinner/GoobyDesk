#!/usr/bin/env python3
import io
import csv
import json
import logging
from functools import wraps
from flask import Blueprint, render_template, session, Response
from local_handlers.local_config_loader import load_core_config

core_yaml_config = load_core_config()
LOG_LEVEL = core_yaml_config["logging"]["level"]
LOG_FILE = core_yaml_config["logging"]["file"]
CUSTOMERS_FILE = core_yaml_config["core"]["customers_file"]
SERVICE_APPID_FILE = core_yaml_config["core"]["serviceid_appid_file"]

logging.basicConfig(filename=LOG_FILE, level=getattr(logging, LOG_LEVEL.upper(), logging.INFO), format="%(asctime)s - %(levelname)s - %(message)s")

crm_module_bp = Blueprint('crm_module', __name__, url_prefix='/crm')

# Helpers
def technician_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Session-based auth check
        if not session.get("technician"):
            # Unauthorized access attempt
            return render_template("errors/403.html"), 403
        # Authorized technician → proceed to the route
        return func(*args, **kwargs)
    return wrapper

def load_customers_file():
    try:
        with open(CUSTOMERS_FILE, "r") as customer_file:
            return json.load(customer_file)
    except FileNotFoundError:
        logging.critical("Ticket JSON Database file could not be located.")
        exit(1)
        return [] # represents an empty list.

# Dashboard Route
@crm_module_bp.route("/dashboard", methods=["GET"])
@technician_required
def crm_dashboard():
    # Render the CRM dashboard with a list of customers
    try:
        with open(CUSTOMERS_FILE, "r") as customer_file:
            customers = json.load(customer_file)
    except FileNotFoundError:
        logging.critical("Customer JSON Database file could not be located.")
        exit(1)
        return []  # represents an empty list.

    return render_template("crm/crm_dashboard.html", customers=customers, loggedInTech=session["technician"])

# Create New Customer Route

# View Customer Details Route

# Edit Customer Details Route

# Export Customer Data Route
